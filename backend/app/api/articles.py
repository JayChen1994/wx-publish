from fastapi import APIRouter, Depends, Query

from app.api.deps import get_editorial_service, get_polish_service, get_publish_service
from app.api.schemas import ArticleOut, ArticleUpdate, MessageOut, PolishRequest
from app.application.editorial import EditorialService
from app.application.polishing import PolishArticleService
from app.application.publishing import PublishArticleService
from app.domain.models import Article, ArticleStatus

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", response_model=list[ArticleOut])
async def list_articles(
    status: ArticleStatus | None = Query(default=None),
    svc: EditorialService = Depends(get_editorial_service),
) -> list[Article]:
    return await svc.list(status)


@router.get("/{article_id}", response_model=ArticleOut)
async def get_article(
    article_id: str, svc: EditorialService = Depends(get_editorial_service)
) -> Article:
    return await svc.get(article_id)


@router.patch("/{article_id}", response_model=ArticleOut)
async def update_article(
    article_id: str,
    payload: ArticleUpdate,
    svc: EditorialService = Depends(get_editorial_service),
) -> Article:
    return await svc.update(article_id, **payload.model_dump())


@router.post("/{article_id}/approve", response_model=ArticleOut)
async def approve_article(
    article_id: str, svc: EditorialService = Depends(get_editorial_service)
) -> Article:
    return await svc.approve(article_id)


@router.post("/{article_id}/reject", response_model=ArticleOut)
async def reject_article(
    article_id: str, svc: EditorialService = Depends(get_editorial_service)
) -> Article:
    return await svc.reject(article_id)


@router.post("/{article_id}/polish", response_model=ArticleOut)
async def polish_article(
    article_id: str,
    payload: PolishRequest,
    svc: PolishArticleService = Depends(get_polish_service),
) -> Article:
    return await svc.polish(article_id, payload.style)


@router.post("/{article_id}/publish", response_model=MessageOut)
async def publish_article(
    article_id: str, svc: PublishArticleService = Depends(get_publish_service)
) -> MessageOut:
    await svc.publish(article_id)
    return MessageOut(message="已提交微信（草稿或发表，取决于 AUTO_PUBLISH）")
