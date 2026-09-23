from uuid import uuid4

import pytest

from app.application.editorial import IngestArticlesService, SubmitArticleService
from app.application.polishing import PolishArticleService
from app.application.publishing import PublishArticleService
from app.core.errors import ConflictError
from app.domain.models import (
    Article,
    ArticleStatus,
    CrawledItem,
    PolishedContent,
    PublishResult,
    Source,
    SourceKind,
)


class MemSources:
    def __init__(self, sources: list[Source]) -> None:
        self.items = {s.id: s for s in sources}

    async def list_all(self, enabled_only: bool = False) -> list[Source]:
        values = list(self.items.values())
        return [s for s in values if s.enabled] if enabled_only else values

    async def get(self, source_id: str) -> Source | None:
        return self.items.get(source_id)

    async def add(self, source: Source) -> Source:
        self.items[source.id] = source
        return source

    async def save(self, source: Source) -> None:
        self.items[source.id] = source

    async def delete(self, source_id: str) -> None:
        self.items.pop(source_id, None)

    async def touch_crawled(self, source_id: str) -> None:
        return None


class MemArticles:
    def __init__(self) -> None:
        self.items: dict[str, Article] = {}

    async def get(self, article_id: str) -> Article | None:
        return self.items.get(article_id)

    async def get_by_source_url(self, source_url: str) -> Article | None:
        for item in self.items.values():
            if item.source_url == source_url:
                return item
        return None

    async def list(self, status: ArticleStatus | None = None, limit: int = 50, offset: int = 0):
        values = list(self.items.values())
        if status:
            values = [a for a in values if a.status == status]
        return values[offset : offset + limit]

    async def add(self, article: Article) -> Article:
        self.items[article.id] = article
        return article

    async def save(self, article: Article) -> None:
        self.items[article.id] = article


class MemPublications:
    def __init__(self) -> None:
        self.success: set[str] = set()
        self.records: list[tuple] = []

    async def has_success(self, article_id: str) -> bool:
        return article_id in self.success

    async def add(self, article_id, draft_media_id, publish_id, status, error) -> None:
        self.records.append((article_id, status, error))
        if status == "success":
            self.success.add(article_id)


class FakeCrawler:
    def __init__(self, items: list[CrawledItem]) -> None:
        self.items = items

    async def fetch(self, source: Source) -> list[CrawledItem]:
        return self.items


class FakeWeChat:
    def __init__(self) -> None:
        self.calls = 0

    async def publish_draft(self, **kwargs) -> PublishResult:
        self.calls += 1
        return PublishResult(draft_media_id="media-1", publish_id="pub-1")


class FakePolisher:
    async def polish(self, article: Article, style: str) -> PolishedContent:
        return PolishedContent(
            title=f"{article.title}｜润色版",
            summary="结构化摘要",
            body_html=(
                f"<h2>核心观点</h2><p>坚持训练。</p>"
                f"<p>内容参考：{article.author} "
                f"<a href=\"{article.source_url}\">原文</a></p>"
            ),
        )


class FakePageCrawler:
    def __init__(self, item: CrawledItem) -> None:
        self.item = item
        self.calls = 0

    async def fetch_one(self, url: str) -> CrawledItem:
        self.calls += 1
        return self.item


@pytest.mark.asyncio
async def test_submit_url_stores_metrics_and_rejects_duplicates() -> None:
    item = CrawledItem(
        title="高赞减脂经验",
        summary="摘要",
        body_html="<p>控制热量缺口</p>",
        source_url="https://www.toutiao.com/article/1",
        author="原作者",
        metrics="阅读 12万 · 点赞 3000",
    )
    articles = MemArticles()
    crawler = FakePageCrawler(item)
    svc = SubmitArticleService(articles, crawler)

    stored = await svc.submit(item.source_url, "健身减脂")
    assert stored.metrics == "阅读 12万 · 点赞 3000"
    assert stored.status == ArticleStatus.INGESTED

    with pytest.raises(ConflictError):
        await svc.submit(item.source_url, "健身减脂")
    assert crawler.calls == 1


@pytest.mark.asyncio
async def test_ingest_is_idempotent_by_source_url() -> None:
    source = Source("s1", "测试源", "https://example.com/rss", SourceKind.RSS)
    item = CrawledItem("减脂日记", "训练", "<p>力量训练</p>", "https://example.com/a1", "作者")
    articles = MemArticles()
    svc = IngestArticlesService(MemSources([source]), articles, FakeCrawler([item]))
    created, skipped = await svc.ingest()
    assert created == 1 and skipped == 0
    created, skipped = await svc.ingest()
    assert created == 0 and skipped == 1
    assert len(articles.items) == 1


@pytest.mark.asyncio
async def test_publish_requires_approved_and_is_idempotent() -> None:
    article = Article(
        id=str(uuid4()),
        source_id="s1",
        title="习惯的力量",
        summary="感悟",
        body_html="<p>坚持</p>",
        source_url="https://example.com/b",
        author="编辑",
        status=ArticleStatus.INGESTED,
        quality_score=50,
        topics="感悟",
    )
    articles = MemArticles()
    await articles.add(article)
    pubs = MemPublications()
    wechat = FakeWeChat()
    svc = PublishArticleService(articles, pubs, wechat)
    with pytest.raises(ConflictError):
        await svc.publish(article.id, auto_publish=False)
    article.approve()
    await articles.save(article)
    await svc.publish(article.id, auto_publish=False)
    assert article.status == ArticleStatus.PUBLISHED
    with pytest.raises(ConflictError):
        await svc.publish(article.id, auto_publish=False)
    assert wechat.calls == 1


@pytest.mark.asyncio
async def test_polish_updates_content_and_requires_reapproval() -> None:
    article = Article(
        id=str(uuid4()),
        source_id="s1",
        title="训练记录",
        summary="原摘要",
        body_html="<p>原正文</p>",
        source_url="https://example.com/training",
        author="原作者",
        status=ArticleStatus.APPROVED,
        quality_score=40,
        topics="健身",
    )
    articles = MemArticles()
    await articles.add(article)

    polished = await PolishArticleService(articles, FakePolisher()).polish(
        article.id, "专业"
    )

    assert polished.title.endswith("润色版")
    assert polished.status == ArticleStatus.INGESTED
    assert "内容参考" in polished.body_html
