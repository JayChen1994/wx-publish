import asyncio
import html
import re

import feedparser

from app.domain.models import CrawledItem, Source


def _entry_html(entry: object) -> str:
    content = getattr(entry, "content", None)
    if content:
        value = content[0].get("value") if isinstance(content[0], dict) else getattr(content[0], "value", "")
        if value:
            return str(value)
    summary = getattr(entry, "summary", "") or ""
    if summary:
        return str(summary)
    title = html.escape(getattr(entry, "title", "") or "")
    return f"<p>{title}</p>"


def _plain(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


class RssFeedCrawler:
    async def fetch(self, source: Source) -> list[CrawledItem]:
        parsed = await asyncio.to_thread(feedparser.parse, source.url)
        items: list[CrawledItem] = []
        for entry in parsed.entries:
            link = getattr(entry, "link", "") or ""
            if not link:
                continue
            body = _entry_html(entry)
            summary = _plain(getattr(entry, "summary", "") or body)[:240]
            items.append(
                CrawledItem(
                    title=(getattr(entry, "title", None) or "未命名").strip(),
                    summary=summary,
                    body_html=body,
                    source_url=link.strip(),
                    author=(getattr(entry, "author", None) or source.name).strip(),
                )
            )
        return items
