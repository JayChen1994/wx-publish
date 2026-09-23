from pydantic import BaseModel, Field

from app.domain.models import ArticleStatus, SourceKind


class SourceCreate(BaseModel):
    name: str
    url: str
    kind: SourceKind = SourceKind.RSS
    enabled: bool = True
    topics: str = "健身减脂,人生感悟"


class SourceOut(BaseModel):
    id: str
    name: str
    url: str
    kind: SourceKind
    enabled: bool
    topics: str


class ArticleUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    body_html: str | None = None
    author: str | None = None
    topics: str | None = None


class PolishRequest(BaseModel):
    style: str = Field(
        default="专业、真诚、克制，适合健身减脂与个人成长类公众号",
        min_length=2,
        max_length=200,
    )


class ArticleOut(BaseModel):
    id: str
    source_id: str | None
    title: str
    summary: str
    body_html: str
    source_url: str
    author: str
    status: ArticleStatus
    quality_score: int
    topics: str


class ArticleListOut(BaseModel):
    items: list[ArticleOut]
    total: int = Field(description="本页条数")


class HealthOut(BaseModel):
    status: str
    wechat_configured: bool
    llm_configured: bool
    auto_publish: bool


class MessageOut(BaseModel):
    message: str
    created: int | None = None
    skipped: int | None = None
