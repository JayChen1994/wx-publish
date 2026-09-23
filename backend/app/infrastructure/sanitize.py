import re

import bleach
from bleach.css_sanitizer import CSSSanitizer
from bs4 import BeautifulSoup

ALLOWED_TAGS = [
    "p",
    "h2",
    "h3",
    "strong",
    "em",
    "blockquote",
    "ul",
    "ol",
    "li",
    "a",
    "br",
    "img",
]
ALLOWED_ATTRIBUTES = {
    "a": ["href"],
    "img": ["src", "alt", "title", "style"],
}
ALLOWED_PROTOCOLS = ["http", "https"]
IMAGE_STYLE = "max-width:100%;height:auto;display:block;margin:16px auto"
CSS_SANITIZER = CSSSanitizer(
    allowed_css_properties=["max-width", "height", "display", "margin"]
)

# bleach 的 strip 会保留被删标签的文本，脚本正文必须连内容一起丢掉。
_DROP_WITH_CONTENT = re.compile(
    r"<(script|style|iframe|noscript|template)\b[^>]*>.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)


def drop_dangerous_blocks(html: str) -> str:
    """整块丢弃脚本/样式，避免其文本被后续当成正文分段。"""
    return _DROP_WITH_CONTENT.sub("", html)


def _is_persistable_image_src(source: str) -> bool:
    if source.startswith(("http://", "https://")):
        return True
    # 抓取后 localize 到本机 /media，预览与发布都要保留
    return source.startswith("/media/")


def normalize_remote_images(html: str) -> str:
    """把懒加载 data-src 转成 src，并丢弃不可持久化的 blob/data 图片。"""
    soup = BeautifulSoup(html, "html.parser")
    for image in soup.find_all("img"):
        source = (image.get("src") or image.get("data-src") or "").strip()
        if not _is_persistable_image_src(source):
            image.decompose()
            continue
        image.attrs = {
            "src": source,
            "alt": image.get("alt", ""),
            "title": image.get("title", ""),
            "style": IMAGE_STYLE,
        }
    return str(soup)


def extract_image_tags(html: str) -> list[str]:
    soup = BeautifulSoup(normalize_remote_images(html), "html.parser")
    return [str(image) for image in soup.find_all("img")]


def sanitize_wechat_html(html: str) -> str:
    """只保留公众号正文支持的标签，丢弃脚本、样式和事件属性。"""
    return bleach.clean(
        normalize_remote_images(drop_dangerous_blocks(html)),
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        css_sanitizer=CSS_SANITIZER,
        strip=True,
    )
