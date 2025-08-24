# Adding New Coffee Roaster Scrapers

This guide explains how to add new scrapers to the Kissaten project using the registry system.

## Quick Start

1. **Copy the template**: Start with `src/kissaten/scrapers/template.py`
2. **Rename the file**: `cp template.py new_roaster_name.py`
3. **Update the registration**: Modify the `@register_scraper` decorator
4. **Implement extraction**: Update the parsing logic for the specific roaster
5. **Test the scraper**: Use `kissaten test-scraper new-roaster-name`

## Detailed Steps

### 1. Create the Scraper File

```bash
cd src/kissaten/scrapers/
cp template.py my_roaster.py
```

### 2. Update the Registration Decorator

```python
@register_scraper(
    name="my-roaster",                    # CLI name (lowercase, hyphens)
    display_name="My Coffee Roaster",     # Human-readable name
    roaster_name="My Coffee Roaster Ltd", # Official company name
    website="mycoffee.com",               # Website domain
    description="Specialty coffee from My City",
    requires_api_key=False,               # True if using AI extraction
    currency="EUR",                       # Default currency
    country="Germany",                    # Country
    status="available"                    # available, experimental, deprecated
)
```

### 3. Update the Class

```python
class MyRoasterScraper(BaseScraper):
    """Scraper for My Coffee Roaster."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            roaster_name="My Coffee Roaster Ltd",
            base_url="https://mycoffee.com",
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0
        )
        # Add AI extractor if needed
```

### 4. Implement Store URLs

```python
def get_store_urls(self) -> List[str]:
    return [
        "https://mycoffee.com/collections/coffee",
        "https://mycoffee.com/shop/beans",
        # Add all relevant collection pages
    ]
```

### 5. Implement Product URL Extraction

Update `_extract_product_urls()` with the actual CSS selectors:

```python
async def _extract_product_urls(self, soup: BeautifulSoup) -> List[str]:
    product_urls = []

    # Find product links - update these selectors!
    product_links = soup.find_all('a', class_='product-item-link')

    for link in product_links:
        href = link.get('href')
        if href:
            product_url = self.resolve_url(href)
            if self._is_coffee_product_url(product_url):
                product_urls.append(product_url)

    return list(set(product_urls))  # Remove duplicates
```

### 6. Choose Extraction Method

#### Option A: AI-Powered Extraction (Recommended)

Set `requires_api_key=True` in the decorator and rely on the AI extractor:

```python
async def _extract_with_ai(self, soup: BeautifulSoup, product_url: str) -> Optional[CoffeeBean]:
    html_content = str(soup)
    bean = await self.ai_extractor.extract_with_fallback(html_content, product_url)

    if bean:
        # Ensure correct roaster details
        bean.roaster = "My Coffee Roaster Ltd"
        bean.currency = "EUR"
        return bean

    return None
```

#### Option B: Traditional CSS Parsing

Update `_extract_traditional()` with actual selectors:

```python
async def _extract_traditional(self, soup: BeautifulSoup, product_url: str) -> Optional[CoffeeBean]:
    # Extract name (required)
    name_elem = soup.find('h1', class_='product-title')
    name = self.clean_text(name_elem.get_text()) if name_elem else None

    # Extract price
    price_elem = soup.find('span', class_='price-current')
    price = self.extract_price(price_elem.get_text()) if price_elem else None

    # Extract other fields...

    return CoffeeBean(
        name=name,
        roaster="My Coffee Roaster Ltd",
        url=product_url,
        price=price,
        currency="EUR",
        # ... other fields
    )
```

### 7. Update Product Filtering

Customize the exclusion patterns for this roaster:

```python
def _is_coffee_product_url(self, url: str) -> bool:
    """Filter out non-coffee products."""
    excluded = ['equipment', 'merch', 'gift-card', 'subscription']
    return not any(pattern in url.lower() for pattern in excluded)

def _is_coffee_product(self, name: str) -> bool:
    """Filter out non-coffee products by name."""
    excluded = ['mug', 'grinder', 'filter', 'book']
    return not any(pattern in name.lower() for pattern in excluded)
```

### 8. Register the Scraper

Add import to `src/kissaten/scrapers/__init__.py`:

```python
from .my_roaster import MyRoasterScraper

__all__ = [
    "BaseScraper",
    "CartwheelCoffeeScraper",
    "MyRoasterScraper",  # Add this line
    "ScraperRegistry",
    "get_registry",
    "register_scraper",
]
```

### 9. Test the Scraper

```bash
# List all scrapers (should show your new one)
uv run kissaten list-scrapers

# Get info about your scraper
uv run kissaten scraper-info my-roaster

# Test connection
uv run kissaten test-scraper my-roaster

# Run the scraper
uv run kissaten scrape my-roaster
```

## Common Patterns

### Finding Product Links

Different sites use different patterns:

```python
# Shopify stores
product_links = soup.find_all('a', href=lambda x: x and '/products/' in x)

# WooCommerce stores
product_links = soup.find_all('a', class_='woocommerce-LoopProduct-link')

# Custom stores - inspect the HTML
product_links = soup.find_all('a', class_='product-link')
```

### Extracting Tasting Notes

Common patterns for flavor descriptions:

```python
# Comma-separated: "Chocolate, Orange, Vanilla"
if ',' in notes_text:
    tasting_notes = [note.strip() for note in notes_text.split(',')]

# Slash-separated: "Chocolate / Orange / Vanilla"
elif '/' in notes_text:
    tasting_notes = [note.strip() for note in notes_text.split('/')]

# Bullet points or line breaks
elif '\n' in notes_text:
    tasting_notes = [note.strip() for note in notes_text.split('\n') if note.strip()]
```

### Handling Multiple Weights/Prices

```python
# Find the standard weight option (usually 250g or 12oz)
weight_options = soup.find_all('option', value=lambda x: x and '250' in x)
if weight_options:
    price_elem = weight_options[0].find_next('span', class_='price')
    price = self.extract_price(price_elem.get_text())
```

## Best Practices

1. **Be respectful**: Use appropriate rate limiting (`rate_limit_delay`)
2. **Handle errors**: Wrap extraction in try/catch blocks
3. **Validate data**: Check that required fields are present
4. **Filter products**: Exclude non-coffee items early
5. **Test thoroughly**: Test with various product pages
6. **Use AI when possible**: AI extraction is more robust than CSS parsing
7. **Provide fallbacks**: Handle missing or changed selectors gracefully

## Debugging Tips

### Enable Verbose Logging

```bash
uv run kissaten scrape my-roaster --verbose
```

### Inspect HTML Structure

```python
# Add debug prints in your scraper
print("HTML structure:")
print(soup.prettify()[:1000])

# Save sample pages for analysis
with open('debug_page.html', 'w') as f:
    f.write(str(soup))
```

### Test Individual Functions

```python
# Test URL extraction separately
product_urls = await self._extract_product_urls(soup)
print(f"Found {len(product_urls)} URLs: {product_urls[:5]}")
```

## Need Help?

- Check the existing `CartwheelCoffeeScraper` for a working example
- Use AI extraction (`requires_api_key=True`) for complex sites
- The `BaseScraper` class provides helpful utility methods:
  - `clean_text()` - normalize text content
  - `extract_price()` - extract numeric prices
  - `extract_weight()` - convert weights to grams
  - `resolve_url()` - convert relative to absolute URLs

## Adding to Production

1. **Test thoroughly** with the actual website
2. **Check rate limiting** - don't overwhelm the site
3. **Validate output** - ensure data quality
4. **Update documentation** - add to the main README
5. **Consider contributing** - submit a PR to help others!
