# ☕ Kissaten - Coffee Bean Discovery Platform

A modern coffee bean database and search application that scrapes coffee bean information from roasters worldwide and provides a beautiful interface to discover and explore specialty coffee.

## 🚀 Features

- **🔍 Unified Search**: Search across coffee beans, roasters, origins, and tasting notes
- **🏭 Browse by Roaster**: Explore beans from specific roasters worldwide
- **🌍 Browse by Country**: Discover beans by their country of origin
- **📊 Analytics**: Statistics and insights about coffee data
- **📱 Responsive Design**: Mobile-friendly interface
- **⚡ Fast Performance**: Built with modern technologies for optimal speed

## 🏗️ Architecture

### Backend (FastAPI + DuckDB + Polars)
- **FastAPI**: Modern, fast web framework for building APIs
- **DuckDB**: High-performance analytical database for efficient querying
- **Polars**: Fast DataFrame library for data processing
- **Pydantic**: Data validation and serialization

### Frontend (SvelteKit + shadcn-svelte)
- **SvelteKit**: Full-stack web framework
- **shadcn-svelte**: Modern, accessible UI components
- **Tailwind CSS**: Utility-first CSS framework
- **TypeScript**: Type-safe JavaScript

### Data Sources
Scraped data from coffee roasters including:
- A.M.O.C.
- Cartwheel Coffee
- Drop Coffee
- Killbean
- People's Possession
- Qima Coffee
- And more...

## 🛠️ Setup Instructions

### Prerequisites
- Python 3.10+
- Bun 1.0+ (recommended) or Node.js 18+
- uv (Python package manager)
- (Optional) HTTP proxy server if scraping from behind a proxy

### Backend Setup

1. **Install Python dependencies**:
```bash
uv sync
```

2. **Configure environment (optional)**:
```bash
# Copy the example environment file
cp env.example .env

# Edit .env and add your API keys and proxy settings (if needed)
```

For proxy configuration, add to your `.env` file:
```bash
# HTTP/HTTPS Proxy (optional)
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=https://proxy.example.com:8443
```

3. **Start the API server**:
```bash
# Using the CLI (recommended)
uv run python -m kissaten.cli.main serve

# Development mode with auto-reload
uv run python -m kissaten.cli.main serve --reload

# Start both API and frontend together
uv run python -m kissaten.cli.main dev --frontend
```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. **Install Bun dependencies**:
```bash
cd frontend
bun install
```

2. **Start the development server**:
```bash
bun run dev
```

The frontend will be available at `http://localhost:5173`

## 📊 Data Processing

The application automatically loads and processes JSON data from the `data/roasters/` directory:

```
data/
├── roasters/
│   ├── a_matter_of_concrete/
│   │   └── 20250824/
│   │       ├── bean1.json
│   │       └── bean2.json
│   ├── cartwheel_coffee/
│   └── ...
```

Data is processed using Polars for efficient handling and stored in DuckDB for fast querying.

## 🔌 API Endpoints

- `GET /api/v1/search` - Search coffee beans with filters
- `GET /api/v1/roasters` - Get all roasters
- `GET /api/v1/roasters/{name}/beans` - Get beans from specific roaster
- `GET /api/v1/countries` - Get coffee origin countries
- `GET /api/v1/stats` - Get database statistics
- `GET /api/v1/beans/{id}` - Get specific coffee bean

## 🖼️ UI Preview

The application features a clean, modern interface with:

- **Home Page**: Hero section with search and quick navigation
- **Search Page**: Advanced filtering with sidebar and grid results
- **Roasters Page**: Browse all coffee roasters with bean counts
- **Countries Page**: Explore beans by country of origin

## 📱 Responsive Design

The interface is fully responsive with:
- Mobile-first design approach
- Collapsible filters on mobile
- Grid layouts that adapt to screen size
- Touch-friendly interactions

## 🧪 Development

### Adding New Scrapers

See `ADDING_SCRAPERS.md` for detailed instructions on adding new coffee roaster scrapers.

### Proxy Configuration

The scrapers support HTTP/HTTPS proxies for environments that require routing traffic through a proxy server. Configure proxies via environment variables in your `.env` file:

```bash
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=https://proxy.example.com:8443
```

Both httpx (for standard HTTP requests) and Playwright (for JavaScript-heavy sites) will use the configured proxy. The scraper prefers `HTTPS_PROXY` when both are set.

### Data Schema

The application uses Pydantic models for data validation:
- `CoffeeBean`: Main coffee bean data model
- `Roaster`: Roaster information model
- `SearchQuery`: Search request model
- `APIResponse`: Standardized API response wrapper

## 🔮 Future Features

- **Semantic Search**: Find similar beans using AI
- **Recommendations**: Personalized coffee recommendations
- **User Accounts**: Save favorite beans and roasters
- **Price Tracking**: Monitor price changes over time
- **Mobile App**: Native mobile applications

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please read the contributing guidelines and feel free to submit pull requests.

## 🙏 Acknowledgments

Thanks to all the specialty coffee roasters who make their bean information publicly available, enabling this project to help coffee enthusiasts discover amazing beans from around the world.