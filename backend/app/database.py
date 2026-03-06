import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text, select
from .config import settings

logger = logging.getLogger(__name__)

# seeds/feeds.opml lives two levels above this file: backend/app/ → backend/ → repo root
_SEEDS_OPML = Path(__file__).parent.parent.parent / "seeds" / "feeds.opml"


engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # FTS5 virtual table for full-text search
        await conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts
            USING fts5(title, excerpt, full_content, content='articles', content_rowid='id')
        """))

        # Triggers to keep FTS in sync
        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
                INSERT INTO articles_fts(rowid, title, excerpt, full_content)
                VALUES (new.id, new.title, new.excerpt, new.full_content);
            END
        """))
        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
                INSERT INTO articles_fts(articles_fts, rowid, title, excerpt, full_content)
                VALUES('delete', old.id, old.title, old.excerpt, old.full_content);
                INSERT INTO articles_fts(rowid, title, excerpt, full_content)
                VALUES (new.id, new.title, new.excerpt, new.full_content);
            END
        """))
        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
                INSERT INTO articles_fts(articles_fts, rowid, title, excerpt, full_content)
                VALUES('delete', old.id, old.title, old.excerpt, old.full_content);
            END
        """))

        # Seed default settings
        await conn.execute(text("""
            INSERT OR IGNORE INTO settings(key, value) VALUES
                ('digest_time', '07:00'),
                ('ollama_model', 'qwen3.5:9b'),
                ('fetch_interval', '3600')
        """))

        # Column migrations for existing databases (SQLite has no IF NOT EXISTS for ALTER)
        migrations = [
            "ALTER TABLE feeds ADD COLUMN last_error TEXT",
            "ALTER TABLE feeds ADD COLUMN error_count INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE feeds ADD COLUMN is_muted INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE articles ADD COLUMN audio_url TEXT",
            "ALTER TABLE articles ADD COLUMN is_saved INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE articles ADD COLUMN note TEXT",
            "ALTER TABLE articles ADD COLUMN summary TEXT",
            "ALTER TABLE articles ADD COLUMN priority_score REAL NOT NULL DEFAULT 0.5",
            "ALTER TABLE articles ADD COLUMN score INTEGER",
            "ALTER TABLE articles ADD COLUMN comment_count INTEGER",
        ]
        for sql in migrations:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass  # Column already exists



async def _seed_feeds_if_empty():
    """Insert feeds from seeds/feeds.opml on first run (when feeds table is empty)."""
    if not _SEEDS_OPML.exists():
        return

    from .models import Feed  # local import to avoid circular deps at module load

    async with SessionLocal() as db:
        count = (await db.execute(text("SELECT COUNT(*) FROM feeds"))).scalar()
        if count and count > 0:
            return

        try:
            root = ET.parse(_SEEDS_OPML).getroot()
        except ET.ParseError as e:
            logger.warning(f"Failed to parse seeds/feeds.opml: {e}")
            return

        body = root.find("body")
        if body is None:
            return

        def _source_type(xml_url: str) -> str:
            if "reddit.com" in xml_url:
                return "reddit"
            return "rss"

        inserted = 0
        for outline in body.iter("outline"):
            xml_url = outline.get("xmlUrl")
            if not xml_url:
                continue
            title = outline.get("title") or outline.get("text") or xml_url
            feed = Feed(url=xml_url, title=title, source_type=_source_type(xml_url))
            db.add(feed)
            inserted += 1

        await db.commit()
        logger.info(f"Seeded {inserted} feed(s) from seeds/feeds.opml")
