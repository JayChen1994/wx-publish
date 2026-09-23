from enum import StrEnum
from typing import Protocol


class ArticleStatus(StrEnum):
    INGESTED = "ingested"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class SourceKind(StrEnum):
    RSS = "rss"


class Source:
    def __init__(
        self,
        id: str,
        name: str,
        url: str,
        kind: SourceKind = SourceKind.RSS,
        enabled: bool = True,
        topics: str = "健身减脂,人生感悟",
    ) -> None:
        self.id = id
        self.name = name
        self.url = url
        self.kind = kind
        self.enabled = enabled
        self.topics = topics


class Article:
    def __init__(
        self,
        id: str,
        source_id: str | None,
        title: str,
        summary: str,
        body_html: str,
        source_url: str,
        author: str,
        status: ArticleStatus,
        quality_score: int,
        topics: str,
    ) -> None:
        self.id = id
        self.source_id = source_id
        self.title = title
        self.summary = summary
        self.body_html = body_html
        self.source_url = source_url
        self.author = author
        self.status = status
        self.quality_score = quality_score
        self.topics = topics

    def approve(self) -> None:
        if self.status == ArticleStatus.PUBLISHED:
            raise ValueError("已发布文章不可改审核状态")
        if not self.title.strip() or not self.body_html.strip():
            raise ValueError("标题与正文不能为空")
        self.status = ArticleStatus.APPROVED

    def reject(self) -> None:
        if self.status == ArticleStatus.PUBLISHED:
            raise ValueError("已发布文章不可拒绝")
        self.status = ArticleStatus.REJECTED

    def mark_published(self) -> None:
        if self.status != ArticleStatus.APPROVED:
            raise ValueError("仅已审核文章可发布")
        self.status = ArticleStatus.PUBLISHED


class CrawledItem:
    def __init__(
        self,
        title: str,
        summary: str,
        body_html: str,
        source_url: str,
        author: str,
    ) -> None:
        self.title = title
        self.summary = summary
        self.body_html = body_html
        self.source_url = source_url
        self.author = author


class PublishResult:
    def __init__(self, draft_media_id: str, publish_id: str | None) -> None:
        self.draft_media_id = draft_media_id
        self.publish_id = publish_id


class PolishedContent:
    def __init__(self, title: str, summary: str, body_html: str) -> None:
        self.title = title
        self.summary = summary
        self.body_html = body_html


class SourceRepository(Protocol):
    async def list_all(self, enabled_only: bool = False) -> list[Source]: ...
    async def get(self, source_id: str) -> Source | None: ...
    async def add(self, source: Source) -> Source: ...
    async def save(self, source: Source) -> None: ...
    async def delete(self, source_id: str) -> None: ...
    async def touch_crawled(self, source_id: str) -> None: ...


class ArticleRepository(Protocol):
    async def get(self, article_id: str) -> Article | None: ...
    async def get_by_source_url(self, source_url: str) -> Article | None: ...
    async def list(
        self, status: ArticleStatus | None = None, limit: int = 50, offset: int = 0
    ) -> list[Article]: ...
    async def add(self, article: Article) -> Article: ...
    async def save(self, article: Article) -> None: ...


class PublicationRepository(Protocol):
    async def has_success(self, article_id: str) -> bool: ...
    async def add(
        self,
        article_id: str,
        draft_media_id: str,
        publish_id: str | None,
        status: str,
        error: str | None,
    ) -> None: ...


class FeedCrawler(Protocol):
    async def fetch(self, source: Source) -> list[CrawledItem]: ...


class ContentPolisher(Protocol):
    async def polish(self, article: Article, style: str) -> PolishedContent: ...


class WeChatPublisher(Protocol):
    async def publish_draft(
        self,
        *,
        title: str,
        author: str,
        digest: str,
        content_html: str,
        source_url: str,
        auto_publish: bool,
    ) -> PublishResult: ...
