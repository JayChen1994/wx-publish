from __future__ import annotations

import asyncio
import ipaddress
import socket
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

from app.core.config import settings
from app.core.errors import PublishFailed
from app.domain.models import PublishResult
from app.infrastructure.images import read_media, strip_watermark_bytes

TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
DRAFT_ADD_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"
PUBLISH_URL = "https://api.weixin.qq.com/cgi-bin/freepublish/submit"
MATERIAL_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material"
UPLOAD_IMG_URL = "https://api.weixin.qq.com/cgi-bin/media/uploadimg"
MAX_IMAGE_BYTES = 10 * 1024 * 1024
WECHAT_IMAGE_MAX_BYTES = 1024 * 1024
THUMB_MAX_BYTES = 64 * 1024
COVER_WIDTH = 900
COVER_RATIO = 2.35


def _first_image_src(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for image in soup.find_all("img"):
        src = str(image.get("src") or "").strip()
        if src:
            return src
    return ""


def _cover_from_image(content: bytes) -> bytes:
    """把正文首图裁成微信封面比例，并压到 thumb 素材 64KB 以内。"""
    try:
        image = Image.open(BytesIO(content)).convert("RGB")
    except OSError as exc:
        raise PublishFailed("首图无法作为封面") from exc
    width, height = image.size
    if width < 2 or height < 2:
        raise PublishFailed("首图尺寸过小，无法作为封面")
    target_h = max(int(width / COVER_RATIO), 1)
    if target_h < height:
        top = (height - target_h) // 2
        image = image.crop((0, top, width, top + target_h))
    else:
        target_w = min(max(int(height * COVER_RATIO), 1), width)
        left = (width - target_w) // 2
        image = image.crop((left, 0, left + target_w, height))
    cover_h = max(int(COVER_WIDTH / COVER_RATIO), 1)
    image = image.resize((COVER_WIDTH, cover_h), Image.Resampling.LANCZOS)
    for quality in (85, 75, 65, 55, 45, 35, 25):
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
        payload = buffer.getvalue()
        if len(payload) <= THUMB_MAX_BYTES:
            return payload
        image = image.resize(
            (max(image.width * 4 // 5, 320), max(int(image.width * 4 // 5 / COVER_RATIO), 136)),
            Image.Resampling.LANCZOS,
        )
    raise PublishFailed("封面压缩后仍超过微信 64KB 限制")


class WeChatOfficialPublisher:
    def __init__(self) -> None:
        self._token: str | None = None

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        if not settings.wechat_configured:
            raise PublishFailed("未配置微信 AppId / AppSecret")
        resp = await client.get(
            TOKEN_URL,
            params={
                "grant_type": "client_credential",
                "appid": settings.wechat_app_id,
                "secret": settings.wechat_app_secret,
            },
            timeout=20,
        )
        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise PublishFailed(f"获取 access_token 失败: {data}")
        self._token = token
        return token

    def _cover_bytes(self) -> bytes:
        cache = Path("data/cover.jpg")
        cache.parent.mkdir(parents=True, exist_ok=True)
        if cache.exists():
            return cache.read_bytes()
        image = Image.new("RGB", (900, 500), "#1f6f4a")
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()
        draw.text((80, 220), "FitLife", fill="white", font=font)
        buf = BytesIO()
        image.save(buf, format="JPEG", quality=85)
        payload = buf.getvalue()
        cache.write_bytes(payload)
        return payload

    async def _draft_cover_bytes(
        self, client: httpx.AsyncClient, content_html: str
    ) -> bytes:
        src = _first_image_src(content_html)
        if not src:
            return self._cover_bytes()
        content, _, _ = await self._download_image(client, src)
        return _cover_from_image(content)

    async def _thumb_media_id(
        self, client: httpx.AsyncClient, token: str, cover: bytes
    ) -> str:
        files = {"media": ("cover.jpg", cover, "image/jpeg")}
        resp = await client.post(
            MATERIAL_URL,
            params={"access_token": token, "type": "thumb"},
            files=files,
            timeout=30,
        )
        data = resp.json()
        media_id = data.get("media_id")
        if not media_id:
            raise PublishFailed(f"上传封面失败: {data}")
        return media_id

    async def _assert_public_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise PublishFailed(f"正文图片地址无效: {url}")
        try:
            addresses = await asyncio.to_thread(
                socket.getaddrinfo,
                parsed.hostname,
                parsed.port or (443 if parsed.scheme == "https" else 80),
            )
        except socket.gaierror as exc:
            raise PublishFailed(f"无法解析正文图片域名: {parsed.hostname}") from exc
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                raise PublishFailed("正文图片地址不可指向内网或本机")

    def _jpeg_under_limit(self, image: Image.Image, url: str) -> tuple[bytes, str, str]:
        image.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
        for quality in (88, 78, 68, 58):
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=quality, optimize=True)
            if len(buffer.getvalue()) <= WECHAT_IMAGE_MAX_BYTES:
                return buffer.getvalue(), "image/jpeg", "article.jpg"
            image.thumbnail(
                (max(image.width * 4 // 5, 1), max(image.height * 4 // 5, 1)),
                Image.Resampling.LANCZOS,
            )
        raise PublishFailed(f"正文图片压缩后仍超过微信 1MB 限制: {url}")

    async def _download_image(
        self, client: httpx.AsyncClient, url: str
    ) -> tuple[bytes, str, str]:
        local = read_media(url)
        if local is not None:
            return local, "image/jpeg", "article.jpg"
        if urlparse(url).path.startswith("/media/"):
            raise PublishFailed(f"正文图片文件不存在: {url}")
        await self._assert_public_url(url)
        response = await client.get(
            url,
            follow_redirects=True,
            timeout=30,
            headers={"Referer": "https://mp.weixin.qq.com/"},
        )
        response.raise_for_status()
        await self._assert_public_url(str(response.url))
        content_type = response.headers.get("content-type", "").split(";")[0]
        if not content_type.startswith("image/"):
            raise PublishFailed(f"正文图片返回的不是图片: {url}")
        if len(response.content) > MAX_IMAGE_BYTES:
            raise PublishFailed(f"正文图片超过 10MB: {url}")
        host = urlparse(str(response.url)).netloc
        watermarked = (
            host.endswith("qpic.cn")
            or host.endswith("qlogo.cn")
            or host.endswith("weixin.qq.com")
        )
        if watermarked:
            try:
                cleaned = strip_watermark_bytes(response.content)
            except OSError as exc:
                raise PublishFailed(f"正文图片格式无法转换: {url}") from exc
            if len(cleaned) <= WECHAT_IMAGE_MAX_BYTES:
                return cleaned, "image/jpeg", "article.jpg"
            return self._jpeg_under_limit(Image.open(BytesIO(cleaned)), url)
        if (
            content_type in ("image/jpeg", "image/png")
            and len(response.content) <= WECHAT_IMAGE_MAX_BYTES
        ):
            suffix = content_type.removeprefix("image/").replace("jpeg", "jpg")
            return response.content, content_type, f"article.{suffix}"
        try:
            image = Image.open(BytesIO(response.content)).convert("RGB")
        except OSError as exc:
            raise PublishFailed(f"正文图片格式无法转换: {url}") from exc
        return self._jpeg_under_limit(image, url)

    async def _upload_content_image(
        self, client: httpx.AsyncClient, token: str, source_url: str
    ) -> str:
        try:
            content, content_type, filename = await self._download_image(
                client, source_url
            )
            response = await client.post(
                UPLOAD_IMG_URL,
                params={"access_token": token},
                files={"media": (filename, content, content_type)},
                timeout=30,
            )
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise PublishFailed(f"正文图片转存失败: {source_url}") from exc
        uploaded_url = data.get("url")
        if not uploaded_url:
            raise PublishFailed(f"微信正文图片上传失败: {data}")
        return str(uploaded_url)

    async def _prepare_content_images(
        self, client: httpx.AsyncClient, token: str, content_html: str
    ) -> str:
        soup = BeautifulSoup(content_html, "html.parser")
        images = soup.find_all("img")
        for image in images:
            source_url = str(image.get("src") or "")
            if not source_url:
                raise PublishFailed("正文中存在没有地址的图片")
            image["src"] = await self._upload_content_image(
                client, token, source_url
            )
        return str(soup)

    async def publish_draft(
        self,
        *,
        title: str,
        author: str,
        digest: str,
        content_html: str,
        source_url: str,
        auto_publish: bool,
    ) -> PublishResult:
        async with httpx.AsyncClient() as client:
            token = await self._access_token(client)
            cover = await self._draft_cover_bytes(client, content_html)
            thumb = await self._thumb_media_id(client, token, cover)
            content_html = await self._prepare_content_images(
                client, token, content_html
            )
            # 草稿不写作者，也不写阅读原文链接。
            _ = (author, source_url)
            payload = {
                "articles": [
                    {
                        "title": title[:64],
                        "digest": digest[:120],
                        "content": content_html,
                        "thumb_media_id": thumb,
                        "need_open_comment": 0,
                        "only_fans_can_comment": 0,
                    }
                ]
            }
            draft = await client.post(
                DRAFT_ADD_URL, params={"access_token": token}, json=payload, timeout=30
            )
            draft_data = draft.json()
            media_id = draft_data.get("media_id")
            if not media_id:
                raise PublishFailed(f"创建草稿失败: {draft_data}")
            publish_id = None
            if auto_publish:
                pub = await client.post(
                    PUBLISH_URL,
                    params={"access_token": token},
                    json={"media_id": media_id},
                    timeout=30,
                )
                pub_data = pub.json()
                publish_id = pub_data.get("publish_id")
                errcode = pub_data.get("errcode")
                if errcode not in (0, None) and not publish_id:
                    if errcode == 48001:
                        raise PublishFailed(
                            "草稿已写入微信草稿箱，但当前公众号未开通「发布」接口权限"
                            f"（media_id={media_id}）。请在 mp.weixin.qq.com 草稿箱里手动点发表。"
                        )
                    raise PublishFailed(f"提交发表失败: {pub_data}")
            return PublishResult(draft_media_id=media_id, publish_id=publish_id)
