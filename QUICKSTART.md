# 🚀 Kissaten Quick Start

Get Kissaten running in 2 minutes!

## One-Command Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd kissaten

# Install dependencies
uv sync

# Start development environment (API + Frontend)
uv run python -m kissaten.cli.main dev --frontend
```

That's it! 🎉

- **API**: http://localhost:8000 (with auto-reload)
- **Frontend**: http://localhost:5173 (with bun/hot-reload)
- **API Docs**: http://localhost:8000/docs

## Alternative Commands

### API Only
```bash
uv run python -m kissaten.cli.main serve --reload
```

### Production Mode
```bash
uv run python -m kissaten.cli.main serve --workers 4
```

### Frontend Only
```bash
cd frontend && bun run dev
```

## First Time Setup

If this is your first time running Kissaten, you might want to scrape some data:

```bash
# List available scrapers
uv run python -m kissaten.cli.main list-scrapers

# Scrape coffee data from a roaster (example)
uv run python -m kissaten.cli.main scrape drop_coffee

# Then start the development environment
uv run python -m kissaten.cli.main dev --frontend
```

## Need Help?

- Run any command with `--help` for detailed options
- Check the [full documentation](README.md)
- View [setup guide](SETUP.md) for troubleshooting

Happy coffee exploring! ☕
