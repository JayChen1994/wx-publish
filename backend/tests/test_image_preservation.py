from io import BytesIO

import httpx
import pytest
from PIL import Image

from app.core.errors import PublishFailed
from app.infrastructure.llm.openai_polisher import (
    _protect_images,
    _restore_images,
)
from app.infrastructure.wechat.publisher import (
    THUMB_MAX_BYTES,
    WeChatOfficialPublisher,
    _cover_from_image,
    _first_image_src,
)
from PIL import Image
from io import BytesIO


def test_llm_placeholders_restore_all_original_images() -> None:
    source = (
        '<p>动作一</p><img src="https://img.example.com/1.jpg">'
        '<p>动作二</p><img src="https://img.example.com/2.jpg">'
    )
    protected, images = _protect_images(source)

    assert protected.count("[[IMAGE_") == 2
    restored = _restore_images(
        "<h2>润色后</h2>[[IMAGE_1]]<p>新段落</p>", images
    )

    assert restored.count("<img") == 2
    assert "https://img.example.com/1.jpg" in restored
    assert "https://img.example.com/2.jpg" in restored


class FakeImagePublisher(WeChatOfficialPublisher):
    async def _upload_content_image(
        self, client: httpx.AsyncClient, token: str, source_url: str
    ) -> str:
        filename = source_url.rsplit("/", 1)[-1]
        return f"https://mmbiz.qpic.cn/uploaded/{filename}"


@pytest.mark.asyncio
async def test_publish_replaces_every_image_with_wechat_url() -> None:
    html = (
        '<p>动作一</p><img src="https://origin.example.com/1.jpg">'
        '<p>动作二</p><img src="https://origin.example.com/2.jpg">'
    )
    async with httpx.AsyncClient() as client:
        prepared = await FakeImagePublisher()._prepare_content_images(
            client, "token", html
        )

    assert "origin.example.com" not in prepared
    assert prepared.count("https://mmbiz.qpic.cn/uploaded/") == 2


def test_cover_is_center_crop_of_first_image() -> None:
    html = (
        '<p>引子</p><img src="https://cdn.example.com/first.jpg">'
        '<img src="https://cdn.example.com/second.jpg">'
    )
    assert _first_image_src(html) == "https://cdn.example.com/first.jpg"

    image = Image.new("RGB", (600, 600), (0, 0, 255))
    draw_top = Image.new("RGB", (600, 180), (255, 0, 0))
    image.paste(draw_top, (0, 0))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    cover = _cover_from_image(buffer.getvalue())
    opened = Image.open(BytesIO(cover))

    assert opened.format == "JPEG"
    assert len(cover) <= THUMB_MAX_BYTES
    assert opened.size[0] / opened.size[1] == pytest.approx(2.35, rel=0.03)
    # 上下被裁掉，封面中心应仍是蓝色而不是顶部红条
    pixel = opened.getpixel((opened.size[0] // 2, opened.size[1] // 2))
    assert isinstance(pixel, tuple)
    assert pixel[2] > pixel[0]


@pytest.mark.asyncio
async def test_publish_rejects_private_image_url() -> None:
    with pytest.raises(PublishFailed, match="内网或本机"):
        await WeChatOfficialPublisher()._assert_public_url(
            "http://127.0.0.1/private.jpg"
        )
