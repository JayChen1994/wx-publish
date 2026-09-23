from uuid import uuid4

from fastapi import APIRouter, Depends

from app.api.deps import get_ingest_service, get_source_service
from app.api.schemas import MessageOut, SourceCreate, SourceOut
from app.application.editorial import IngestArticlesService, SourceService
from app.domain.models import Source

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut])
async def list_sources(svc: SourceService = Depends(get_source_service)) -> list[Source]:
    return await svc.list()


@router.post("", response_model=SourceOut)
async def create_source(
    payload: SourceCreate, svc: SourceService = Depends(get_source_service)
) -> Source:
    return await svc.create(
        Source(
            id=str(uuid4()),
            name=payload.name,
            url=payload.url,
            kind=payload.kind,
            enabled=payload.enabled,
            topics=payload.topics,
        )
    )


@router.delete("/{source_id}", response_model=MessageOut)
async def delete_source(
    source_id: str, svc: SourceService = Depends(get_source_service)
) -> MessageOut:
    await svc.delete(source_id)
    return MessageOut(message="已删除")


@router.post("/ingest", response_model=MessageOut)
async def ingest_all(svc: IngestArticlesService = Depends(get_ingest_service)) -> MessageOut:
    created, skipped = await svc.ingest()
    return MessageOut(message="抓取完成", created=created, skipped=skipped)


@router.post("/{source_id}/ingest", response_model=MessageOut)
async def ingest_one(
    source_id: str, svc: IngestArticlesService = Depends(get_ingest_service)
) -> MessageOut:
    created, skipped = await svc.ingest(source_id)
    return MessageOut(message="抓取完成", created=created, skipped=skipped)
