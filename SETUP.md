# 🚀 Kissaten Quick Setup Guide

This guide will get you up and running with the Kissaten coffee bean discovery platform in just a few minutes.

## 📋 Prerequisites

- **Python 3.10+** with `uv` package manager
- **Bun 1.0+** (recommended) or Node.js 18+

### Install Prerequisites

**Install uv (Python package manager):**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Install Bun (JavaScript runtime):**
```bash
curl -fsSL https://bun.sh/install | bash
```

## ⚡ Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd kissaten
```

### 2. Start Backend (Terminal 1)

```bash
# Install Python dependencies
uv sync

# Start the API server
uv run python -m kissaten.cli.main serve
```

The backend will be available at: http://localhost:8000

### 3. Start Frontend (Terminal 2)

```bash
# Install frontend dependencies
cd frontend
bun install

# Start the development server
bun run dev
```

The frontend will be available at: http://localhost:5173

## 🎯 What You Get

- **Backend API**: FastAPI server with automatic data loading from JSON files
- **Frontend**: Modern SvelteKit interface with shadcn-svelte components
- **Data Processing**: Automatic DuckDB database with Polars-powered data ingestion
- **Full Search**: Unified search across beans, roasters, and origins

## 📚 API Documentation

Once the backend is running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc

## 🔧 Development Commands

### Backend
```bash
uv run python -m kissaten.cli.main serve     # Start API server
uv run python -m kissaten.cli.main dev       # Start API with auto-reload
uv run python -m kissaten.cli.main dev --frontend  # Start API + Frontend
```

### Frontend
```bash
bun run dev                     # Start development server
bun run build                   # Build for production
bun run preview                 # Preview production build
bun run check                   # Type checking
bun run lint                    # Code linting
bun run format                  # Code formatting
```

## 🗂️ Data Structure

The application automatically loads coffee bean data from:
```
data/roasters/
├── a_matter_of_concrete/
├── cartwheel_coffee/
├── drop_coffee_roasters/
├── killbean/
├── people's_possession/
└── qima_cafe/
```

Each roaster directory contains timestamped folders with JSON files containing coffee bean data.

## 🚨 Troubleshooting

**Backend not starting?**
- Check Python version: `python --version`
- Ensure uv is installed: `uv --version`
- Check if port 8000 is available

**Frontend not starting?**
- Check Bun version: `bun --version`
- Clear node_modules: `rm -rf node_modules && bun install`
- Check if port 5173 is available

**No data showing?**
- Ensure data files exist in `data/roasters/`
- Check backend logs for data loading messages
- Verify API is responding: `curl http://localhost:8000/health`

## 📱 Mobile Testing

The interface is fully responsive. Test on mobile by:
1. Find your local IP: `ip addr show` or `ifconfig`
2. Access via `http://YOUR_IP:5173` on mobile device
3. Ensure your firewall allows connections on port 5173

## 🎉 You're Ready!

Visit http://localhost:5173 and start exploring coffee beans from roasters worldwide!
