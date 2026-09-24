import asyncio
import re
import time
from html import escape
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag

from app.core.config import settings
from app.core.errors import AppError
from app.domain.models import CrawledItem, Source, SourceKind

# 站点专用选择器。抓不到时回落到通用正文识别。
SITE_RULES: dict[str, dict[str, list[str]]] = {
    "mp.weixin.qq.com": {
        "title": ["#activity-name", "h1"],
        "author": ["#js_name", "#meta_content .rich_media_meta_text"],
        "body": ["#js_content"],
    },
    "www.toutiao.com": {
        "title": ["h1"],
        "author": [".article-meta .name", ".author-info__name"],
        "body": ["article", ".article-content"],
    },
}

METRIC_PATTERNS = (
    re.compile(r"(阅读|浏览)\s*[:：]?\s*([\d.,]+\s*[万千]?)"),
    re.compile(r"(点赞|赞|在看)\s*[:：]?\s*([\d.,]+\s*[万千]?)"),
    re.compile(r"(收藏)\s*[:：]?\s*([\d.,]+\s*[万千]?)"),
)


class CrawlBlocked(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 422)


class _DomainThrottle:
    """同一域名串行且按 crawl_delay_seconds 间隔请求，避免给对方站点压力。"""

    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._last_hit: dict[str, float] = {}

    async def wait(self, host: str) -> None:
        lock = self._locks.setdefault(host, asyncio.Lock())
        async with lock:
            elapsed = time.monotonic() - self._last_hit.get(host, 0.0)
            remaining = settings.crawl_delay_seconds - elapsed
            if remaining > 0:
                await asyncio.sleep(remaining)
            self._last_hit[host] = time.monotonic()


def _first_match(soup: BeautifulSoup, selectors: list[str]) -> Tag | None:
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            return node
    return None


def _guess_body(soup: BeautifulSoup) -> Tag | None:
    candidates = soup.select("article, main, div")
    best: Tag | None = None
    best_len = 0
    for node in candidates:
        length = len(node.get_text(strip=True))
        if length > best_len:
            best, best_len = node, length
    return best if best_len >= 200 else None


_SKIP_TAGS = {"script", "style", "iframe", "noscript", "template", "svg"}
_BLOCK_TAGS = {"p", "h2", "h3", "blockquote", "li"}
_LIST_TAGS = {"ul", "ol"}


def _img_tag(image: Tag) -> str:
    source = (image.get("data-src") or image.get("src") or "").strip()
    if not source.startswith(("http://", "https://")):
        return ""
    alt = image.get("alt") or ""
    if isinstance(alt, list):
        alt = alt[0] if alt else ""
    return f'<img src="{escape(source, quote=True)}" alt="{escape(str(alt))}">'


def _inline_html(node: Tag) -> str:
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            text = str(child).strip()
            if text:
                parts.append(escape(text))
            continue
        if not isinstance(child, Tag) or child.name in _SKIP_TAGS:
            continue
        if child.name == "br":
            parts.append("<br>")
            continue
        if child.name in ("strong", "em"):
            inner = _inline_html(child)
            if inner:
                parts.append(f"<{child.name}>{inner}</{child.name}>")
            continue
        if child.name == "img":
            tag = _img_tag(child)
            if tag:
                parts.append(tag)
            continue
        parts.append(_inline_html(child))
    return "".join(parts)


def _render_blocks(node: Tag) -> str:
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            text = str(child).strip()
            if len(text) >= 2:
                parts.append(f"<p>{escape(text)}</p>")
            continue
        if not isinstance(child, Tag) or child.name in _SKIP_TAGS:
            continue
        if child.name == "img":
            tag = _img_tag(child)
            if tag:
                parts.append(tag)
            continue
        if child.name in _BLOCK_TAGS:
            inner = _inline_html(child)
            if not inner:
                continue
            tag_name = child.name if child.name in ("h2", "h3", "blockquote", "li") else "p"
            parts.append(f"<{tag_name}>{inner}</{tag_name}>")
            continue
        if child.name in _LIST_TAGS:
            inner = _render_blocks(child)
            if inner:
                parts.append(f"<{child.name}>{inner}</{child.name}>")
            continue
        parts.append(_render_blocks(child))
    return "".join(parts)


def _clean_body(node: Tag) -> str:
    rendered = _render_blocks(node)
    if rendered:
        return rendered
    text = node.get_text("\n", strip=True)
    return "".join(f"<p>{escape(line)}</p>" for line in text.split("\n") if line.strip())


def _extract_metrics(soup: BeautifulSoup) -> str:
    text = soup.get_text(" ", strip=True)[:4000]
    found = []
    for pattern in METRIC_PATTERNS:
        match = pattern.search(text)
        if match:
            found.append(f"{match.group(1)} {match.group(2).strip()}")
    return " · ".join(found)


class HtmlArticleCrawler:
    """抓取公开文章页。遵守 robots，限速，不处理登录/验证码页面。"""

    def __init__(self) -> None:
        self._throttle = _DomainThrottle()
        self._robots: dict[str, RobotFileParser | None] = {}

    async def _allowed(self, client: httpx.AsyncClient, url: str) -> bool:
        if not settings.crawl_respect_robots:
            return True
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._robots:
            parser: RobotFileParser | None = RobotFileParser()
            try:
                resp = await client.get(f"{origin}/robots.txt", timeout=10)
                if resp.status_code == 200:
                    parser.parse(resp.text.splitlines())
                else:
                    parser = None
            except httpx.HTTPError:
                parser = None
            self._robots[origin] = parser
        parser = self._robots[origin]
        if parser is None:
            return True
        return parser.can_fetch(settings.crawl_user_agent, url)

    async def _get(self, client: httpx.AsyncClient, url: str) -> str:
        if not await self._allowed(client, url):
            raise CrawlBlocked(f"robots.txt 不允许抓取该地址：{url}")
        await self._throttle.wait(urlparse(url).netloc)
        headers: dict[str, str] = {}
        if urlparse(url).netloc == "mp.weixin.qq.com":
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Mobile/15E148 MicroMessenger/8.0.38 NetType/WIFI Language/zh_CN"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://mp.weixin.qq.com/",
            }
        resp = await client.get(url, follow_redirects=True, headers=headers or None)
        if resp.status_code in (401, 403):
            raise CrawlBlocked("目标页面需要登录或已拒绝访问，请改用官方授权接口")
        resp.raise_for_status()
        return resp.text

    def _parse(self, url: str, html: str) -> CrawledItem:
        if "环境异常" in html and "js_content" not in html:
            raise CrawlBlocked(
                "微信返回验证页，服务器无法自动打开该链接。"
                "请粘贴正文，或稍后在浏览器复制完整链接再试。"
            )
        plain = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
        if "参数错误" in plain and "js_content" not in html:
            raise CrawlBlocked(
                "微信返回「参数错误」：链接不完整或仅能在微信内打开。"
                "请在文章里点「··· → 复制链接」获取带 __biz= 的完整地址；"
                "或在下方粘贴从微信复制的正文（含图片）。"
            )
        soup = BeautifulSoup(html, "lxml")
        rules = SITE_RULES.get(urlparse(url).netloc, {})

        title_node = _first_match(soup, rules.get("title", ["h1"]))
        title = title_node.get_text(strip=True) if title_node else ""
        if not title and soup.title:
            title = soup.title.get_text(strip=True)

        author_node = _first_match(soup, rules.get("author", []))
        author = author_node.get_text(strip=True) if author_node else urlparse(url).netloc

        body_node = _first_match(soup, rules.get("body", [])) or _guess_body(soup)
        if body_node is None:
            raise CrawlBlocked(
                "未能从页面提取正文，可能是动态渲染或需要登录，请人工粘贴内容"
            )
        body_html = _clean_body(body_node)
        summary = re.sub(r"<[^>]+>", "", body_html)[:240]

        return CrawledItem(
            title=title or "未命名",
            summary=summary,
            body_html=body_html,
            source_url=url,
            author=author,
            metrics=_extract_metrics(soup),
        )

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=settings.crawl_timeout_seconds,
            headers={"User-Agent": settings.crawl_user_agent},
        )

    async def fetch_one(self, url: str) -> CrawledItem:
        from app.infrastructure.images import localize_images

        async with self._client() as client:
            item = self._parse(url, await self._get(client, url))
            item.body_html = await localize_images(
                client, item.body_html, page_url=url
            )
            item.summary = re.sub(r"<[^>]+>", "", item.body_html)[:240]
            return item

    async def fetch(self, source: Source) -> list[CrawledItem]:
        async with self._client() as client:
            if source.kind == SourceKind.HTML_PAGE:
                return [self._parse(source.url, await self._get(client, source.url))]

            listing = await self._get(client, source.url)
            links = self._collect_links(source.url, listing)
            items: list[CrawledItem] = []
            for link in links[: settings.crawl_max_items_per_source]:
                try:
                    items.append(self._parse(link, await self._get(client, link)))
                except (CrawlBlocked, httpx.HTTPError):
                    continue
            return items

    def _collect_links(self, base_url: str, html: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        host = urlparse(base_url).netloc
        seen: dict[str, None] = {}
        for anchor in soup.find_all("a", href=True):
            link = urljoin(base_url, anchor["href"]).split("#")[0]
            parsed = urlparse(link)
            if parsed.scheme not in ("http", "https") or parsed.netloc != host:
                continue
            if link.rstrip("/") == base_url.rstrip("/"):
                continue
            seen.setdefault(link, None)
        return list(seen)
