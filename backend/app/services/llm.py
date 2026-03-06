import logging
from datetime import date, datetime, timedelta, timezone
from ollama import AsyncClient
from sqlalchemy import select, delete
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
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)

    if topic_id is None:
        stmt = (
            select(Article)
            .options(selectinload(Article.feed))
            .where(Article.fetched_at >= since)
            .order_by(Article.published_at.desc())
            .limit(200)
        )
    else:
        stmt = (
            select(Article)
            .join(Feed)
            .join(Feed.topics)
            .options(selectinload(Article.feed))
            .where(Topic.id == topic_id)
            .where(Article.fetched_at >= since)
            .order_by(Article.published_at.desc())
            .limit(200)
        )

    articles = (await db.execute(stmt)).scalars().all()

    if not articles:
        return None

    # Group articles by source for better context
    from collections import defaultdict
    by_source = defaultdict(list)
    for a in articles:
        source = a.feed.title if a.feed else f"Feed #{a.feed_id}"
        by_source[source].append(a)

    articles_text = ""
    for source, arts in by_source.items():
        articles_text += f"\n### {source} ({len(arts)} articles)\n"
        for a in arts[:5]:  # max 5 per source to keep prompt manageable
            excerpt = (a.excerpt or "")[:200].replace("\n", " ")
            articles_text += f"- [{a.title}]({a.url})"
            if excerpt:
                articles_text += f" — {excerpt}"
            articles_text += "\n"
        if len(arts) > 5:
            articles_text += f"  ...and {len(arts) - 5} more\n"

    n_sources = len(by_source)
    n_articles = len(articles)

    model = await _get_ollama_model()
    prompt = f"""You are a personal news curator for someone with extremely diverse interests, from tech and AI to woodworking, cooking, finance, music production, travel, and many more. Today is {target_date}. You are summarizing their "{topic_name}" feed.

You have {n_articles} articles from {n_sources} sources in the last 24 hours.

Write a daily digest structured as follows:

1. **Highlights** — The 3-5 most interesting/important stories across all sources. One short paragraph each with the source name.
2. **By Theme** — Group the remaining noteworthy content into thematic sections (e.g. "Tech & AI", "Making & Crafting", "Food & Cooking", "Finance", etc.). Use 3-8 themes based on what's actually present. Each theme gets 2-5 bullet points. Skip themes with nothing interesting.
3. **Quick Hits** — A rapid-fire list of 5-10 other things worth a glance, one line each.

Guidelines:
- IMPORTANT: Every story you mention MUST be a markdown link to the original article. Use the exact URLs from the input. Format: [short description](url). Never fabricate URLs.
- Be concise but specific — include concrete details, not vague summaries
- Prioritize surprising, useful, or actionable content over routine posts
- Skip low-quality, repetitive, or clickbait content entirely
- Use the actual source/subreddit names so the reader knows where things came from
- Do not invent or hallucinate content — only summarize what's in the articles below

Articles by source:
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


async def generate_all_digests(target_date: str | None = None, topic_id: int | None = None, force: bool = False):
    if target_date is None:
        target_date = date.today().isoformat()

    model = await _get_ollama_model()

    async with SessionLocal() as db:
        if force:
            stmt_del = delete(Digest).where(Digest.date == target_date)
            if topic_id is not None:
                stmt_del = stmt_del.where(Digest.topic_id == topic_id)
            await db.execute(stmt_del)
            await db.commit()
            logger.info(f"Force-deleted existing digests for {target_date}")

        if topic_id is not None:
            # Generate for a specific topic only
            topic = await db.get(Topic, topic_id)
            topics_to_process = [(topic_id, topic.name if topic else "Unknown")]
        else:
            # Generate global + per-topic
            topics = (await db.execute(select(Topic))).scalars().all()
            topics_to_process = [(None, "All Topics")] + [(t.id, t.name) for t in topics]

        for tid, tname in topics_to_process:
            # Skip if already generated (unless force)
            if not force:
                existing = await db.execute(
                    select(Digest).where(Digest.date == target_date, Digest.topic_id == tid)
                )
                if existing.scalars().first():
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
