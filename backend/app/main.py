from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.api.articles import router as articles_router
from app.api.draft import router as draft_router
from app.api.schemas import HealthOut
from app.api.sources import router as sources_router
from app.core.config import settings
from app.core.errors import AppError
from app.domain.models import Source, SourceKind
from app.infrastructure.db.repositories import SqlSourceRepository
from app.infrastructure.db.session import SessionLocal, init_db
from app.infrastructure.db.tables import SourceRow
from app.infrastructure.scheduler import start_scheduler

DEFAULT_SOURCES = (
    Source(
        id="seed-sspai",
        name="少数派",
        url="https://sspai.com/feed",
        kind=SourceKind.RSS,
        enabled=True,
        topics="效率,生活,感悟",
    ),
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    async with SessionLocal() as session:
        repo = SqlSourceRepository(session)
        existing = await session.scalar(select(SourceRow).limit(1))
        if existing is None:
            for source in DEFAULT_SOURCES:
                await repo.add(source)
    start_scheduler()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="FitLife Publisher", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(sources_router, prefix="/api/v1")
    app.include_router(articles_router, prefix="/api/v1")
    app.include_router(draft_router, prefix="/api/v1")
    media_dir = Path("data/media")
    media_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")

    @app.exception_handler(AppError)
    async def handle_app_error(_, exc: AppError) -> JSONResponse:
        return JSONResponse({"detail": exc.message}, status_code=exc.status_code)

    @app.get("/api/v1/health", response_model=HealthOut)
    async def health() -> HealthOut:
        return HealthOut(
            status="ok",
            wechat_configured=settings.wechat_configured,
            llm_configured=settings.llm_configured,
            auto_publish=settings.auto_publish,
        )

    return app


app = create_app()
