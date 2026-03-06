from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, Boolean, DateTime, Float, ForeignKey, Table, Column, func, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


feed_topics = Table(
    "feed_topics",
    Base.metadata,
    Column("feed_id", Integer, ForeignKey("feeds.id", ondelete="CASCADE"), primary_key=True),
    Column("topic_id", Integer, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
)

article_tags = Table(
    "article_tags",
    Base.metadata,
    Column("article_id", Integer, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Feed(Base):
    __tablename__ = "feeds"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True)
    title: Mapped[Optional[str]] = mapped_column(String(512))
    description: Mapped[Optional[str]] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(32), default="rss")  # rss | reddit | rsshub
    favicon_url: Mapped[Optional[str]] = mapped_column(String(2048))
    last_fetched: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False)
    poll_interval: Mapped[int] = mapped_column(Integer, default=3600)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    articles: Mapped[list["Article"]] = relationship(
        back_populates="feed", cascade="all, delete-orphan"
    )
    topics: Mapped[list["Topic"]] = relationship(
        secondary="feed_topics", back_populates="feeds"
    )


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    feed_id: Mapped[int] = mapped_column(ForeignKey("feeds.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(1024))
    url: Mapped[str] = mapped_column(String(2048), unique=True)
    excerpt: Mapped[Optional[str]] = mapped_column(Text)
    full_content: Mapped[Optional[str]] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(String(2048))
    author: Mapped[Optional[str]] = mapped_column(String(256))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_bookmarked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    audio_url: Mapped[Optional[str]] = mapped_column(String(2048))
    note: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    priority_score: Mapped[float] = mapped_column(Float, default=0.5, index=True)

    feed: Mapped["Feed"] = relationship(back_populates="articles")
    tags: Mapped[list["Tag"]] = relationship(secondary="article_tags", back_populates="articles")
    highlights: Mapped[list["Highlight"]] = relationship(back_populates="article", cascade="all, delete-orphan")
    entities: Mapped[list["Entity"]] = relationship(back_populates="article", cascade="all, delete-orphan")


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    color: Mapped[str] = mapped_column(String(32), default="#6366f1")
    icon: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    feeds: Mapped[list["Feed"]] = relationship(
        secondary="feed_topics", back_populates="topics"
    )
    digests: Mapped[list["Digest"]] = relationship(back_populates="topic")


class Digest(Base):
    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD
    topic_id: Mapped[Optional[int]] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))
    content: Mapped[Optional[str]] = mapped_column(Text)
    model_used: Mapped[Optional[str]] = mapped_column(String(128))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    topic: Mapped[Optional["Topic"]] = relationship(back_populates="digests")


class MuteFilter(Base):
    __tablename__ = "mute_filters"

    id: Mapped[int] = mapped_column(primary_key=True)
    pattern: Mapped[str] = mapped_column(String(512))
    is_regex: Mapped[bool] = mapped_column(Boolean, default=False)
    # NULL = global; set to a feed_id to scope to one feed
    feed_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("feeds.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    color: Mapped[str] = mapped_column(String(32), default="#6366f1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    articles: Mapped[list["Article"]] = relationship(secondary="article_tags", back_populates="tags")


class Rule(Base):
    """Automation rule: if condition matches an incoming article, apply action."""
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    # condition: {"field": "title"|"author"|"feed_id", "op": "contains"|"not_contains"|"matches"|"equals", "value": "..."}
    condition: Mapped[dict] = mapped_column(JSON)
    # action: "mark_read" | "save" | "bookmark" | "mute" | "tag:<tag_id>"
    action: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text)


class Highlight(Base):
    __tablename__ = "highlights"

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    note: Mapped[Optional[str]] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(32), default="yellow")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    article: Mapped["Article"] = relationship(back_populates="highlights")


class ArticleSignal(Base):
    """Thumbs up / down signal per article (one signal per article)."""
    __tablename__ = "article_signals"
    __table_args__ = (UniqueConstraint("article_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), index=True)
    feed_id: Mapped[int] = mapped_column(ForeignKey("feeds.id", ondelete="CASCADE"), index=True)
    signal: Mapped[int] = mapped_column(Integer)  # 1 = like, -1 = dislike
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Entity(Base):
    """Named entity extracted from an article via LLM."""
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(256), index=True)
    entity_type: Mapped[str] = mapped_column(String(32))  # PERSON, ORG, PLACE, TOPIC, PRODUCT, EVENT
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    article: Mapped["Article"] = relationship(back_populates="entities")


class SavedSearch(Base):
    """A named smart search whose query is expanded into terms by Ollama."""
    __tablename__ = "saved_searches"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    query: Mapped[str] = mapped_column(Text)
    # Ollama-expanded list of search terms, stored as JSON array
    expanded_terms: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    terms_refreshed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    matches: Mapped[list["ArticleSearchMatch"]] = relationship(
        back_populates="search", cascade="all, delete-orphan"
    )


class ArticleSearchMatch(Base):
    """Pre-computed match between an article and a saved search."""
    __tablename__ = "article_search_matches"

    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True
    )
    search_id: Mapped[int] = mapped_column(
        ForeignKey("saved_searches.id", ondelete="CASCADE"), primary_key=True
    )
    score: Mapped[float] = mapped_column(Float)  # 0–1, fraction of terms matched
    matched_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    article: Mapped["Article"] = relationship()
    search: Mapped["SavedSearch"] = relationship(back_populates="matches")
