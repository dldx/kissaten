# Kissaten ☕

A coffee bean database and search application that scrapes coffee bean information from roasters worldwide.

## Overview

Kissaten is designed to automatically collect coffee bean data from various roaster websites, storing detailed information about origins, tasting notes, prices, and availability. The project follows a modular architecture that makes it easy to add new roaster scrapers.

## Features

- 🤖 **AI-Powered Extraction**: Uses Gemini 2.5 Flash with PydanticAI for intelligent data extraction
- 🌍 **Multi-roaster support**: Extensible scraper system for different coffee roasters
- 📊 **Rich data extraction**: Captures names, origins, prices, tasting notes, processing methods, and more
- 🔧 **CLI interface**: Easy-to-use command-line tools for scraping and data management
- 📈 **Data validation**: Pydantic v2 schemas ensure data quality and consistency
- 🚀 **Async operations**: High-performance async HTTP requests with rate limiting
- 💾 **Flexible storage**: JSON output with plans for DuckDB analytics
- 🎯 **Hybrid approach**: Combines structural scraping (BS4/Playwright) with AI extraction for best results

## Installation

Install using UV (recommended):

```bash
uv sync
```

Or with pip:

```bash
pip install -e .
```

## Usage

### Command Line Interface

**Setup**: First, configure your Google API key for AI extraction:

1. Copy the example environment file:
```bash
cp env.example .env
```

2. Edit `.env` and add your Google API key:
```bash
GOOGLE_API_KEY=your-gemini-api-key-here
```

Alternatively, you can set the environment variable directly:
```bash
export GOOGLE_API_KEY='your-gemini-api-key-here'
```

List available scrapers:
```bash
uv run kissaten list-scrapers
```

Test a scraper connection:
```bash
uv run kissaten test-scraper cartwheel
```

Scrape coffee beans from Cartwheel Coffee with AI extraction:
```bash
uv run kissaten scrape-cartwheel
```

Or pass the API key directly:
```bash
uv run kissaten scrape-cartwheel --api-key your-key-here
```

View scraped data:
```bash
uv run kissaten show-bean data/cartwheel_coffee/cartwheel_coffee_*.json --index 0
```

### Configuration

Create a `.env` file in the project root:
```bash
cp env.example .env
```

Required environment variables:
- `GOOGLE_API_KEY`: Your Google Gemini API key for AI extraction

### Current Scrapers

| Roaster | Website | Status | Extraction Method | Coffee Beans |
|---------|---------|--------|------------------|--------------|
| Cartwheel Coffee | cartwheelcoffee.com | ✅ Active | 🤖 AI-Powered | ~12 unique beans |

## Architecture

```
kissaten/
├── src/kissaten/
│   ├── schemas/          # Pydantic v2 data models
│   ├── scrapers/         # Roaster-specific scrapers
│   │   ├── base.py       # Abstract base scraper
│   │   └── cartwheel_coffee.py  # AI-powered scraper
│   ├── ai/               # AI-powered extraction
│   │   └── extractor.py  # Gemini + PydanticAI integration
│   ├── cli/              # Command-line interface
│   └── database/         # DuckDB operations (planned)
├── data/                 # Scraped data storage
├── env.example           # Environment variables template
└── tests/                # Test suite (planned)
```

## Data Schema

Each coffee bean includes:

- **Basic Info**: name, roaster, product URL
- **Origin**: country/region of origin
- **Pricing**: price, currency, weight
- **Flavor**: tasting notes, description, roast level
- **Availability**: stock status
- **Metadata**: scraping timestamp, version info

## Hybrid Scraping Approach

Kissaten uses a sophisticated two-stage approach that combines the best of traditional scraping with modern AI:

### Stage 1: Structural Scraping (BS4/Playwright)
- 🔗 **URL Discovery**: Extract product links from index pages using CSS selectors
- 🚀 **Fast & Reliable**: Traditional DOM parsing for navigation and structure
- 🎯 **Precise Targeting**: Identify coffee products vs equipment/accessories
- ⚡ **Efficient**: Minimal API calls, fast execution

### Stage 2: AI-Powered Extraction (Gemini 2.5 Flash)
- 🤖 **Intelligent Understanding**: AI comprehends context and meaning
- 📊 **Rich Data**: Extracts complex information like descriptions, processing methods
- 🌍 **Universal**: Works with any coffee origin, variety, or flavor profile
- 🔧 **Self-Adapting**: No hardcoded lists - adapts to new terms automatically
- 🎯 **Accurate**: Better origin detection, tasting note extraction, and data quality

### Benefits of This Approach
- **Higher Accuracy**: AI understands context better than regex patterns
- **More Maintainable**: No hardcoded lists of origins, flavors, or processing methods
- **Scalable**: Easy to add new roasters without domain-specific knowledge
- **Future-Proof**: Adapts to new coffee terminology and website structures
- **Rich Data**: Extracts narrative descriptions and complex processing information

## Development

### Adding New Scrapers

1. Create a new scraper class inheriting from `BaseScraper`
2. Implement URL extraction using BS4/Playwright
3. Use `CoffeeDataExtractor` for AI-powered data extraction
4. Register in the CLI interface

Example:
```python
from kissaten.scrapers.base import BaseScraper
from kissaten.ai import CoffeeDataExtractor

class NewRoasterScraper(BaseScraper):
    def __init__(self, api_key=None):
        super().__init__(
            roaster_name="New Roaster",
            base_url="https://newroaster.com"
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def scrape(self) -> List[CoffeeBean]:
        # 1. Extract product URLs with BS4
        product_urls = await self._extract_product_urls(index_soup)

        # 2. Use AI to extract data from each product page
        beans = []
        for url in product_urls:
            soup = await self.fetch_page(url)
            bean = await self.ai_extractor.extract_coffee_data(str(soup), url)
            if bean:
                beans.append(bean)
        return beans
```

### Data Quality

The Cartwheel Coffee scraper currently extracts:

- ✅ **Coffee names**: Correctly identified and deduplicated
- ✅ **Prices**: Accurate GBP pricing extraction
- ✅ **Origins**: Major coffee-producing countries detected
- ✅ **Equipment filtering**: Non-coffee products mostly filtered out
- ⚠️ **Tasting notes**: Some formatting issues remain
- ⚠️ **Stock status**: All showing as out of stock (site-specific)

## Example Output

```json
{
  "name": "Bungoma AA",
  "roaster": "Cartwheel Coffee",
  "url": "https://cartwheelcoffee.com/products/bungoma-aa",
  "origin": "Kenya",
  "price": 14.0,
  "currency": "GBP",
  "tasting_notes": ["Blackcurrant", "Gummy Sweets", "Raspberry"],
  "in_stock": false,
  "scraped_at": "2025-08-24T15:47:51.443194"
}
```

## Technology Stack

- **Python 3.10+** with async/await
- **Pydantic v2** for data validation
- **httpx** for async HTTP requests
- **BeautifulSoup4** for HTML parsing
- **Typer + Rich** for CLI interface
- **DuckDB** (planned) for analytics
- **FastAPI** (planned) for web API

## Data Storage

Each roaster has its own scraper in the `src/kissaten/scrapers` directory.
The scraped data is stored in JSON files in the `data` directory, organized as:

```
data/
├── cartwheel_coffee/
│   ├── cartwheel_coffee_20250824_154935.json
│   └── ...
└── <other_roasters>/
```

## Contributing

1. Follow the project structure outlined in `AGENTS.md`
2. Use Pydantic models for all data structures
3. Implement proper error handling and logging
4. Add tests for new scrapers
5. Respect rate limiting and robots.txt

## License

This project is open source. Please scrape responsibly and respect roaster websites' terms of service.

---

**Note**: This is an educational project for learning web scraping and data processing. Always respect website terms of service and implement appropriate rate limiting.