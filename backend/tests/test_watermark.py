from io import BytesIO

from PIL import Image, ImageDraw

from app.infrastructure.images import strip_corner_watermark


def test_bottom_right_badge_is_covered() -> None:
    image = Image.new("RGB", (400, 300), (10, 80, 160))
    draw = ImageDraw.Draw(image)
    draw.rectangle((280, 250, 392, 292), fill=(255, 255, 255))

    cleaned = strip_corner_watermark(image)
    pixel = cleaned.getpixel((350, 275))

    assert isinstance(pixel, tuple)
    assert pixel[0] < 80
    assert pixel[2] > 80


def test_strip_watermark_bytes_returns_jpeg() -> None:
    from app.infrastructure.images import strip_watermark_bytes

    image = Image.new("RGB", (200, 180), (20, 40, 60))
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    cleaned = Image.open(BytesIO(strip_watermark_bytes(buffer.getvalue())))
    assert cleaned.format == "JPEG"
