from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.editorial import (
    EditorialService,
    IngestArticlesService,
    SourceService,
    SubmitArticleService,
)
from app.application.draft_workflow import DraftWorkflowService
from app.application.polishing import PolishArticleService
from app.application.publishing import PublishArticleService
from app.infrastructure.crawler.dispatching import DispatchingCrawler
from app.infrastructure.crawler.html_page import HtmlArticleCrawler
from app.infrastructure.crawler.rss import RssFeedCrawler
from app.infrastructure.db.repositories import (
    SqlArticleRepository,
    SqlPublicationRepository,
    SqlSourceRepository,
)
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.llm.openai_polisher import OpenAICompatiblePolisher
from app.infrastructure.wechat.publisher import WeChatOfficialPublisher


_html_crawler = HtmlArticleCrawler()
_feed_crawler = DispatchingCrawler(RssFeedCrawler(), _html_crawler)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


def get_source_service(session: AsyncSession = Depends(get_session)) -> SourceService:
    return SourceService(SqlSourceRepository(session))


def get_ingest_service(session: AsyncSession = Depends(get_session)) -> IngestArticlesService:
    return IngestArticlesService(
        SqlSourceRepository(session), SqlArticleRepository(session), _feed_crawler
    )


def get_submit_service(session: AsyncSession = Depends(get_session)) -> SubmitArticleService:
    return SubmitArticleService(SqlArticleRepository(session), _html_crawler)


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


def get_draft_workflow_service() -> DraftWorkflowService:
    return DraftWorkflowService(
        _html_crawler,
        OpenAICompatiblePolisher(),
        WeChatOfficialPublisher(),
    )
