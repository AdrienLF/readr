"""API tests for /api/articles."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch


async def _seed_article(client, mocker, *, url="https://example.com/a1", title="Test Article",
                         source_type="rss", feed_url="https://example.com/feed.rss"):
    """Helper: create a feed + article via the DB session for test setup."""
    # We bypass the API for seeding to keep tests focused on the article endpoints
    from app.database import SessionLocal
    from app.models import Feed, Article

    async with SessionLocal() as db:
        feed = Feed(url=feed_url, title="Test Feed", source_type=source_type)
        db.add(feed)
        await db.flush()
        article = Article(
            feed_id=feed.id,
            title=title,
            url=url,
            excerpt="Test excerpt",
            full_content="<p>Full content here.</p>",
            published_at=datetime(2024, 1, 15, 10, 0, 0),
        )
        db.add(article)
        await db.commit()
        return {"feed_id": feed.id, "article_id": article.id}


async def test_list_articles_empty(client):
    res = await client.get("/api/articles")
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_list_articles_pagination_defaults(client, mocker):
    ids = await _seed_article(client, mocker)
    res = await client.get("/api/articles")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["page"] == 1
    assert data["page_size"] == 30


async def test_list_articles_filter_by_feed(client, mocker):
    ids = await _seed_article(client, mocker, url="https://ex.com/a1", feed_url="https://feed1.com/rss")
    await _seed_article(client, mocker, url="https://ex.com/a2", feed_url="https://feed2.com/rss")

    res = await client.get(f"/api/articles?feed_id={ids['feed_id']}")
    assert res.status_code == 200
    assert res.json()["total"] == 1


async def test_list_articles_filter_unread(client, mocker):
    ids = await _seed_article(client, mocker)

    # Mark as read
    await client.patch(f"/api/articles/{ids['article_id']}/read?is_read=true")

    res_unread = await client.get("/api/articles?is_read=false")
    assert res_unread.json()["total"] == 0

    res_read = await client.get("/api/articles?is_read=true")
    assert res_read.json()["total"] == 1


async def test_list_articles_filter_bookmarked(client, mocker):
    ids = await _seed_article(client, mocker)
    await client.patch(f"/api/articles/{ids['article_id']}/bookmark")

    res = await client.get("/api/articles?is_bookmarked=true")
    assert res.json()["total"] == 1

    res2 = await client.get("/api/articles?is_bookmarked=false")
    assert res2.json()["total"] == 0


async def test_get_article_by_id(client, mocker):
    ids = await _seed_article(client, mocker)
    res = await client.get(f"/api/articles/{ids['article_id']}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == ids["article_id"]
    assert data["title"] == "Test Article"
    assert data["full_content"] == "<p>Full content here.</p>"
    assert data["feed_title"] == "Test Feed"


async def test_get_article_not_found(client):
    res = await client.get("/api/articles/9999")
    assert res.status_code == 404


async def test_mark_article_read(client, mocker):
    ids = await _seed_article(client, mocker)

    res = await client.patch(f"/api/articles/{ids['article_id']}/read?is_read=true")
    assert res.status_code == 200
    assert res.json()["is_read"] is True

    # Verify persisted
    article = await client.get(f"/api/articles/{ids['article_id']}")
    assert article.json()["is_read"] is True


async def test_mark_article_unread(client, mocker):
    ids = await _seed_article(client, mocker)

    await client.patch(f"/api/articles/{ids['article_id']}/read?is_read=true")
    res = await client.patch(f"/api/articles/{ids['article_id']}/read?is_read=false")
    assert res.json()["is_read"] is False


async def test_toggle_bookmark(client, mocker):
    ids = await _seed_article(client, mocker)

    res = await client.patch(f"/api/articles/{ids['article_id']}/bookmark")
    assert res.status_code == 200
    assert res.json()["is_bookmarked"] is True

    # Toggle again
    res2 = await client.patch(f"/api/articles/{ids['article_id']}/bookmark")
    assert res2.json()["is_bookmarked"] is False


async def test_get_comments_non_reddit(client, mocker):
    """Comments endpoint should 400 for non-Reddit articles."""
    ids = await _seed_article(client, mocker, source_type="rss")
    res = await client.get(f"/api/articles/{ids['article_id']}/comments")
    assert res.status_code == 400


async def test_get_comments_reddit(client, mocker):
    """Comments endpoint fetches from Reddit for Reddit articles."""
    ids = await _seed_article(
        client, mocker,
        url="https://www.reddit.com/r/python/comments/abc123/test_post/",
        source_type="reddit",
        feed_url="https://www.reddit.com/r/python.rss",
    )

    mock_comments = [
        {
            "id": "c1",
            "author": "user1",
            "body": "Great post!",
            "score": 42,
            "created_utc": 1700000000.0,
            "depth": 0,
            "replies": [],
        }
    ]

    with patch(
        "app.routers.articles.fetch_reddit_comments",
        new_callable=AsyncMock,
        return_value=mock_comments,
    ):
        res = await client.get(f"/api/articles/{ids['article_id']}/comments")

    assert res.status_code == 200
    data = res.json()
    assert len(data["comments"]) == 1
    assert data["comments"][0]["id"] == "c1"


async def test_search_articles(client, mocker):
    """FTS5 search returns matching articles."""
    await _seed_article(client, mocker, url="https://ex.com/a1", title="Python async programming")
    await _seed_article(client, mocker, url="https://ex.com/a2", title="JavaScript promises",
                        feed_url="https://ex.com/feed2.rss")

    res = await client.get("/api/articles/search?q=Python")
    assert res.status_code == 200
    data = res.json()
    # At least the Python article should be found
    titles = [item["title"] for item in data["items"]]
    assert any("Python" in t for t in titles)


async def test_search_articles_short_query(client):
    res = await client.get("/api/articles/search?q=a")
    assert res.status_code == 422  # min_length=2


async def test_list_articles_has_more_flag(client, mocker):
    """has_more is True when there are more pages."""
    for i in range(5):
        await _seed_article(
            client, mocker,
            url=f"https://ex.com/a{i}",
            feed_url=f"https://ex.com/feed{i}.rss",
        )

    res = await client.get("/api/articles?page=1&page_size=3")
    assert res.status_code == 200
    data = res.json()
    assert data["has_more"] is True
    assert len(data["items"]) == 3
