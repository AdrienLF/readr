# Readr

A self-hosted, single-user RSS reader with full-text article fetching, Reddit comment threads, and a daily AI digest — no cloud, no tracking, no algorithmic interference.

![Stack](https://img.shields.io/badge/backend-FastAPI-009688?style=flat-square) ![Stack](https://img.shields.io/badge/frontend-SvelteKit-FF3E00?style=flat-square) ![Stack](https://img.shields.io/badge/db-SQLite-003B57?style=flat-square) ![Stack](https://img.shields.io/badge/deploy-Docker_Compose-2496ED?style=flat-square)

> **Heads up:** This project was vibe-coded — built iteratively with AI assistance, not architected upfront. I use it every day as my primary RSS reader and it works well for me, but it hasn't been battle-tested by a wide audience. Expect rough edges. Issues and PRs are welcome.

## Features

- **Full-text reading** — fetches and stores complete article content server-side via trafilatura
- **Topic organization** — organize feeds into topics (many-to-many); filter your reading by topic
- **Bulk feed import with AI classification** — paste a list of URLs (or any text containing URLs) and let the local LLM auto-classify them into topics, with a review step before import
- **Inline topic creation** — create new topics on the fly when adding a feed, no separate modal needed
- **Reddit first-class** — Reddit posts include live threaded comment trees, upvotes, and comment counts
- **Daily AI digest** — local LLM (Ollama + Qwen3.5:9b) summarizes the day's stories per topic at a configurable time
- **Article summarization** — on-demand per-article summaries via local LLM, cached after first generation
- **Named entity extraction** — extract people, organizations, places, and topics from articles; view trending entities
- **Read tracking & bookmarks** — per-article state, persisted in SQLite
- **Save for later** — separate saved-articles list, distinct from bookmarks
- **Tags & automation rules** — color-coded tags and fetch-time rules (auto-bookmark, auto-tag, auto-mute)
- **Mute filters** — drop articles matching patterns (plain text or regex) at fetch time, globally or per-feed
- **Smart searches** — saved search queries with automatic article matching
- **Full-text search** — SQLite FTS5, BM25 ranking, no external service needed
- **OPML import/export** — standard feed list exchange; OPML folders become topics on import
- **Article highlights & notes** — highlight text passages and attach private notes to any article
- **Priority scoring** — articles scored based on thumbs-up/down signals per feed
- **Mobile-friendly** — responsive UI with bottom navigation, accessible over Tailscale from any device
- **Self-contained** — runs entirely in Docker Compose; all data stays local

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async), aiosqlite |
| Frontend | SvelteKit 2, Svelte 5 (runes), TailwindCSS 3 |
| Database | SQLite with FTS5 full-text search |
| LLM | Ollama (local inference, GPU or CPU) |
| Feed conversion | RSSHub (Bluesky, YouTube, and 400+ other sources) |
| Deployment | Docker Compose + nginx reverse proxy |

## Quick Start

```bash
git clone https://github.com/AdrienLF/readr
cd readr

# Pull the Ollama model (first run only)
docker compose up -d ollama
docker exec -it readr-ollama-1 ollama pull qwen3.5:9b

# Start everything (auto-detects GPU)
bash start.sh
```

Open `http://localhost:7755` in your browser.

### GPU support

The `start.sh` script auto-detects `nvidia-smi` and enables GPU passthrough if available (requires NVIDIA Container Toolkit or Docker Desktop with WSL2 GPU support). To force CPU mode:

```bash
docker compose up -d
```

## Adding Feeds

| Source | URL format |
|---|---|
| Any RSS/Atom feed | Direct feed URL |
| Reddit subreddit | `https://www.reddit.com/r/{subreddit}.rss` |
| Bluesky user | `http://rsshub:1200/bsky/user/{handle}` |
| YouTube channel | `http://rsshub:1200/youtube/user/{username}` |
| GitHub releases | `https://github.com/{user}/{repo}/releases.atom` |

RSSHub supports hundreds of additional sources — see [docs.rsshub.app](https://docs.rsshub.app).

## Configuration

Settings are available through the UI (`/settings`) or via environment variables:

| Setting | Default | Description |
|---|---|---|
| `digest_time` | `07:00` | Daily digest generation time (HH:MM) |
| `ollama_model` | `qwen3.5:9b` | Ollama model used for digests |
| `fetch_interval` | `3600` | Feed poll interval in seconds |

Environment variables:

| Variable | Default |
|---|---|
| `OLLAMA_BASE_URL` | `http://ollama:11434` |
| `RSSHUB_BASE_URL` | `http://rsshub:1200` |
| `DATABASE_URL` | `sqlite+aiosqlite:////app/data/rss_reader.db` |

## Development

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload  # dev server on :8000
uv run pytest                          # run all tests
```

### Frontend

```bash
cd frontend
npm install
npm run dev    # dev server on :5173
npm test       # unit tests (vitest)
```

### Architecture

```
readr/
├── backend/
│   └── app/
│       ├── main.py          FastAPI app + lifespan
│       ├── models.py        SQLAlchemy ORM models
│       ├── schemas.py       Pydantic schemas
│       ├── routers/         REST API endpoints
│       └── services/
│           ├── fetcher.py   Feed polling + Reddit normalization
│           ├── extractor.py Full-text extraction (trafilatura)
│           ├── scheduler.py    APScheduler (poll + digest cron)
│           ├── llm.py          Ollama digest generation
│           └── smart_search.py Saved-search matching
└── frontend/
    └── src/
        ├── routes/          SvelteKit pages
        └── lib/
            ├── api.js       Typed fetch wrapper
            ├── stores/      Svelte 5 reactive state
            └── components/  UI components
```

## Security

Readr is designed for **local / private network use** (e.g. behind Tailscale). It has no authentication layer — anyone who can reach the port can use it. Do not expose it to the public internet.

Protections in place:
- **XSS** — all rendered HTML from feeds and LLM output is sanitized with DOMPurify
- **SSRF** — feed URL validation blocks private IPs, loopback, link-local, and internal Docker hostnames
- **ReDoS** — mute-filter regex patterns are validated against nested quantifiers
- **Docker** — backend and frontend containers run as non-root users
- **Nginx** — security headers (X-Frame-Options, X-Content-Type-Options, Referrer-Policy)

## Non-Goals

- Multi-user / auth (single-user by design)
- Cloud sync or remote storage
- Twitter/X integration
- Public internet exposure (designed for a private network / Tailscale)

## License

MIT
