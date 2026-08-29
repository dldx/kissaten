# ☕ Kissaten - Coffee Bean Discovery Platform

A coffee bean database and search application that scrapes coffee bean information from roasters worldwide (~400 roasters) and provides a modern interface to discover and explore specialty coffee.

## ✨ Features

- **🔍 Unified Search**: Search and filter across beans, roasters, origins, tasting notes, varietals, processes, and flavours with a single query or advanced filters
- **🏷️ Faceted Filtering**: Refine results by origin, roaster, process, varietal, roast level, price, and availability
- **🫘 Bean Detail Pages**: Tasting notes, processing, elevation, cupping scores, pricing, and direct links to roaster sites
- **🏭 Roaster & Origin Exploration**: Browse roasters, origins by country → region → farm, and roasted-in locations with stats
- **🤖 AI Features**: AI-powered bean search (including image search) and a guided brew assistant
- **📊 Analytics & Insights**: Visualize statistics on origins, processes, varietals, and price trends
- **🧭 Guided Discovery**: Explore by flavour, process, or varietal with curated links and educational content
- **🗄️ Personal Vault**: Save and organize your favourite beans
- **🌗 Theme Toggle**: Light/dark mode
- **📱 Fully Responsive**: Mobile-first design with collapsible filters

## 🏗️ Architecture

### Backend (FastAPI + DuckDB)
- **FastAPI**: Modern, fast web framework for the API
- **DuckDB**: High-performance analytical database
- **Pydantic v2**: Data validation and serialization
- **Scrapers**: One module per roaster (~400), using httpx, BeautifulSoup4/lxml, or Playwright for JavaScript-heavy sites
- **Typer CLI**: `kissaten` command-line interface for scraping, refresh, and validation workflows
- **Logfire**: Observability and telemetry

### Frontend (SvelteKit + shadcn-svelte)
- **SvelteKit**: Full-stack web framework (Svelte 5 runes)
- **shadcn-svelte / bits-ui**: Accessible UI components
- **Tailwind CSS v4**: Utility-first CSS
- **TypeScript**: Type-safe JavaScript
- **Bun**: Package manager and dev server

### Data
Scraped data is stored as per-bean JSON files with incremental diff updates, then loaded into DuckDB for querying. See [docs/INCREMENTAL_DATABASE_UPDATES.md](docs/INCREMENTAL_DATABASE_UPDATES.md) for details.

## 🛠️ Getting Started

### Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- [Bun](https://bun.sh) 1.0+
- (Optional) HTTP proxy if scraping from behind one

### Backend Setup

```bash
uv sync
cp env.example .env   # optional: add API keys / proxy settings
```

Start the API server:

```bash
uv run kissaten serve              # API at http://localhost:8000
uv run kissaten serve --reload     # dev mode with auto-reload
uv run kissaten dev --frontend     # API + frontend together
```

> Note: `serve` opens the production database read-only. Writes happen through the refresh pipeline — see [docs/TESTING.md](docs/TESTING.md) for the database modes.

### Frontend Setup

```bash
cd frontend
bun install
bun run dev
```

The frontend will be available at `http://localhost:5173` and proxies API calls to `:8000`.

## 🔄 Data Pipeline

1. **Scrape**: `kissaten run-all-scrapers` (or `kissaten scrape <roaster>`) writes per-bean JSON + diff artifacts into `data/roasters/<roaster>/<YYYYMMDD>/`
2. **Refresh**: `kissaten refresh --incremental` applies the diffs to the read-write DuckDB
3. **Validate**: `kissaten validate-db` runs integrity checks before promotion
4. **Promote**: `cp data/rw_kissaten.duckdb data/kissaten.duckdb` swaps the validated database into production

See [docs/SCHEDULING.md](docs/SCHEDULING.md) for the recommended hourly scheduling setup.

## 🧭 CLI Commands

Common `kissaten` commands:

| Command | Purpose |
| --- | --- |
| `scrape <roaster>` / `test-scraper` | Scrape or test a single roaster |
| `run-all-scrapers` | Run all scrapers (supports batched scheduling) |
| `refresh` | Apply scraped diffs to the read-write database |
| `validate-db` | Validate the database before promotion |
| `serve` / `dev` | Run the API (and optionally the frontend) |
| `show-bean` | Inspect a scraped bean record |
| `apply-review-decisions` | Apply admin tasting-kit review decisions |
| `categorize-*` / `validate-mappings` | Manage origin, process, varietal, and tasting-note mappings |

## 🔌 API Endpoints

All routes live under `/v1`:

- `GET /v1/search` - Search coffee beans with filters
- `GET /v1/beans/{roaster_slug}/{bean_slug}` - Get a specific bean (+ `/recommendations`)
- `GET /v1/roasters` - List roasters
- `GET /v1/origins` - Explore origins, regions, and farms
- `GET /v1/processes` / `GET /v1/varietals` - Processing methods and varietals
- `GET /v1/tasting-note-categories` - Tasting notes and flavour categories
- `POST /v1/ai/search` (+ `/extract`, `/imagesearch`) - AI-powered search
- `POST /v1/brew-assistant` - Guided brew recommendations
- `GET /v1/stats` / `GET /v1/health` - Statistics and health checks

The full route list lives in `src/kissaten/api/main.py`.

## 🧪 Development

### Adding New Scrapers

See [ADDING_SCRAPERS.md](ADDING_SCRAPERS.md) for the full walkthrough. Platform-specific patterns (Shopify, Squarespace, and general) are documented as skills in `.opencode/skills/` — each comes with a ready-made scraper template. Register new scrapers in `src/kissaten/scrapers/registry.py` and add tests in `tests/unit/`.

### Proxy Configuration

Scrapers support HTTP/HTTPS proxies via environment variables in `.env`:

```bash
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
```

Both httpx and Playwright use the configured proxy; `HTTPS_PROXY` wins when both are set. See [docs/PROXY_CONFIGURATION.md](docs/PROXY_CONFIGURATION.md).

### Tests

```bash
uv run pytest        # backend tests (DB isolation handled automatically)
cd frontend && bun run test   # frontend unit + integration tests
```

## 🤝 Contributing

Contributions are welcome! See [AGENTS.md](AGENTS.md) for project conventions, then open a pull request.

## 🙏 Acknowledgments

Thanks to all the specialty coffee roasters who make their bean information publicly available, enabling this project to help coffee enthusiasts discover amazing beans from around the world.