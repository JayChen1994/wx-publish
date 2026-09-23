from fastapi import APIRouter, Depends, Query

from app.api.deps import (
    get_editorial_service,
    get_polish_service,
    get_publish_service,
    get_submit_service,
)
from app.api.schemas import (
    ArticleOut,
    ArticleUpdate,
    ManualArticleRequest,
    MessageOut,
    PolishRequest,
    SubmitBatchRequest,
    SubmitUrlRequest,
)
from app.application.editorial import EditorialService, SubmitArticleService
from app.application.polishing import PolishArticleService
from app.application.publishing import PublishArticleService
from app.domain.formatting import normalize_body
from app.domain.models import Article, ArticleStatus
from app.infrastructure.sanitize import drop_dangerous_blocks, sanitize_wechat_html


def _prepare_body(raw: str) -> str:
    return sanitize_wechat_html(normalize_body(drop_dangerous_blocks(raw)))

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", response_model=list[ArticleOut])
async def list_articles(
    status: ArticleStatus | None = Query(default=None),
    svc: EditorialService = Depends(get_editorial_service),
) -> list[Article]:
    return await svc.list(status)


@router.post("/submit", response_model=ArticleOut)
async def submit_article(
    payload: SubmitUrlRequest,
    svc: SubmitArticleService = Depends(get_submit_service),
) -> Article:
    return await svc.submit(str(payload.url), payload.topics)


@router.post("/submit-batch", response_model=MessageOut)
async def submit_articles(
    payload: SubmitBatchRequest,
    svc: SubmitArticleService = Depends(get_submit_service),
) -> MessageOut:
    created, skipped, failures = await svc.submit_many(
        [str(url) for url in payload.urls], payload.topics
    )
    return MessageOut(
        message="批量抓取完成", created=created, skipped=skipped, failures=failures
    )


@router.post("/manual", response_model=ArticleOut)
async def create_manual_article(
    payload: ManualArticleRequest,
    svc: SubmitArticleService = Depends(get_submit_service),
) -> Article:
    return await svc.create_from_link(
        payload.title,
        str(payload.source_url),
        payload.topics,
        payload.author,
    )


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
    fields = payload.model_dump()
    if fields.get("body_html") is not None:
        fields["body_html"] = _prepare_body(fields["body_html"])
    return await svc.update(article_id, **fields)


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
