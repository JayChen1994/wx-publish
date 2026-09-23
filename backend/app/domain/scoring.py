from app.domain.models import Article


TOPIC_KEYWORDS = {
    "健身": 12,
    "减脂": 16,
    "增肌": 8,
    "训练": 8,
    "饮食": 8,
    "卡路里": 6,
    "感悟": 10,
    "成长": 6,
    "习惯": 6,
}


def score_article(article: Article | None = None, *, title: str = "", summary: str = "", body: str = "") -> int:
    text = " ".join(
        part
        for part in (
            getattr(article, "title", "") if article else title,
            getattr(article, "summary", "") if article else summary,
            getattr(article, "body_html", "") if article else body,
        )
        if part
    )
    score = 20
    for word, weight in TOPIC_KEYWORDS.items():
        if word in text:
            score += weight
    length = len(text)
    if length > 400:
        score += 10
    if length > 1200:
        score += 10
    return min(score, 100)
