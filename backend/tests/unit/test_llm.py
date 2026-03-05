"""Unit tests for llm.py — digest generation with mocked Ollama."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


@pytest.mark.asyncio
async def test_generate_digest_returns_content(db):
    """generate_digest_for_topic returns a string when Ollama responds."""
    from app.models import Feed, Article, Topic
    from app.services.llm import generate_digest_for_topic

    # Seed a feed and some articles
    feed = Feed(url="https://example.com/feed.rss", title="Test Feed", source_type="rss")
    db.add(feed)
    await db.flush()

    for i in range(3):
        article = Article(
            feed_id=feed.id,
            title=f"Article {i}",
            url=f"https://example.com/article-{i}",
            excerpt=f"Excerpt for article {i}",
            fetched_at=datetime.utcnow(),
        )
        db.add(article)
    await db.commit()

    mock_response = MagicMock()
    mock_response.message.content = "1. Overview\n2. Top stories\n3. Trends"

    with patch("app.services.llm.AsyncClient") as mock_ollama:
        mock_ollama.return_value.chat = AsyncMock(return_value=mock_response)
        result = await generate_digest_for_topic(
            topic_id=None,
            topic_name="All Topics",
            target_date="2024-01-15",
            db=db,
        )

    assert result is not None
    assert "Overview" in result or "stories" in result


@pytest.mark.asyncio
async def test_generate_digest_returns_none_when_no_articles(db):
    """generate_digest_for_topic returns None when there are no recent articles."""
    from app.services.llm import generate_digest_for_topic

    result = await generate_digest_for_topic(
        topic_id=None,
        topic_name="Empty Topic",
        target_date="2024-01-15",
        db=db,
    )
    assert result is None


@pytest.mark.asyncio
async def test_generate_digest_handles_ollama_error(db):
    """generate_digest_for_topic returns None on Ollama failure."""
    from app.models import Feed, Article
    from app.services.llm import generate_digest_for_topic

    feed = Feed(url="https://example.com/f2.rss", title="Feed 2", source_type="rss")
    db.add(feed)
    await db.flush()

    article = Article(
        feed_id=feed.id,
        title="Some article",
        url="https://example.com/a1",
        excerpt="Excerpt",
        fetched_at=datetime.utcnow(),
    )
    db.add(article)
    await db.commit()

    with patch("app.services.llm.AsyncClient") as mock_ollama:
        mock_ollama.return_value.chat = AsyncMock(side_effect=Exception("Connection refused"))
        result = await generate_digest_for_topic(
            topic_id=None,
            topic_name="All",
            target_date="2024-01-15",
            db=db,
        )

    assert result is None
