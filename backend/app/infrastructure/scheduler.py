from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.application.editorial import IngestArticlesService
from app.core.config import settings
from app.infrastructure.crawler.rss import RssFeedCrawler
from app.infrastructure.db.repositories import SqlArticleRepository, SqlSourceRepository
from app.infrastructure.db.session import SessionLocal

scheduler = AsyncIOScheduler()


async def _scheduled_ingest() -> None:
    async with SessionLocal() as session:
        svc = IngestArticlesService(
            SqlSourceRepository(session), SqlArticleRepository(session), RssFeedCrawler()
        )
        await svc.ingest()


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        _scheduled_ingest,
        "interval",
        minutes=settings.crawl_interval_minutes,
        id="ingest",
        replace_existing=True,
    )
    scheduler.start()
