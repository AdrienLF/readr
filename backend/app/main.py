from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db, _seed_feeds_if_empty
from .services.scheduler import start_scheduler, stop_scheduler
from .routers import feeds, articles, topics, digests, settings, filters, tags, rules


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _seed_feeds_if_empty()
    await start_scheduler()
    yield
    await stop_scheduler()


app = FastAPI(title="RSS Reader", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(feeds.router, prefix="/api/feeds", tags=["feeds"])
app.include_router(articles.router, prefix="/api/articles", tags=["articles"])
app.include_router(topics.router, prefix="/api/topics", tags=["topics"])
app.include_router(digests.router, prefix="/api/digests", tags=["digests"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(filters.router, prefix="/api/filters", tags=["filters"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
app.include_router(rules.router, prefix="/api/rules", tags=["rules"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
