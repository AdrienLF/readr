import trafilatura
import httpx
import logging

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RSSReader/1.0; +https://github.com/local/rss-reader)"
}


async def fetch_full_content(url: str) -> tuple[str | None, str | None, str | None]:
    """
    Returns (full_content_html, excerpt, image_url).
    Falls back gracefully on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=HEADERS) as client:
            response = await client.get(url)
            if response.status_code != 200:
                return None, None, None
            html = response.text
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None, None, None

    return extract_from_html(html, url)


def extract_from_html(html: str, url: str) -> tuple[str | None, str | None, str | None]:
    try:
        content_html = trafilatura.extract(
            html,
            url=url,
            output_format="html",
            include_images=True,
            include_links=True,
            include_tables=True,
            favor_recall=True,
        )
        content_text = trafilatura.extract(
            html,
            url=url,
            output_format="txt",
            favor_recall=True,
        )
        metadata = trafilatura.extract_metadata(html, default_url=url)

        excerpt = None
        if content_text:
            excerpt = content_text[:400].rsplit(" ", 1)[0] + "…" if len(content_text) > 400 else content_text

        image_url = metadata.image if metadata and metadata.image else None

        # Fallback: extract first image from article content
        if not image_url and content_html:
            import re
            img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content_html)
            if img_match:
                image_url = img_match.group(1)

        return content_html, excerpt, image_url
    except Exception as e:
        logger.warning(f"Extraction failed for {url}: {e}")
        return None, None, None
