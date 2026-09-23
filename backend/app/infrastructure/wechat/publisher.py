from __future__ import annotations

from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

from app.core.config import settings
from app.core.errors import PublishFailed
from app.domain.models import PublishResult

TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
DRAFT_ADD_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"
PUBLISH_URL = "https://api.weixin.qq.com/cgi-bin/freepublish/submit"
MATERIAL_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material"


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

    async def _thumb_media_id(self, client: httpx.AsyncClient, token: str) -> str:
        files = {"media": ("cover.jpg", self._cover_bytes(), "image/jpeg")}
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
            thumb = await self._thumb_media_id(client, token)
            payload = {
                "articles": [
                    {
                        "title": title[:64],
                        "author": author[:16],
                        "digest": digest[:120],
                        "content": content_html,
                        "content_source_url": source_url,
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
                if pub_data.get("errcode") not in (0, None) and not publish_id:
                    raise PublishFailed(f"提交发表失败: {pub_data}")
            return PublishResult(draft_media_id=media_id, publish_id=publish_id)
