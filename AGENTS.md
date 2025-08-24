# AGENTS.md - Kissaten Coffee Bean Scraper & Search App

This document provides comprehensive information about the Kissaten project architecture, technologies, and development guidelines for AI coding assistants and developers.

## Project Overview

Kissaten is a coffee bean database and search application that scrapes coffee bean information from individual roasters worldwide. The project consists of:

- **Backend**: Python-based scrapers and API using modern Python tooling
- **Frontend**: SvelteKit-based web application for searching and browsing coffee beans
- **Database**: DuckDB for efficient data processing and analytics
- **Data**: Structured storage of coffee bean information in JSON format

## Architecture

```
kissaten/
├── src/kissaten/           # Main Python package
│   ├── scrapers/          # Individual roaster scrapers
│   │   ├── base.py        # Base scraper class
│   │   ├── cartwheel_coffee.py   # Cartwheel Coffee scraper
│   │   └── scrapers.py      # Scrapers registry
│   ├── schemas/           # Pydantic data models
│   ├── database/          # DuckDB operations and queries
│   ├── api/               # FastAPI endpoints
│   └── cli/               # Command-line interface
├── frontend/              # SvelteKit application
│   ├── src/
│   │   ├── routes/        # SvelteKit routes
│   │   ├── lib/           # Shared components and utilities
│   │   └── app.html       # Main app template
│   └── static/            # Static assets
├── tests/                 # Unit and integration tests
├── data/                  # Scraped coffee bean data
│   └── <roaster_name>/    # Per-roaster data folders
│       └── <timestamp>/   # Timestamped scraping sessions
└── docs/                  # Project documentation
```

## Technology Stack

### Backend Technologies

- **Python 3.10+**: Core language
- **UV**: Package manager
- **Pydantic v2**: Data validation and serialization schemas
- **DuckDB**: High-performance analytical database
- **FastAPI**: Modern async web framework for APIs
- **httpx**: Async HTTP client for web scraping
- **playwright**: Browser automation for scraping
- **BeautifulSoup4**: HTML parsing for scraping
- **Typer**: CLI framework
- **pytest**: Testing framework
- **rich**: Rich terminal output for CLI

### Frontend Technologies

- **SvelteKit**: Full-stack web framework
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **Vite**: Build tool and dev server

### Data & Storage

- **DuckDB**: Primary database for analytics and queries
- **JSON**: Raw scraped data storage format
- **Parquet**: Processed data storage for analytics

## Core Components

### 1. Data Schemas (Pydantic Models)

All data structures should use Pydantic models for validation and serialization. Core models should include:

- **CoffeeBean**: Main coffee bean data model with fields for name, roaster, origin, process, price, weight, roast level, tasting notes, description, URL, scraped timestamp, and availability
- **Roaster**: Roaster information including name, website, location, and scraping configuration
- **ScrapingSession**: Metadata for scraping sessions including timestamp, roaster, success status, and error information
- **SearchQuery**: Structured search requests with filters and pagination
- **APIResponse**: Standardized API response wrapper with data, metadata, and pagination info

Use Pydantic Field validators for data cleaning and transformation. Implement custom validators for URL validation, price parsing, and date normalization.

### 2. Scrapers

Each roaster has its own scraper module in `src/kissaten/scrapers/`. All scrapers should:

- Inherit from a `BaseScraper` abstract base class
- Implement async `scrape()` method returning validated `CoffeeBean` objects
- Include error handling and retry logic
- Respect rate limiting and robots.txt
- Support both BeautifulSoup4 for simple HTML and Playwright for JavaScript-heavy sites
- Log scraping progress and errors using structured logging
- Handle pagination and lazy loading
- Validate and clean data before returning

Scraper implementations should be modular and easily testable with mock data.

### 3. Database Operations

DuckDB operations for data processing and querying should include:

- **CoffeeDatabase**: Main database interface class
- **Connection Management**: Efficient connection pooling and transaction handling
- **Data Insertion**: Batch insertion of validated coffee bean data with conflict resolution
- **Search Operations**: Full-text search with filters for origin, roaster, price range, roast level
- **Analytics Queries**: Aggregation queries for statistics, trends, and reporting
- **Data Migrations**: Schema versioning and migration scripts
- **Export Functions**: Data export to CSV, Parquet, and JSON formats

Use DuckDB's columnar storage advantages for analytical queries. Implement proper indexing for frequently queried fields like roaster, origin, and price.

### 4. CLI Interface

Command-line interface using Typer with Rich for enhanced output:

- **Scraping Commands**: `scrape`, `scrape-all`, `scrape-roaster`
- **Data Management**: `import`, `export`, `clean`, `validate`
- **Database Operations**: `init-db`, `migrate`, `stats`
- **Roaster Management**: `list-roasters`, `add-roaster`, `test-roaster`
- **Development Tools**: `dev-server`, `test-scraper`

Use Rich for colorized output, progress bars, tables, and interactive prompts. Implement comprehensive help text and command validation.

## Development Guidelines

### Code Style & Quality

- Use **ruff** for linting and formatting
- Follow **PEP 8** naming conventions

### Testing Strategy

#### Backend Tests (`tests/`)

```
tests/
├── unit/                  # Unit tests
│   ├── test_scrapers.py   # Scraper unit tests
│   ├── test_schemas.py    # Pydantic model tests
│   └── test_database.py   # Database operation tests
├── integration/           # Integration tests
│   ├── test_api.py        # API endpoint tests
│   └── test_cli.py        # CLI command tests
└── fixtures/              # Test data and fixtures
```

#### Frontend Tests

```
frontend/
├── src/
│   └── __tests__/         # Component and unit tests
└── tests/                 # E2E tests with Playwright
```

### Data Management

#### Scraped Data Structure

```
data/
├── <roaster_name>/
│   └── <timestamp>/       # ISO format: 2024-01-15T10-30-00
│       ├── <bean_name>.json
│       └── <bean_name>.json
│       └── <bean_name>.json
└── processed/             # DuckDB files and aggregated data
    ├── kissaten.duckdb    # Main database
    └── exports/           # Data exports (CSV, Parquet)
```

#### Data Processing Pipeline

1. **Scraping**: Raw data extraction → `data/<roaster>/<timestamp>/raw_data.json`
2. **Validation**: Pydantic validation → `data/<roaster>/<timestamp>/processed.json`
3. **Storage**: DuckDB insertion → `data/processed/kissaten.duckdb`
4. **API**: FastAPI serves processed data to frontend

### API Design

#### RESTful Endpoints

Core API endpoints should include:

- **GET /api/v1/roasters**: List all roasters with metadata
- **GET /api/v1/roasters/{name}/beans**: Get beans from specific roaster
- **GET /api/v1/search**: Advanced search with faceted filtering
- **GET /api/v1/stats**: Database statistics and analytics
- **GET /api/v1/origins**: List all coffee origins
- **GET /api/v1/health**: Health check endpoint

Implement proper HTTP status codes, error handling, request validation, response serialization, and OpenAPI documentation generation.

### Frontend Development

#### SvelteKit Routes

```
frontend/src/routes/
├── +layout.svelte         # Main layout
├── +page.svelte           # Home page
├── search/
│   └── +page.svelte       # Search page
├── beans/
│   └── [id]/
│       └── +page.svelte   # Individual bean page
└── roasters/
    └── +page.svelte       # Roasters listing
```

#### Component Structure

```
frontend/src/lib/
├── components/
│   ├── CoffeeBeanCard.svelte  # Coffee bean card component
│   ├── SearchForm.svelte  # Search form
│   └── FilterPanel.svelte # Filter sidebar
├── stores/                # Svelte stores for state management
└── utils/                 # Utility functions and API calls
```

## Environment Setup

### Development Dependencies

Key development dependencies should include:

- **Code Quality**: ruff
- **Testing**: pytest, pytest-asyncio, pytest-mock, coverage
- **Web Framework**: fastapi[all], uvicorn, httpx
- **Database**: duckdb
- **Scraping**: playwright, beautifulsoup4, lxml
- **CLI**: typer, rich
- **Data**: pydantic, duckdb, polars (for data analysis)
- **Development**: pre-commit, tox

### Environment Variables

Required environment variables:

- **DATABASE_URL**: Path to DuckDB database file
- **API_HOST**: API server host address
- **API_PORT**: API server port
- **LOG_LEVEL**: Logging level (DEBUG, INFO, WARNING, ERROR)
- **DATA_DIR**: Directory for scraped data storage
- **SCRAPING_DELAY**: Default delay between scraping requests
- **MAX_CONCURRENT_SCRAPERS**: Maximum concurrent scraping tasks

## Common Tasks for AI Assistants

### When Adding New Scrapers

Remember to avoid hardcoding any coffee bean values in the scrapers so that scraped data can be future-proof for new types of beans, origins, etc. Extract values from the HTML using BeautifulSoup4. Check that extracted values are not empty and test for scraping blocks or errors.

1. Create scraper in `src/kissaten/scrapers/<roaster_name>.py`
2. Inherit from `BaseScraper`
3. Implement async `scrape()` method
4. Return list of validated `CoffeeBean` objects
5. Add tests in `tests/unit/test_scrapers.py`
6. Update roaster registry in `src/kissaten/scrapers/scrapers.py`

### When Modifying Schemas

1. Update Pydantic models in `src/kissaten/schemas/`
2. Run database migrations if needed
3. Update API documentation
4. Update frontend TypeScript types
5. Add/update tests

### When Adding API Endpoints

1. Add endpoint to `src/kissaten/api/`
2. Use Pydantic models for request/response
3. Add comprehensive docstrings
4. Add integration tests
5. Update frontend API client

### When Working with Data

1. Always validate data with Pydantic schemas
2. Use DuckDB for efficient querying
3. Store raw data in timestamped folders
4. Process data before database insertion
5. Add appropriate indexes for performance

## Performance Considerations

- Use async/await for all I/O operations
- Implement connection pooling for database operations
- Use DuckDB's columnar storage for analytics
- Implement caching for frequently accessed data
- Optimize scraping with rate limiting and concurrent requests

## Security Guidelines

- Validate all input data with Pydantic v2. Do not use Pydantic v1 validators.
- Implement rate limiting for API endpoints
- Use HTTPS in production
- Sanitize scraped data before storage
- Implement proper error handling and logging

## Deployment

### Backend Deployment

- Use Docker containers
- Deploy with uvicorn/gunicorn
- Use environment variables for configuration
- Implement health checks

### Frontend Deployment

- Build with SvelteKit adapter
- Deploy to Vercel/Netlify or similar
- Configure API endpoints for production

This document should be updated as the project evolves and new patterns emerge.
