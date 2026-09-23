from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.infrastructure.db.tables import Base


def _ensure_sqlite_dir(url: str) -> None:
    if "sqlite" in url and "///./" in url:
        Path("./data").mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(settings.database_url)
engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _existing_columns(conn, table: str) -> set[str]:
    return {column["name"] for column in inspect(conn).get_columns(table)}


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        columns = await conn.run_sync(_existing_columns, "articles")
        if "metrics" not in columns:
            await conn.execute(
                text("ALTER TABLE articles ADD COLUMN metrics VARCHAR(200) DEFAULT ''")
            )
