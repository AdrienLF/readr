from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, Table, Column, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


feed_topics = Table(
    "feed_topics",
    Base.metadata,
    Column("feed_id", Integer, ForeignKey("feeds.id", ondelete="CASCADE"), primary_key=True),
    Column("topic_id", Integer, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
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

    feed: Mapped["Feed"] = relationship(back_populates="articles")


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


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text)
