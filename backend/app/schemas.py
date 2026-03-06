from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


# --- Topic ---

class TopicBase(BaseModel):
    name: str
    color: str = "#6366f1"
    icon: Optional[str] = None


class TopicCreate(TopicBase):
    pass


class TopicUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class TopicBrief(BaseModel):
    id: int
    name: str
    color: str
    model_config = ConfigDict(from_attributes=True)


class TopicResponse(TopicBase):
    id: int
    created_at: datetime
    feed_count: int = 0
    model_config = ConfigDict(from_attributes=True)


# --- Feed ---

class FeedCreate(BaseModel):
    url: str
    topic_ids: list[int] = []


class FeedUpdate(BaseModel):
    title: Optional[str] = None
    poll_interval: Optional[int] = None
    topic_ids: Optional[list[int]] = None


class FeedResponse(BaseModel):
    id: int
    url: str
    title: Optional[str]
    description: Optional[str]
    source_type: str
    favicon_url: Optional[str]
    last_fetched: Optional[datetime]
    last_error: Optional[str]
    error_count: int = 0
    is_muted: bool = False
    health: str = "ok"  # ok | stale | error | never
    poll_interval: int
    created_at: datetime
    unread_count: int = 0
    topics: list[TopicBrief] = []
    model_config = ConfigDict(from_attributes=True)


# --- Tag ---

class TagCreate(BaseModel):
    name: str
    color: str = "#6366f1"


class TagResponse(BaseModel):
    id: int
    name: str
    color: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TagBrief(BaseModel):
    id: int
    name: str
    color: str
    model_config = ConfigDict(from_attributes=True)


# --- Rule ---

class RuleCreate(BaseModel):
    name: str
    condition: dict  # {field, op, value}
    action: str
    is_active: bool = True


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    condition: Optional[dict] = None
    action: Optional[str] = None
    is_active: Optional[bool] = None


class RuleResponse(BaseModel):
    id: int
    name: str
    condition: dict
    action: str
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Highlight ---

class HighlightCreate(BaseModel):
    text: str
    note: Optional[str] = None
    color: str = "yellow"


class HighlightResponse(BaseModel):
    id: int
    article_id: int
    text: str
    note: Optional[str]
    color: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Entity ---

class EntityResponse(BaseModel):
    id: int
    name: str
    entity_type: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TrendingEntity(BaseModel):
    name: str
    entity_type: str
    count: int


# --- Article ---

class ArticleResponse(BaseModel):
    id: int
    feed_id: int
    feed_title: Optional[str]
    feed_source_type: str
    title: str
    url: str
    excerpt: Optional[str]
    full_content: Optional[str]
    image_url: Optional[str]
    audio_url: Optional[str]
    author: Optional[str]
    published_at: Optional[datetime]
    fetched_at: datetime
    is_read: bool
    is_bookmarked: bool
    is_saved: bool = False
    note: Optional[str] = None
    summary: Optional[str] = None
    priority_score: float = 0.5
    score: Optional[int] = None
    comment_count: Optional[int] = None
    user_signal: Optional[int] = None
    tags: list[TagBrief] = []
    highlights: list[HighlightResponse] = []
    entities: list[EntityResponse] = []
    model_config = ConfigDict(from_attributes=True)


class ArticleListItem(BaseModel):
    id: int
    feed_id: int
    feed_title: Optional[str]
    feed_source_type: str
    title: str
    url: str
    excerpt: Optional[str]
    image_url: Optional[str]
    audio_url: Optional[str]
    author: Optional[str]
    published_at: Optional[datetime]
    is_read: bool
    is_bookmarked: bool
    is_saved: bool = False
    priority_score: float = 0.5
    score: Optional[int] = None
    comment_count: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


# --- Reddit Comment ---

class RedditComment(BaseModel):
    id: str
    author: str
    body: str
    score: int
    created_utc: float
    depth: int
    replies: list["RedditComment"] = []


RedditComment.model_rebuild()


# --- Digest ---

class DigestResponse(BaseModel):
    id: int
    date: str
    topic_id: Optional[int]
    topic_name: Optional[str]
    content: Optional[str]
    model_used: Optional[str]
    generated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DigestGenerateRequest(BaseModel):
    topic_id: Optional[int] = None
    date: Optional[str] = None  # YYYY-MM-DD, defaults to today
    force: bool = False


# --- Settings ---

class SettingsUpdate(BaseModel):
    digest_time: Optional[str] = None   # HH:MM
    ollama_model: Optional[str] = None
    fetch_interval: Optional[int] = None


class SettingsResponse(BaseModel):
    digest_time: str
    ollama_model: str
    fetch_interval: int


# --- Mute Filters ---

class MuteFilterCreate(BaseModel):
    pattern: str
    is_regex: bool = False
    feed_id: Optional[int] = None


class MuteFilterResponse(BaseModel):
    id: int
    pattern: str
    is_regex: bool
    feed_id: Optional[int]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Feed Discovery ---

class DiscoveredFeed(BaseModel):
    url: str
    title: str


# --- Pagination ---

class PaginatedArticles(BaseModel):
    items: list[ArticleListItem]
    total: int
    page: int
    page_size: int
    has_more: bool
