# Readr — Personal RSS Reader

## What is this?

Readr is a self-hosted, single-user RSS reader designed to give back control over your information diet. It aggregates content from RSS/Atom feeds, Reddit subreddits, Bluesky accounts (via RSSHub), and any other RSS-compatible sources into a clean, fast, visual interface. At the end of each day, a local LLM generates a digest of the most important stories across your chosen topics — no cloud, no tracking, no algorithmic interference.

## Goals

- **Full-text reading** — fetches and stores complete article content server-side, not just summaries
- **Topic organization** — feeds can belong to multiple topics (many-to-many relationship)
- **Reddit first-class** — Reddit posts include live threaded comment trees via the Reddit JSON API
- **Daily AI digest** — Ollama + Qwen3:8b summarizes the day's stories per topic, scheduled at a configurable time (default 7am)
- **Read tracking + bookmarks** — per-article state, persistent
- **Full-text search** — SQLite FTS5, no external search service needed
- **Mobile-friendly** — responsive UI, accessible over Tailscale from any device
- **Self-contained** — runs entirely in Docker Compose, all data stays local

## Non-Goals

- Multi-user support (single user, no auth)
- Twitter/X integration (API too restrictive and expensive)
- Cloud sync or remote storage
- Public internet exposure (intended for a private Tailscale network)

---

## Architecture

### Services (Docker Compose)

| Service | Image/Tech | Port (internal) | Purpose |
|---|---|---|---|
| `nginx` | nginx:alpine | 80 (exposed) | Reverse proxy: `/api/*` → backend, `/*` → frontend |
| `backend` | Python 3.12 + FastAPI | 8000 | REST API, feed polling, digest generation |
| `frontend` | Node 22 + SvelteKit | 3000 | UI (server-side rendered, node adapter) |
| `rsshub` | diygod/rsshub | 1200 | Converts social platforms → RSS (Bluesky, etc.) |
| `ollama` | ollama/ollama | 11434 | Local LLM inference (GPU or CPU) |

GPU passthrough is enabled via `docker-compose.gpu.yml` (requires NVIDIA Container Toolkit or Docker Desktop WSL2 GPU support). The `start.sh` script auto-detects `nvidia-smi` and selects the correct compose file.

### Backend (`backend/`)

Built with **FastAPI** + **SQLAlchemy 2 (async)** + **aiosqlite**. Dependency management via **UV**.

```
app/
├── main.py           FastAPI app, lifespan (init DB + start scheduler)
├── config.py         Pydantic settings (env vars + .env)
├── database.py       Async engine, session factory, init_db() (FTS5 setup)
├── models.py         ORM models
├── schemas.py        Pydantic request/response schemas
├── routers/
│   ├── feeds.py      Feed CRUD + refresh triggers
│   ├── articles.py   Article list/get/search + read/bookmark/comments
│   ├── topics.py     Topic CRUD
│   ├── digests.py    Digest list + generation trigger
│   └── settings.py  App settings get/update (also reschedules APScheduler)
└── services/
    ├── fetcher.py    feedparser polling, Reddit normalization, comment scraping
    ├── extractor.py  trafilatura full-text + excerpt + image extraction
    ├── scheduler.py  APScheduler: feed polling (interval) + digest (cron)
    └── llm.py        Ollama async client, per-topic digest generation
```

### Data Model

```
feeds          id, url (unique), title, description, source_type, favicon_url,
               last_fetched, poll_interval, created_at

articles       id, feed_id (FK), title, url (unique), excerpt, full_content,
               image_url, author, published_at, fetched_at, is_read, is_bookmarked

topics         id, name, color (#hex), icon, created_at

feed_topics    feed_id ↔ topic_id  (many-to-many association table)

digests        id, date (YYYY-MM-DD), topic_id (nullable = global), content,
               model_used, generated_at

settings       key (PK), value

articles_fts   SQLite FTS5 virtual table (content table on articles)
               — kept in sync via SQL triggers (INSERT/UPDATE/DELETE)
```

### Frontend (`frontend/`)

Built with **SvelteKit 2** + **Svelte 5** (runes mode) + **TailwindCSS 3** + **@tailwindcss/typography**.

```
src/
├── app.html / app.css        HTML shell, global styles, Tailwind base
├── routes/
│   ├── +layout.svelte        App shell: Sidebar + ArticleReader + Modals + MobileNav
│   ├── +page.svelte          Main feed (all articles or by selected topic)
│   ├── bookmarks/            Bookmarked articles
│   ├── search/               Full-text search with debounce
│   ├── digest/               Daily digest viewer + manual generation trigger
│   └── settings/             Feed management, topic management, app config
└── lib/
    ├── api.js                Typed fetch wrapper for all backend endpoints
    ├── stores/
    │   └── app.svelte.js     Global reactive state (Svelte 5 class with $state runes)
    └── components/
        ├── Sidebar.svelte    Left nav: topics, main nav, add feed/refresh
        ├── ArticleList.svelte Paginated card grid, filter by topic/feed/bookmarks
        ├── ArticleCard.svelte Card with image, title, excerpt, bookmark toggle
        ├── ArticleReader.svelte Slide-in panel: full content, Reddit comments
        ├── CommentThread.svelte Recursive Reddit comment tree (max 3 levels deep)
        ├── AddFeedModal.svelte  Add feed + assign topics
        ├── TopicModal.svelte    Create topic with color picker
        └── MobileNav.svelte     Bottom tab bar (mobile only)
```

**Design system:** Dark-first (zinc scale), violet accent, `@tailwindcss/typography` for article prose, smooth slide-in transitions for the reader panel.

### Key Flows

**Feed polling:**
APScheduler fires every `fetch_interval` seconds (default: 3600). For each feed:
1. `feedparser.parse(url)` — get entries
2. Deduplicate by URL
3. For new articles: `trafilatura` fetches and extracts full HTML content, excerpt, image
4. Reddit self-posts skip the external fetch (content already in RSS)
5. Store in `articles` table; FTS5 triggers update the search index automatically

**Article reading:**
User clicks card → `app.openArticle(id)` → ArticleReader slides in → `GET /api/articles/:id` (returns full_content) → renders with `{@html}` into `.article-content` (prose styles). `is_read` is set on open.

**Reddit comments:**
"Comments" button → `GET /api/articles/:id/comments` → backend extracts post ID from URL → calls `reddit.com/comments/:id.json?sort=top&depth=4` → returns recursive comment tree → rendered by `<CommentThread>`.

**Daily digest:**
APScheduler cron fires at `digest_time` (default: `07:00`) → for each topic (+ global):
1. Query articles from last 24h in that topic
2. Build prompt with titles + excerpts
3. Ollama chat completion (`qwen3:8b`)
4. Store result in `digests` table
Can also be triggered manually via `POST /api/digests/generate`.

**Search:**
`GET /api/articles/search?q=...` → `SELECT ... FROM articles JOIN articles_fts WHERE articles_fts MATCH :q ORDER BY rank` → SQLite FTS5 BM25 ranking.

---

## API Reference

```
GET    /api/feeds                     List all feeds with unread counts
POST   /api/feeds                     Add feed (auto-discovers title, type)
GET    /api/feeds/:id                 Get single feed
PUT    /api/feeds/:id                 Update title, poll_interval, topics
DELETE /api/feeds/:id                 Delete feed + cascade articles
POST   /api/feeds/:id/refresh         Trigger immediate fetch (background)
POST   /api/feeds/refresh-all         Refresh all feeds (background)

GET    /api/articles?topic_id&feed_id&is_read&is_bookmarked&page&page_size
GET    /api/articles/search?q&page
GET    /api/articles/:id              Full article including content
PATCH  /api/articles/:id/read         Mark read/unread (?is_read=true/false)
PATCH  /api/articles/:id/bookmark     Toggle bookmark
GET    /api/articles/:id/comments     Reddit comment tree (Reddit feeds only)

GET    /api/topics                    List topics with feed counts
POST   /api/topics                    Create topic
PUT    /api/topics/:id                Update name/color/icon
DELETE /api/topics/:id                Delete topic (feeds unaffected)

GET    /api/digests?target_date       List digests for a date (default: today)
POST   /api/digests/generate          Trigger digest generation (background)

GET    /api/settings                  Get all settings
PUT    /api/settings                  Update settings (also reschedules jobs)

GET    /api/health                    Health check
```

---

## Development

### First-time setup

```bash
# Pull Ollama model after first docker compose up
docker exec -it rss-reader-ollama-1 ollama pull qwen3:8b
```

### Running

```bash
# Auto-detects GPU
bash start.sh

# Force CPU
docker compose up -d

# Force GPU (requires NVIDIA Container Toolkit)
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

Access at `http://localhost` (or your Tailscale IP on port 80).

### Backend development

```bash
cd backend
uv sync
uv run pytest                  # run all tests
uv run pytest tests/unit/      # unit tests only
uv run pytest tests/api/       # API tests only
uv run uvicorn app.main:app --reload  # local dev server
```

### Frontend development

```bash
cd frontend
npm install
npm run dev        # dev server on :5173
npm run build      # production build
npm test           # vitest unit tests
npx playwright test  # E2E tests (requires app running)
```

---

## Configuration (via Settings UI or environment)

| Setting | Default | Description |
|---|---|---|
| `digest_time` | `07:00` | Daily digest cron time (HH:MM) |
| `ollama_model` | `qwen3:8b` | Ollama model to use for digests |
| `fetch_interval` | `3600` | Feed poll interval in seconds |

Environment variables (override defaults):
- `OLLAMA_BASE_URL` — default `http://ollama:11434`
- `RSSHUB_BASE_URL` — default `http://rsshub:1200`
- `DATABASE_URL` — default `sqlite+aiosqlite:////app/data/rss_reader.db`

---

## Adding feeds

| Source | URL format |
|---|---|
| Any RSS/Atom | Direct feed URL |
| Reddit subreddit | `https://www.reddit.com/r/{subreddit}.rss` |
| Bluesky user | `http://rsshub:1200/bsky/user/{handle}` |
| YouTube channel | `http://rsshub:1200/youtube/user/{username}` |
| GitHub releases | `https://github.com/{user}/{repo}/releases.atom` |

RSSHub supports hundreds of additional sources — see [docs.rsshub.app](https://docs.rsshub.app) for the full list.
