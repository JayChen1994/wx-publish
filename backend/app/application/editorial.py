from uuid import uuid4

from app.core.errors import NotFoundError
from app.domain.models import Article, ArticleRepository, ArticleStatus, FeedCrawler, Source, SourceRepository
from app.domain.scoring import score_article


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
                article = Article(
                    id=str(uuid4()),
                    source_id=source.id,
                    title=item.title,
                    summary=item.summary,
                    body_html=item.body_html,
                    source_url=item.source_url,
                    author=item.author,
                    status=ArticleStatus.INGESTED,
                    quality_score=score_article(
                        title=item.title, summary=item.summary, body=item.body_html
                    ),
                    topics=source.topics,
                )
                await self._articles.add(article)
                created += 1
        return created, skipped


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
