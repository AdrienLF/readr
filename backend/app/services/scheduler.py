import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from ..database import SessionLocal
from ..models import Feed, Setting

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def _refresh_all_feeds():
    from .fetcher import fetch_and_store_feed
    async with SessionLocal() as db:
        feeds = (await db.execute(select(Feed))).scalars().all()
    for feed in feeds:
        try:
            await fetch_and_store_feed(feed.id)
        except Exception as e:
            logger.error(f"Error fetching feed {feed.id}: {e}")


async def _run_daily_digest():
    from .llm import generate_all_digests
    try:
        await generate_all_digests()
    except Exception as e:
        logger.error(f"Digest generation error: {e}")


async def _get_setting(key: str, default: str) -> str:
    async with SessionLocal() as db:
        row = await db.get(Setting, key)
        return row.value if row and row.value else default


async def start_scheduler():
    digest_time = await _get_setting("digest_time", "07:00")
    fetch_interval = int(await _get_setting("fetch_interval", "3600"))

    hour, minute = digest_time.split(":")

    scheduler.add_job(
        _refresh_all_feeds,
        IntervalTrigger(seconds=fetch_interval),
        id="refresh_feeds",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        _run_daily_digest,
        CronTrigger(hour=int(hour), minute=int(minute)),
        id="daily_digest",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f"Scheduler started — feeds every {fetch_interval}s, digest at {digest_time}")

    # Initial fetch on startup
    scheduler.add_job(_refresh_all_feeds, id="startup_fetch", replace_existing=True)


async def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)


async def reschedule(digest_time: str | None = None, fetch_interval: int | None = None):
    """Called from settings update to reschedule jobs."""
    if fetch_interval is not None:
        scheduler.reschedule_job(
            "refresh_feeds",
            trigger=IntervalTrigger(seconds=fetch_interval),
        )

    if digest_time is not None:
        hour, minute = digest_time.split(":")
        scheduler.reschedule_job(
            "daily_digest",
            trigger=CronTrigger(hour=int(hour), minute=int(minute)),
        )
