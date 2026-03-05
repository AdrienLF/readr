from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from .config import settings


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
                ('ollama_model', 'qwen3:8b'),
                ('fetch_interval', '3600')
        """))
