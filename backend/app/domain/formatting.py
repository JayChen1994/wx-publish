import html
import re

HEADING_MAX_LEN = 30
_TAG_RE = re.compile(r"<[a-zA-Z/][^>]*>")


def looks_like_html(text: str) -> bool:
    return bool(_TAG_RE.search(text))


def text_to_wechat_html(text: str) -> str:
    """把从原文复制来的纯文本整理成公众号可用的段落结构。"""
    blocks: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        escaped = html.escape(line)
        if len(line) <= HEADING_MAX_LEN and not line.endswith(("。", "，", "；", "：")):
            blocks.append(f"<h2>{escaped}</h2>")
        else:
            blocks.append(f"<p>{escaped}</p>")
    return "".join(blocks)


def normalize_body(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    return text if looks_like_html(text) else text_to_wechat_html(text)


def plain_summary(body_html: str, limit: int = 240) -> str:
    return re.sub(r"<[^>]+>", "", body_html).strip()[:limit]
