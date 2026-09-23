"""正文图片落地，并盖掉右下角公众号水印。"""

from __future__ import annotations

import hashlib
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from PIL import Image

MEDIA_DIR = Path("data/media")
MEDIA_URL_PREFIX = "/media/"
_MEDIA_NAME = re.compile(r"^[a-f0-9]{16}\.jpg$")


def strip_corner_watermark(image: Image.Image) -> Image.Image:
    """用右下角上方的画面盖住公众号水印区域，边缘做渐变避免硬切。"""
    rgb = image.convert("RGB")
    width, height = rgb.size
    if width < 160 or height < 160:
        return rgb
    badge_w = min(int(width * 0.30), 420)
    badge_h = min(max(int(height * 0.10), 44), int(height * 0.16))
    margin_x = max(int(width * 0.012), 6)
    margin_y = max(int(height * 0.012), 6)
    x1 = width - margin_x
    y1 = height - margin_y
    x0 = max(0, x1 - badge_w)
    y0 = max(0, y1 - badge_h)
    patch_w = x1 - x0
    patch_h = y1 - y0
    src_y0 = y0 - patch_h
    if src_y0 < 0 or patch_w < 8 or patch_h < 8:
        return rgb

    donor = rgb.crop((x0, src_y0, x1, y0))
    base = rgb.crop((x0, y0, x1, y1))
    mask = Image.new("L", (patch_w, patch_h), 0)
    pixels = mask.load()
    fade_y = max(int(patch_h * 0.35), 1)
    fade_x = max(int(patch_w * 0.18), 1)
    for y in range(patch_h):
        y_alpha = 255 if y >= fade_y else int(255 * y / fade_y)
        for x in range(patch_w):
            x_alpha = 255 if x >= fade_x else int(255 * x / fade_x)
            pixels[x, y] = min(x_alpha, y_alpha)
    rgb.paste(Image.composite(donor, base, mask), (x0, y0))
    return rgb


def strip_watermark_bytes(content: bytes) -> bytes:
    image = strip_corner_watermark(Image.open(BytesIO(content)))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90, optimize=True)
    return buffer.getvalue()


def save_media(content: bytes) -> str:
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(content).hexdigest()[:16] + ".jpg"
    path = MEDIA_DIR / name
    if not path.exists():
        path.write_bytes(content)
    return f"{MEDIA_URL_PREFIX}{name}"


def read_media(url: str) -> bytes | None:
    path = urlparse(url).path
    name = Path(path).name
    if not path.startswith(MEDIA_URL_PREFIX) or not _MEDIA_NAME.fullmatch(name):
        return None
    file = (MEDIA_DIR / name).resolve()
    root = MEDIA_DIR.resolve()
    if root != file.parent:
        return None
    if not file.is_file():
        return None
    return file.read_bytes()


def _needs_watermark_removal(page_url: str, image_url: str) -> bool:
    hosts = (urlparse(page_url).netloc, urlparse(image_url).netloc)
    return any(
        host.endswith("weixin.qq.com") or host.endswith("qpic.cn") or host.endswith("qlogo.cn")
        for host in hosts
    )


async def localize_images(
    client: httpx.AsyncClient, html: str, *, page_url: str
) -> str:
    """下载公众号图片、去掉右下角水印，改写成站内地址供预览和发布。"""
    soup = BeautifulSoup(html, "html.parser")
    cache: dict[str, str] = {}
    for image in soup.find_all("img"):
        source = str(image.get("src") or "").strip()
        if not source.startswith(("http://", "https://")):
            continue
        if source in cache:
            image["src"] = cache[source]
            continue
        if not _needs_watermark_removal(page_url, source):
            continue
        try:
            response = await client.get(
                source,
                follow_redirects=True,
                timeout=30,
                headers={"Referer": page_url},
            )
            response.raise_for_status()
            cleaned = strip_watermark_bytes(response.content)
        except (httpx.HTTPError, OSError, ValueError):
            continue
        local = save_media(cleaned)
        cache[source] = local
        image["src"] = local
    return str(soup)
