from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.editorial import EditorialService, IngestArticlesService, SourceService
from app.application.polishing import PolishArticleService
from app.application.publishing import PublishArticleService
from app.infrastructure.crawler.rss import RssFeedCrawler
from app.infrastructure.db.repositories import (
    SqlArticleRepository,
    SqlPublicationRepository,
    SqlSourceRepository,
)
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.llm.openai_polisher import OpenAICompatiblePolisher
from app.infrastructure.wechat.publisher import WeChatOfficialPublisher


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


def get_source_service(session: AsyncSession = Depends(get_session)) -> SourceService:
    return SourceService(SqlSourceRepository(session))


def get_ingest_service(session: AsyncSession = Depends(get_session)) -> IngestArticlesService:
    return IngestArticlesService(
        SqlSourceRepository(session), SqlArticleRepository(session), RssFeedCrawler()
    )


def get_editorial_service(session: AsyncSession = Depends(get_session)) -> EditorialService:
    return EditorialService(SqlArticleRepository(session))


def get_polish_service(session: AsyncSession = Depends(get_session)) -> PolishArticleService:
    return PolishArticleService(
        SqlArticleRepository(session), OpenAICompatiblePolisher()
    )


def get_publish_service(session: AsyncSession = Depends(get_session)) -> PublishArticleService:
    return PublishArticleService(
        SqlArticleRepository(session),
        SqlPublicationRepository(session),
        WeChatOfficialPublisher(),
    )
