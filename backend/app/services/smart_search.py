"""
Smart search service.

- Ollama expands a natural-language query into a list of related terms (cached 7 days).
- Matching is pure string ops (no extra LLM calls per article): fast enough to run
  inline after every feed fetch.
- Score = fraction of expanded terms found in title + excerpt + content.
"""
import json
import logging
import re
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import SessionLocal
from ..models import Article, SavedSearch, ArticleSearchMatch, Setting
from ..config import settings as app_settings

logger = logging.getLogger(__name__)

TERMS_TTL_DAYS = 7
MIN_SCORE = 0.08  # at least ~1-2 terms must match


async def _get_ollama_model() -> str:
    async with SessionLocal() as db:
        row = await db.get(Setting, "ollama_model")
        return (row.value if row and row.value else None) or app_settings.ollama_model


async def expand_query(query: str) -> list[str]:
    """Ask Ollama to expand a search query into related terms. Falls back to query words."""
    try:
        from ollama import AsyncClient
        client = AsyncClient(host=app_settings.ollama_base_url)

        # Prefer the configured model; fall back to first available
        model = await _get_ollama_model()
        try:
            available = [m.model for m in (await client.list()).models]
        except Exception:
            available = []
        if available and model not in available:
            model = available[0]

        prompt = (
            f'Generate 15-20 short search terms (keywords and short phrases) that would help '
            f'find articles about: "{query}". Include synonyms, related concepts, and common '
            f'ways people refer to this topic. Return ONLY a JSON array of strings, nothing else.'
        )
        response = await client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3},
        )
        raw = response.message.content.strip()
        # Extract JSON array even if wrapped in markdown
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            terms = json.loads(match.group())
            if isinstance(terms, list) and terms:
                logger.info(f"Expanded '{query}' → {len(terms)} terms via {model}")
                return [str(t).lower().strip() for t in terms if t]
    except Exception as e:
        logger.warning(f"Ollama expansion failed for '{query}': {e}")

    # Fallback: split the query into words
    return [w.lower() for w in re.findall(r'\w+', query) if len(w) > 2]


def _score_article(article: Article, terms: list[str]) -> float:
    """Return fraction of terms found in the article text."""
    text = " ".join(filter(None, [
        article.title,
        article.excerpt,
        article.full_content,
    ])).lower()
    matched = sum(1 for t in terms if t in text)
    return matched / len(terms) if terms else 0.0


async def refresh_search_terms(search: SavedSearch, db: AsyncSession) -> list[str]:
    """Expand the query via Ollama and persist the terms (or parse comma-separated keywords for strict mode)."""
    if search.is_strict:
        terms = [t.strip().lower() for t in search.query.split(",") if t.strip()]
    else:
        terms = await expand_query(search.query)
    search.expanded_terms = terms
    search.terms_refreshed_at = datetime.now(timezone.utc)
    await db.commit()
    return terms


async def match_article_to_all_searches(article: Article, db: AsyncSession):
    """Score a single article against all saved searches and persist matches."""
    searches = (await db.execute(select(SavedSearch))).scalars().all()
    if not searches:
        return

    for search in searches:
        # Refresh terms if stale or missing
        if not search.expanded_terms or (
            search.terms_refreshed_at and
            datetime.now(timezone.utc) - search.terms_refreshed_at.replace(tzinfo=timezone.utc)
            > timedelta(days=TERMS_TTL_DAYS)
        ):
            await refresh_search_terms(search, db)

        terms = search.expanded_terms or []
        score = _score_article(article, terms)
        if score < MIN_SCORE:
            continue

        # Upsert match
        existing = await db.get(ArticleSearchMatch, (article.id, search.id))
        if existing:
            existing.score = score
        else:
            db.add(ArticleSearchMatch(
                article_id=article.id,
                search_id=search.id,
                score=score,
            ))

    await db.commit()


async def backfill_search(search_id: int):
    """Run a saved search against all existing articles (called after creation)."""
    async with SessionLocal() as db:
        search = await db.get(SavedSearch, search_id)
        if not search:
            return

        if not search.expanded_terms:
            await refresh_search_terms(search, db)

        terms = search.expanded_terms or []
        articles = (await db.execute(select(Article))).scalars().all()
        added = 0
        for article in articles:
            score = _score_article(article, terms)
            if score < MIN_SCORE:
                continue
            existing = await db.get(ArticleSearchMatch, (article.id, search.id))
            if not existing:
                db.add(ArticleSearchMatch(
                    article_id=article.id,
                    search_id=search.id,
                    score=score,
                ))
                added += 1

        search.backfill_done = True
        await db.commit()
        logger.info(f"Backfilled search '{search.name}': {added} matches from {len(articles)} articles")
