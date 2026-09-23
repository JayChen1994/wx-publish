from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Article, ArticleStatus, Source, SourceKind
from app.infrastructure.db.tables import ArticleRow, PublicationRow, SourceRow


def _source_from_row(row: SourceRow) -> Source:
    return Source(
        id=row.id,
        name=row.name,
        url=row.url,
        kind=SourceKind(row.kind),
        enabled=row.enabled,
        topics=row.topics,
    )


def _article_from_row(row: ArticleRow) -> Article:
    return Article(
        id=row.id,
        source_id=row.source_id,
        title=row.title,
        summary=row.summary,
        body_html=row.body_html,
        source_url=row.source_url,
        author=row.author,
        status=ArticleStatus(row.status),
        quality_score=row.quality_score,
        topics=row.topics,
    )


class SqlSourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self, enabled_only: bool = False) -> list[Source]:
        stmt = select(SourceRow)
        if enabled_only:
            stmt = stmt.where(SourceRow.enabled.is_(True))
        rows = (await self._session.scalars(stmt)).all()
        return [_source_from_row(row) for row in rows]

    async def get(self, source_id: str) -> Source | None:
        row = await self._session.get(SourceRow, source_id)
        return _source_from_row(row) if row else None

    async def add(self, source: Source) -> Source:
        self._session.add(
            SourceRow(
                id=source.id,
                name=source.name,
                url=source.url,
                kind=source.kind.value,
                enabled=source.enabled,
                topics=source.topics,
            )
        )
        await self._session.commit()
        return source

    async def save(self, source: Source) -> None:
        row = await self._session.get(SourceRow, source.id)
        if not row:
            return
        row.name = source.name
        row.url = source.url
        row.enabled = source.enabled
        row.topics = source.topics
        await self._session.commit()

    async def delete(self, source_id: str) -> None:
        row = await self._session.get(SourceRow, source_id)
        if row:
            await self._session.delete(row)
            await self._session.commit()

    async def touch_crawled(self, source_id: str) -> None:
        from datetime import datetime, timezone

        row = await self._session.get(SourceRow, source_id)
        if row:
            row.last_crawled_at = datetime.now(timezone.utc)
            await self._session.commit()


class SqlArticleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, article_id: str) -> Article | None:
        row = await self._session.get(ArticleRow, article_id)
        return _article_from_row(row) if row else None

    async def get_by_source_url(self, source_url: str) -> Article | None:
        stmt = select(ArticleRow).where(ArticleRow.source_url == source_url)
        row = await self._session.scalar(stmt)
        return _article_from_row(row) if row else None

    async def list(
        self, status: ArticleStatus | None = None, limit: int = 50, offset: int = 0
    ) -> list[Article]:
        stmt = select(ArticleRow).order_by(ArticleRow.created_at.desc()).offset(offset).limit(limit)
        if status:
            stmt = select(ArticleRow).where(ArticleRow.status == status.value).order_by(
                ArticleRow.created_at.desc()
            ).offset(offset).limit(limit)
        rows = (await self._session.scalars(stmt)).all()
        return [_article_from_row(row) for row in rows]

    async def add(self, article: Article) -> Article:
        self._session.add(
            ArticleRow(
                id=article.id,
                source_id=article.source_id,
                title=article.title,
                summary=article.summary,
                body_html=article.body_html,
                source_url=article.source_url,
                author=article.author,
                status=article.status.value,
                quality_score=article.quality_score,
                topics=article.topics,
            )
        )
        await self._session.commit()
        return article

    async def save(self, article: Article) -> None:
        row = await self._session.get(ArticleRow, article.id)
        if not row:
            return
        row.title = article.title
        row.summary = article.summary
        row.body_html = article.body_html
        row.author = article.author
        row.status = article.status.value
        row.quality_score = article.quality_score
        row.topics = article.topics
        await self._session.commit()


class SqlPublicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def has_success(self, article_id: str) -> bool:
        stmt = select(PublicationRow).where(
            PublicationRow.article_id == article_id, PublicationRow.status == "success"
        )
        return await self._session.scalar(stmt) is not None

    async def add(
        self,
        article_id: str,
        draft_media_id: str,
        publish_id: str | None,
        status: str,
        error: str | None,
    ) -> None:
        self._session.add(
            PublicationRow(
                id=str(uuid4()),
                article_id=article_id,
                draft_media_id=draft_media_id,
                publish_id=publish_id,
                status=status,
                error=error,
            )
        )
        await self._session.commit()
