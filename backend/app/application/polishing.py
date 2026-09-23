from app.core.errors import ConflictError, NotFoundError
from app.domain.models import Article, ArticleRepository, ArticleStatus, ContentPolisher
from app.domain.scoring import score_article


class PolishArticleService:
    def __init__(
        self, articles: ArticleRepository, content_polisher: ContentPolisher
    ) -> None:
        self._articles = articles
        self._content_polisher = content_polisher

    async def polish(self, article_id: str, style: str) -> Article:
        article = await self._articles.get(article_id)
        if not article:
            raise NotFoundError("文章不存在")
        if article.status == ArticleStatus.PUBLISHED:
            raise ConflictError("已发布文章不可再次润色")

        polished = await self._content_polisher.polish(article, style)
        article.title = polished.title.strip()
        article.summary = polished.summary.strip()
        article.body_html = polished.body_html.strip()
        article.status = ArticleStatus.INGESTED
        article.quality_score = score_article(article)
        await self._articles.save(article)
        return article
