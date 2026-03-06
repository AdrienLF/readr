import logging
from datetime import date, datetime, timedelta, timezone
from ollama import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..database import SessionLocal
from ..models import Feed, Article, Topic, Digest, Setting
from ..config import settings as app_settings

logger = logging.getLogger(__name__)


async def _get_ollama_model() -> str:
    async with SessionLocal() as db:
        row = await db.get(Setting, "ollama_model")
        return row.value if row and row.value else app_settings.ollama_model


async def generate_digest_for_topic(
    topic_id: int | None,
    topic_name: str,
    target_date: str,
    db,
) -> str | None:
    # Fetch articles from the last 24h for this topic
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    if topic_id is None:
        # Global digest — all articles
        stmt = (
            select(Article)
            .where(Article.fetched_at >= since)
            .order_by(Article.published_at.desc())
            .limit(60)
        )
    else:
        stmt = (
            select(Article)
            .join(Feed)
            .join(Feed.topics)
            .where(Topic.id == topic_id)
            .where(Article.fetched_at >= since)
            .order_by(Article.published_at.desc())
            .limit(60)
        )

    articles = (await db.execute(stmt)).scalars().all()

    if not articles:
        return None

    articles_text = "\n\n".join(
        f"Source: {a.feed_id}\nTitle: {a.title}\nExcerpt: {(a.excerpt or '')[:300]}"
        for a in articles
    )

    model = await _get_ollama_model()
    prompt = f"""You are a news curator. Based on the articles below from {target_date}, write a concise daily digest for the topic "{topic_name}".

Structure your response as:
1. **Overview** — 2-3 sentence summary of the day
2. **Top Stories** — 3-5 bullets, one sentence each
3. **Trends** — brief note on any patterns

Be concise and direct. No filler.

Articles:
{articles_text}"""

    client = AsyncClient(host=app_settings.ollama_base_url)
    response = await client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.message.content


async def summarize_article(article) -> str | None:
    """Generate a concise summary for a single article using Ollama."""
    content = article.full_content or article.excerpt or ""
    if not content.strip():
        return None

    model = await _get_ollama_model()
    text = content[:4000]  # Cap to avoid context overflow
    prompt = f"""Summarize the following article in 3-5 sentences. Be concise and factual. Do not add opinion.

Title: {article.title}

Content:
{text}"""

    client = AsyncClient(host=app_settings.ollama_base_url)
    response = await client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.message.content


async def extract_entities(article) -> list[dict]:
    """Extract named entities from an article using Ollama. Returns list of {name, type} dicts."""
    content = article.full_content or article.excerpt or ""
    if not content.strip():
        return []

    import json, re as _re
    model = await _get_ollama_model()
    text = content[:3000]
    prompt = f"""Extract named entities from this article. Return ONLY a JSON array.
Each item: {{"name": "...", "type": "PERSON|ORG|PLACE|TOPIC|PRODUCT|EVENT"}}
Extract up to 10 entities. Return [] if none found.

Title: {article.title}
Content: {text}"""

    client = AsyncClient(host=app_settings.ollama_base_url)
    try:
        response = await client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.message.content
        match = _re.search(r'\[.*\]', raw, _re.DOTALL)
        if not match:
            return []
        return json.loads(match.group())
    except Exception as e:
        logger.warning(f"Entity extraction failed: {e}")
        return []


async def generate_all_digests(target_date: str | None = None, topic_id: int | None = None):
    if target_date is None:
        target_date = date.today().isoformat()

    model = await _get_ollama_model()

    async with SessionLocal() as db:
        if topic_id is not None:
            # Generate for a specific topic only
            topic = await db.get(Topic, topic_id)
            topics_to_process = [(topic_id, topic.name if topic else "Unknown")]
        else:
            # Generate global + per-topic
            topics = (await db.execute(select(Topic))).scalars().all()
            topics_to_process = [(None, "All Topics")] + [(t.id, t.name) for t in topics]

        for tid, tname in topics_to_process:
            # Skip if already generated today
            existing = await db.execute(
                select(Digest).where(Digest.date == target_date, Digest.topic_id == tid)
            )
            if existing.scalar_one_or_none():
                logger.info(f"Digest already exists for {tname} on {target_date}")
                continue

            logger.info(f"Generating digest for '{tname}'...")
            content = await generate_digest_for_topic(tid, tname, target_date, db)

            if content:
                digest = Digest(
                    date=target_date,
                    topic_id=tid,
                    content=content,
                    model_used=model,
                )
                db.add(digest)

        await db.commit()
        logger.info("Digest generation complete")
