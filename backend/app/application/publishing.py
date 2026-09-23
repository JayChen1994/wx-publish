from app.core.config import settings
from app.core.errors import ConflictError, NotFoundError, PublishFailed
from app.domain.models import ArticleRepository, ArticleStatus, PublicationRepository, WeChatPublisher


class PublishArticleService:
    def __init__(
        self,
        articles: ArticleRepository,
        publications: PublicationRepository,
        publisher: WeChatPublisher,
    ) -> None:
        self._articles = articles
        self._publications = publications
        self._publisher = publisher

    async def publish(self, article_id: str, auto_publish: bool | None = None) -> None:
        article = await self._articles.get(article_id)
        if not article:
            raise NotFoundError("文章不存在")
        if await self._publications.has_success(article_id):
            raise ConflictError("该文章已发布，禁止重复提交")
        if article.status != ArticleStatus.APPROVED:
            raise ConflictError("仅已审核文章可发布")
        submit = settings.auto_publish if auto_publish is None else auto_publish
        try:
            result = await self._publisher.publish_draft(
                title=article.title,
                author="",
                digest=article.summary or article.title,
                content_html=article.body_html,
                source_url=article.source_url,
                auto_publish=submit,
            )
        except Exception as exc:
            await self._publications.add(article_id, "", None, "failed", str(exc))
            raise PublishFailed(str(exc)) from exc
        article.mark_published()
        await self._publications.add(
            article_id, result.draft_media_id, result.publish_id, "success", None
        )
        await self._articles.save(article)
