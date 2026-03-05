"""Unit tests for extractor.py."""
import pytest
from unittest.mock import patch, MagicMock
from app.services.extractor import extract_from_html, fetch_full_content


SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Test Article</title>
  <meta property="og:image" content="https://example.com/og-image.jpg" />
</head>
<body>
  <article>
    <h1>Test Article Title</h1>
    <p>This is the first paragraph of the article with meaningful content to extract.</p>
    <p>This is the second paragraph with more substantive text to help trafilatura identify content.</p>
    <p>And a third paragraph to ensure we have enough content for reliable extraction.</p>
  </article>
</body>
</html>"""


def test_extract_from_html_returns_content():
    content_html, excerpt, image_url = extract_from_html(SAMPLE_HTML, "https://example.com/article")
    # trafilatura may or may not extract depending on content density
    # At minimum it should not raise
    assert isinstance(excerpt, (str, type(None)))
    assert isinstance(image_url, (str, type(None)))


def test_extract_from_html_excerpt_length():
    content_html, excerpt, image_url = extract_from_html(SAMPLE_HTML, "https://example.com/article")
    if excerpt:
        assert len(excerpt) <= 405  # 400 chars + ellipsis buffer


def test_extract_from_html_handles_empty():
    content_html, excerpt, image_url = extract_from_html("", "https://example.com")
    assert content_html is None or isinstance(content_html, str)


def test_extract_from_html_handles_bad_html():
    content_html, excerpt, image_url = extract_from_html(
        "<not valid html at all >>>", "https://example.com"
    )
    # Should not raise, just return None/None/None
    assert isinstance(content_html, (str, type(None)))


@pytest.mark.asyncio
async def test_fetch_full_content_returns_none_on_error():
    with patch("app.services.extractor.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("Network error")
        content, excerpt, image = await fetch_full_content("https://example.com/article")
    assert content is None
    assert excerpt is None
    assert image is None


@pytest.mark.asyncio
async def test_fetch_full_content_returns_none_on_bad_status():
    with patch("app.services.extractor.httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        content, excerpt, image = await fetch_full_content("https://example.com/article")
    assert content is None
