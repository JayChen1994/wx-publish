from app.domain.models import CrawledItem, FeedCrawler, Source, SourceKind


class DispatchingCrawler:
    """按来源类型选择 RSS 或 HTML 抓取实现。"""

    def __init__(self, rss: FeedCrawler, html: FeedCrawler) -> None:
        self._rss = rss
        self._html = html

    async def fetch(self, source: Source) -> list[CrawledItem]:
        crawler = self._rss if source.kind == SourceKind.RSS else self._html
        return await crawler.fetch(source)
