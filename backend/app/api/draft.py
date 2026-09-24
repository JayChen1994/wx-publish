from fastapi import APIRouter, Depends

from app.api.deps import get_draft_workflow_service
from app.api.schemas import (
    DraftFetchRequest,
    DraftOut,
    DraftPolishRequest,
    DraftPublishRequest,
    MessageOut,
)
from app.application.draft_workflow import DraftWorkflowService

router = APIRouter(prefix="/draft", tags=["draft"])


@router.post("/fetch", response_model=DraftOut)
async def fetch_draft(
    payload: DraftFetchRequest,
    svc: DraftWorkflowService = Depends(get_draft_workflow_service),
) -> DraftOut:
    data = await svc.fetch_preview(
        payload.title,
        str(payload.source_url),
        payload.author,
        payload.body_html,
    )
    return DraftOut(**data)


@router.post("/polish", response_model=DraftOut)
async def polish_draft(
    payload: DraftPolishRequest,
    svc: DraftWorkflowService = Depends(get_draft_workflow_service),
) -> DraftOut:
    data = await svc.polish(
        title=payload.title,
        summary=payload.summary,
        body_html=payload.body_html,
        source_url=str(payload.source_url),
        author=payload.author,
        style=payload.style,
    )
    return DraftOut(**data)


@router.post("/publish", response_model=MessageOut)
async def publish_draft(
    payload: DraftPublishRequest,
    svc: DraftWorkflowService = Depends(get_draft_workflow_service),
) -> MessageOut:
    message = await svc.publish(
        title=payload.title,
        summary=payload.summary,
        body_html=payload.body_html,
        source_url=str(payload.source_url),
        author=payload.author,
    )
    return MessageOut(message=message)
