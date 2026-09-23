from uuid import uuid4

import httpx

from app.core.errors import AppError, ConflictError, NotFoundError
from app.domain.formatting import plain_summary
from app.domain.models import (
    Article,
    ArticleRepository,
    ArticleStatus,
    CrawledItem,
    FeedCrawler,
    PageCrawler,
    Source,
    SourceRepository,
)
from app.domain.scoring import score_article
from app.infrastructure.images import localize_images


def _to_article(item: CrawledItem, source_id: str | None, topics: str) -> Article:
    return Article(
        id=str(uuid4()),
        source_id=source_id,
        title=item.title,
        summary=item.summary,
        body_html=item.body_html,
        source_url=item.source_url,
        author=item.author,
        status=ArticleStatus.INGESTED,
        quality_score=score_article(
            title=item.title, summary=item.summary, body=item.body_html
        ),
        topics=topics,
        metrics=item.metrics,
    )


class SourceService:
    def __init__(self, sources: SourceRepository) -> None:
        self._sources = sources

    async def list(self) -> list[Source]:
        return await self._sources.list_all()

    async def create(self, source: Source) -> Source:
        return await self._sources.add(source)

    async def delete(self, source_id: str) -> None:
        existing = await self._sources.get(source_id)
        if not existing:
            raise NotFoundError("来源不存在")
        await self._sources.delete(source_id)


class IngestArticlesService:
    def __init__(
        self,
        sources: SourceRepository,
        articles: ArticleRepository,
        crawler: FeedCrawler,
    ) -> None:
        self._sources = sources
        self._articles = articles
        self._crawler = crawler

    async def ingest(self, source_id: str | None = None) -> tuple[int, int]:
        created = 0
        skipped = 0
        if source_id:
            source = await self._sources.get(source_id)
            targets = [source] if source else []
        else:
            targets = await self._sources.list_all(enabled_only=True)
        for source in targets:
            items = await self._crawler.fetch(source)
            await self._sources.touch_crawled(source.id)
            for item in items:
                if await self._articles.get_by_source_url(item.source_url):
                    skipped += 1
                    continue
                await self._articles.add(_to_article(item, source.id, source.topics))
                created += 1
        return created, skipped


class SubmitArticleService:
    """人工提交一条公开文章链接，直接抓取入库。"""

    def __init__(self, articles: ArticleRepository, crawler: PageCrawler) -> None:
        self._articles = articles
        self._crawler = crawler

    async def submit(self, url: str, topics: str) -> Article:
        if await self._articles.get_by_source_url(url):
            raise ConflictError("该链接已入库")
        item = await self._crawler.fetch_one(url)
        return await self._articles.add(_to_article(item, None, topics))

    async def submit_many(self, urls: list[str], topics: str) -> tuple[int, int, list[str]]:
        created = 0
        skipped = 0
        failures: list[str] = []
        for url in urls:
            try:
                await self.submit(url, topics)
                created += 1
            except ConflictError:
                skipped += 1
            except AppError as exc:
                failures.append(f"{url} → {exc.message}")
        return created, skipped, failures

    async def create_from_link(
        self, title: str, url: str, topics: str, author: str = ""
    ) -> Article:
        """按标题和原文链接抓取正文；图片在抓取时去掉右下角水印。"""
        if await self._articles.get_by_source_url(url):
            raise ConflictError("该链接已入库")
        item = await self._crawler.fetch_one(url)
        item.title = title.strip() or item.title
        if author.strip():
            item.author = author.strip()
        item.summary = plain_summary(item.body_html)
        return await self._articles.add(_to_article(item, None, topics))

    async def create_pasted(self, item: CrawledItem, topics: str) -> Article:
        """粘贴录入：保留正文，公众号图片去水印后改成本地地址。"""
        if await self._articles.get_by_source_url(item.source_url):
            raise ConflictError("该链接已入库")
        async with httpx.AsyncClient(timeout=30) as client:
            item.body_html = await localize_images(
                client, item.body_html, page_url=item.source_url
            )
        item.summary = plain_summary(item.body_html)
        return await self._articles.add(_to_article(item, None, topics))


class EditorialService:
    def __init__(self, articles: ArticleRepository) -> None:
        self._articles = articles

    async def list(self, status: ArticleStatus | None = None) -> list[Article]:
        return await self._articles.list(status=status)

    async def get(self, article_id: str) -> Article:
        article = await self._articles.get(article_id)
        if not article:
            raise NotFoundError("文章不存在")
        return article

    async def update(self, article_id: str, **fields: str | None) -> Article:
        article = await self.get(article_id)
        for key, value in fields.items():
            if value is not None:
                setattr(article, key, value)
        article.quality_score = score_article(article)
        await self._articles.save(article)
        return article

    async def approve(self, article_id: str) -> Article:
        article = await self.get(article_id)
        article.approve()
        await self._articles.save(article)
        return article

    async def reject(self, article_id: str) -> Article:
        article = await self.get(article_id)
        article.reject()
        await self._articles.save(article)
        return article
