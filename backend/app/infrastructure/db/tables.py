from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SourceRow(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(String(500), unique=True)
    kind: Mapped[str] = mapped_column(String(32), default="rss")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    topics: Mapped[str] = mapped_column(String(200), default="健身减脂,人生感悟")
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    articles: Mapped[list["ArticleRow"]] = relationship(back_populates="source")


class ArticleRow(Base):
    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="")
    body_html: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(String(800), unique=True)
    author: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(32), default="ingested")
    quality_score: Mapped[int] = mapped_column(Integer, default=0)
    topics: Mapped[str] = mapped_column(String(200), default="")
    metrics: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    source: Mapped[SourceRow | None] = relationship(back_populates="articles")


class PublicationRow(Base):
    __tablename__ = "publications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id"))
    draft_media_id: Mapped[str] = mapped_column(String(128), default="")
    publish_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
