"""Unit tests for llm.py — digest generation and article summarization."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from sqlalchemy import text


def _mock_ollama_response(content: str):
    resp = MagicMock()
    resp.message.content = content
    return resp


# ── generate_digest_for_topic ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_digest_returns_content(db):
    from app.models import Feed, Article
    from app.services.llm import generate_digest_for_topic

    feed = Feed(url="https://example.com/feed.rss", title="Test Feed", source_type="rss")
    db.add(feed)
    await db.flush()

    for i in range(3):
        db.add(Article(
            feed_id=feed.id,
            title=f"Article {i}",
            url=f"https://example.com/article-{i}",
            excerpt=f"Excerpt {i}",
            fetched_at=datetime.now(timezone.utc),
        ))
    await db.commit()

    with patch("app.services.llm.AsyncClient") as MockClient:
        MockClient.return_value.chat = AsyncMock(
            return_value=_mock_ollama_response("1. Overview\n2. Top stories\n3. Trends")
        )
        result = await generate_digest_for_topic(None, "All Topics", "2024-01-15", db)

    assert result is not None
    assert "Overview" in result or "stories" in result


@pytest.mark.asyncio
async def test_generate_digest_returns_none_when_no_articles(db):
    from app.services.llm import generate_digest_for_topic

    result = await generate_digest_for_topic(None, "Empty Topic", "2024-01-15", db)
    assert result is None


@pytest.mark.asyncio
async def test_generate_digest_propagates_ollama_error(db):
    """Errors from Ollama now propagate instead of being swallowed."""
    from app.models import Feed, Article
    from app.services.llm import generate_digest_for_topic

    feed = Feed(url="https://ex.com/f.rss", title="F", source_type="rss")
    db.add(feed)
    await db.flush()
    db.add(Article(
        feed_id=feed.id, title="An article", url="https://ex.com/a",
        excerpt="Excerpt", fetched_at=datetime.now(timezone.utc),
    ))
    await db.commit()

    with patch("app.services.llm.AsyncClient") as MockClient:
        MockClient.return_value.chat = AsyncMock(side_effect=Exception("Connection refused"))
        with pytest.raises(Exception, match="Connection refused"):
            await generate_digest_for_topic(None, "All", "2024-01-15", db)


@pytest.mark.asyncio
async def test_generate_digest_topic_filter(db):
    """Only articles from the given topic's feeds are included."""
    from app.models import Feed, Article, Topic
    from app.services.llm import generate_digest_for_topic

    topic = Topic(name="Tech", color="#6366f1")
    db.add(topic)
    feed_in = Feed(url="https://tech.com/rss", title="Tech Feed", source_type="rss")
    feed_out = Feed(url="https://other.com/rss", title="Other Feed", source_type="rss")
    db.add_all([feed_in, feed_out])
    await db.flush()

    # Direct insert to avoid lazy-load MissingGreenlet in async context
    await db.execute(
        text("INSERT INTO feed_topics (feed_id, topic_id) VALUES (:fid, :tid)"),
        {"fid": feed_in.id, "tid": topic.id},
    )
    db.add(Article(
        feed_id=feed_in.id, title="Tech article", url="https://tech.com/a1",
        excerpt="Tech stuff", fetched_at=datetime.now(timezone.utc),
    ))
    db.add(Article(
        feed_id=feed_out.id, title="Other article", url="https://other.com/a1",
        excerpt="Other stuff", fetched_at=datetime.now(timezone.utc),
    ))
    await db.commit()

    captured_prompt = {}

    async def fake_chat(model, messages):
        captured_prompt["text"] = messages[0]["content"]
        return _mock_ollama_response("Digest content")

    with patch("app.services.llm.AsyncClient") as MockClient:
        MockClient.return_value.chat = fake_chat
        result = await generate_digest_for_topic(topic.id, "Tech", "2024-01-15", db)

    assert result == "Digest content"
    assert "Tech article" in captured_prompt["text"]
    assert "Other article" not in captured_prompt["text"]


# ── summarize_article ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_summarize_article_with_full_content(db):
    from app.models import Feed, Article
    from app.services.llm import summarize_article

    feed = Feed(url="https://ex.com/rss", title="F", source_type="rss")
    db.add(feed)
    await db.flush()
    article = Article(
        feed_id=feed.id, title="AI and the Future",
        url="https://ex.com/ai", full_content="<p>Long article about AI.</p>",
        fetched_at=datetime.now(timezone.utc),
    )
    db.add(article)
    await db.commit()

    with patch("app.services.llm.AsyncClient") as MockClient:
        MockClient.return_value.chat = AsyncMock(
            return_value=_mock_ollama_response("AI is transforming industries.")
        )
        result = await summarize_article(article)

    assert result == "AI is transforming industries."


@pytest.mark.asyncio
async def test_summarize_article_falls_back_to_excerpt(db):
    from app.models import Feed, Article
    from app.services.llm import summarize_article

    feed = Feed(url="https://ex.com/rss2", title="F2", source_type="rss")
    db.add(feed)
    await db.flush()
    article = Article(
        feed_id=feed.id, title="Short post",
        url="https://ex.com/short", full_content=None,
        excerpt="A brief excerpt.", fetched_at=datetime.now(timezone.utc),
    )
    db.add(article)
    await db.commit()

    with patch("app.services.llm.AsyncClient") as MockClient:
        MockClient.return_value.chat = AsyncMock(
            return_value=_mock_ollama_response("Summary of short post.")
        )
        result = await summarize_article(article)

    assert result == "Summary of short post."


@pytest.mark.asyncio
async def test_summarize_article_returns_none_when_no_content(db):
    from app.models import Feed, Article
    from app.services.llm import summarize_article

    feed = Feed(url="https://ex.com/rss3", title="F3", source_type="rss")
    db.add(feed)
    await db.flush()
    article = Article(
        feed_id=feed.id, title="Empty article",
        url="https://ex.com/empty", full_content=None,
        excerpt=None, fetched_at=datetime.now(timezone.utc),
    )
    db.add(article)
    await db.commit()

    result = await summarize_article(article)
    assert result is None
