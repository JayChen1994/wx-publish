"""不落库的编辑发布：抓取预览 → 润色 → 微信草稿。"""

from app.core.config import settings
from app.core.errors import AppError, PublishFailed
from app.domain.formatting import normalize_body, plain_summary
from app.domain.models import (
    Article,
    ArticleStatus,
    ContentPolisher,
    PageCrawler,
    WeChatPublisher,
)
from app.domain.scoring import score_article
from app.infrastructure.sanitize import drop_dangerous_blocks, sanitize_wechat_html


def _prepare_body(raw: str) -> str:
    return sanitize_wechat_html(normalize_body(drop_dangerous_blocks(raw)))


def _draft_to_article(
    *,
    title: str,
    summary: str,
    body_html: str,
    source_url: str,
    author: str,
) -> Article:
    return Article(
        id="draft",
        source_id=None,
        title=title.strip(),
        summary=summary.strip(),
        body_html=body_html.strip(),
        source_url=source_url.strip(),
        author=author.strip(),
        status=ArticleStatus.INGESTED,
        quality_score=score_article(
            title=title, summary=summary, body=body_html
        ),
        topics="",
        metrics="",
    )


class DraftWorkflowService:
    def __init__(
        self,
        crawler: PageCrawler,
        polisher: ContentPolisher,
        publisher: WeChatPublisher,
    ) -> None:
        self._crawler = crawler
        self._polisher = polisher
        self._publisher = publisher

    async def fetch_preview(
        self, title: str, url: str, author: str = ""
    ) -> dict[str, str]:
        item = await self._crawler.fetch_one(url)
        resolved_title = title.strip() or item.title
        resolved_author = author.strip() or item.author
        body_html = _prepare_body(item.body_html)
        summary = plain_summary(body_html)
        return {
            "title": resolved_title,
            "summary": summary,
            "body_html": body_html,
            "source_url": url.strip(),
            "author": resolved_author,
        }

    async def polish(
        self,
        *,
        title: str,
        summary: str,
        body_html: str,
        source_url: str,
        author: str,
        style: str,
    ) -> dict[str, str]:
        if not body_html.strip():
            raise AppError("正文不能为空")
        article = _draft_to_article(
            title=title,
            summary=summary,
            body_html=body_html,
            source_url=source_url,
            author=author,
        )
        polished = await self._polisher.polish(article, style)
        return {
            "title": polished.title.strip(),
            "summary": polished.summary.strip(),
            "body_html": _prepare_body(polished.body_html),
            "source_url": source_url.strip(),
            "author": author.strip(),
        }

    async def publish(
        self,
        *,
        title: str,
        summary: str,
        body_html: str,
        source_url: str,
        author: str,
        auto_publish: bool | None = None,
    ) -> str:
        if not title.strip() or not body_html.strip():
            raise AppError("标题与正文不能为空")
        content_html = _prepare_body(body_html)
        submit = settings.auto_publish if auto_publish is None else auto_publish
        try:
            result = await self._publisher.publish_draft(
                title=title.strip(),
                author="",
                digest=summary.strip() or title.strip(),
                content_html=content_html,
                source_url=source_url.strip(),
                auto_publish=submit,
            )
        except Exception as exc:
            raise PublishFailed(str(exc)) from exc
        if result.publish_id:
            return f"已发表（publish_id={result.publish_id}）"
        return f"已写入微信草稿（media_id={result.draft_media_id}）"
