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
    website="https://mycoffee.com",               # Website domain
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

### 6. Choose Extraction Strategy

First, decide which extraction approach is best for your target site:

**Use Standard Mode** for:
- Simple, static HTML sites
- Sites with clean, structured markup
- Cost-sensitive applications
- Most basic coffee shop websites

**Use Optimized Mode** for:
- Complex visual layouts
- JavaScript-heavy sites
- Sites where pricing/info is in images
- Modern, dynamic e-commerce platforms
- Sites similar to AMOC Coffee

| Feature | Standard Mode | Optimized Mode |
|---------|---------------|----------------|
| **Cost** | Lower (tries cheap models first) | Higher (always uses full model) |
| **Speed** | Slower (4 attempts) | Faster (3 attempts) |
| **Success Rate** | Good for simple sites | Better for complex sites |
| **Screenshots** | Only on final attempt | All attempts |
| **Use Case** | Static HTML, simple layouts | Dynamic content, complex layouts |
| **Example** | Basic Shopify store | AMOC Coffee, modern SPAs |

### 7. Implement Efficient Scraping with Diffjson Support

For production scrapers, implement both full scraping and efficient stock updates using the built-in diffjson functionality:

```python
async def scrape(self, force_full_update: bool = False) -> list[CoffeeBean]:
    """Scrape coffee beans with efficient stock updates."""
    self.start_session()
    output_dir = Path("data/roasters/my-roaster") / self.session_id

    # Get all current product URLs
    all_product_urls = []
    for store_url in self.get_store_urls():
        product_urls = await self._extract_product_urls_from_store(store_url)
        all_product_urls.extend(product_urls)

    if force_full_update:
        self.logger.info("Force full update requested - scraping all products")
        return await self._scrape_all_products(all_product_urls)

    # Use built-in diffjson functionality for efficient updates
    in_stock_count, out_of_stock_count = await self.create_diffjson_stock_updates(
        all_product_urls, output_dir.parent, force_full_update
    )

    # Find and scrape only new products
    new_urls = [url for url in all_product_urls if not self._is_bean_already_scraped(url)]

    self.logger.info(f"Stock updates: {in_stock_count} in stock, {out_of_stock_count} out of stock")
    self.logger.info(f"New products to scrape: {len(new_urls)}")

    if new_urls:
        return await self._scrape_new_products(new_urls)

    return []
```

This approach provides:
- **Efficiency**: Only scrapes new products, updates stock for existing ones
- **Completeness**: Force full update option for complete refreshes
- **CLI Integration**: Automatic support for `--force-full-update` flag
- **Logging**: Clear feedback about what the scraper is doing

### 8. Choose Extraction Method

#### Option A: AI-Powered Extraction (Recommended)

Set `requires_api_key=True` in the decorator and rely on the AI extractor.

##### Simple AI Extraction (Default Mode)

For most sites, use the standard progressive fallback approach:

```python
async def _extract_bean_with_ai(self, soup: BeautifulSoup, product_url: str) -> Optional[CoffeeBean]:
    html_content = str(soup)
    # Uses progressive fallback: lite model → full model → full model + screenshot
    bean = await self.ai_extractor.extract_coffee_data(html_content, product_url)

    if bean:
        # Ensure correct roaster details
        bean.roaster = "My Coffee Roaster Ltd"
        bean.currency = "EUR"
        return bean

    return None
```

##### Complex Sites with Screenshot Support

For complex sites with dynamic content or visual layouts, use optimized mode:

```python
async def _extract_bean_with_ai(self, soup: BeautifulSoup, product_url: str, screenshot_bytes: bytes | None = None) -> Optional[CoffeeBean]:
    html_content = str(soup)

    # Use optimized mode for complex pages (always full model + screenshots)
    bean = await self.ai_extractor.extract_coffee_data(
        html_content, product_url, screenshot_bytes, use_optimized_mode=True
    )

    if bean:
        bean.roaster = "My Coffee Roaster Ltd"
        bean.currency = "EUR"
        return bean

    return None
```

And update your product processing to capture screenshots:

```python
# In your product processing method
product_soup, screenshot_bytes = await self.fetch_page_with_screenshot(product_url, use_playwright=True)
bean = await self._extract_bean_with_ai(product_soup, product_url, screenshot_bytes)
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

### 9. Update Product Filtering

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

### 10. Register the Scraper

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

### 11. Test the Scraper

```bash
# List all scrapers (should show your new one)
uv run kissaten list-scrapers

# Get info about your scraper
uv run kissaten scraper-info my-roaster

# Test connection
uv run kissaten test-scraper my-roaster

# Run the scraper (with efficient diffjson updates)
uv run kissaten scrape my-roaster

# Force full update (re-scrapes all products)
uv run kissaten scrape my-roaster --force-full-update
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
8. **Choose extraction mode wisely**: Use optimized mode for complex sites, standard mode for simple sites
9. **Leverage screenshots**: For visual layouts or dynamic content, use `fetch_page_with_screenshot()`
10. **Consider performance**: Standard mode is more cost-effective, optimized mode prioritizes success rate
11. **Implement efficient scraping**: Use built-in diffjson stock updates for production scrapers
12. **Support force full update**: Add `force_full_update` parameter to enable complete re-scraping
13. **Use semantic session IDs**: The base class generates meaningful session IDs automatically

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

# Test screenshot capture
screenshot_bytes = await self.take_screenshot("https://example.com/product/test")
print(f"Screenshot captured: {len(screenshot_bytes) if screenshot_bytes else 0} bytes")

# Test different extraction modes
bean_standard = await self.ai_extractor.extract_coffee_data(html, url, screenshot, use_optimized_mode=False)
bean_optimized = await self.ai_extractor.extract_coffee_data(html, url, screenshot, use_optimized_mode=True)
```

## Diffjson Files for Partial Updates

Scrapers can create `.diffjson` files to make partial updates to existing coffee beans without overwriting all data. This is useful for tracking price changes, stock status, or other fields that change frequently.

### When to Use Diffjson

- **Price monitoring**: Update only price and stock status
- **Incremental scraping**: Update specific fields without re-scraping full product data
- **Data corrections**: Fix specific fields in existing records
- **Tracking changes**: Record when certain fields were last updated

### Built-in Diffjson Support

The `BaseScraper` class now provides built-in methods to handle diffjson stock updates automatically. This makes it easy to implement efficient scrapers that only re-scrape new products while updating stock status for existing ones.

#### Using the Convenience Method

The simplest way to add diffjson support is using the `create_diffjson_stock_updates()` method:

```python
async def scrape(self, force_full_update: bool = False) -> list[CoffeeBean]:
    """Scrape with automatic diffjson stock updates."""
    self.start_session()
    output_dir = Path("data")

    # Get all current product URLs
    all_product_urls = []
    for store_url in self.get_store_urls():
        product_urls = await self._extract_product_urls_from_store(store_url)
        all_product_urls.extend(product_urls)

    if force_full_update:
        # Skip diffjson and scrape everything
        return await self._scrape_all_products(all_product_urls)

    # Create diffjson stock updates for existing products
    in_stock_count, out_of_stock_count = await self.create_diffjson_stock_updates(
        all_product_urls, output_dir, force_full_update
    )

    # Find new products for full scraping
    new_urls = [url for url in all_product_urls if not self._is_bean_already_scraped(url)]

    logger.info(f"Found {in_stock_count} existing products for stock updates")
    logger.info(f"Found {out_of_stock_count} products now out of stock")
    logger.info(f"Found {len(new_urls)} new products for full scraping")

    # Only scrape new products
    if new_urls:
        return await self._scrape_new_products(new_urls)

    return []
```

#### Adding Force Full Update Support

To support the `--force-full-update` CLI option, add a `force_full_update` parameter to your `scrape()` method:

```python
async def scrape(self, force_full_update: bool = False) -> list[CoffeeBean]:
    """Scrape coffee beans with optional force full update.

    Args:
        force_full_update: If True, perform full scraping for all products

    Returns:
        List of CoffeeBean objects
    """
    # Implementation as shown above
```

#### Manual Diffjson Creation

For more control, you can use the individual methods:

```python
# Load existing beans from all previous sessions
self._load_existing_beans_from_all_sessions(output_dir)

# Create stock updates for products still available
existing_urls = [url for url in current_urls if self._is_bean_already_scraped(url)]
await self._create_stock_updates(existing_urls, output_dir)

# Create out-of-stock updates for missing products
await self._create_out_of_stock_updates(current_urls, output_dir)

# Generate filename for custom diffjson files
filename = self._generate_diffjson_filename("https://example.com/product-slug")
```

### Creating Custom Diffjson Files

If you need custom diffjson files beyond the built-in stock updates, you can create them manually.

Diffjson files contain only the fields you want to update, plus the required `url` field to identify the target bean:

```python
import json
from pathlib import Path
from kissaten.schemas import CoffeeBeanDiffUpdate

# Create a diffjson update
update_data = {
    "url": "https://example.com/colombia-coffee",
    "price": 28.50,
    "in_stock": True,
    "scraped_at": "2025-09-11T15:30:00.000000+00:00"
}

# Validate the data
diff_update = CoffeeBeanDiffUpdate.model_validate(update_data)

# Save as .diffjson file
output_dir = Path("data/roasters/my-roaster/20250911")
output_dir.mkdir(parents=True, exist_ok=True)

diffjson_file = output_dir / "colombia_coffee_update.diffjson"
with open(diffjson_file, 'w') as f:
    json.dump(diff_update.model_dump(exclude_none=True), f, indent=2)
```

### Updatable Fields

The `CoffeeBeanDiffUpdate` schema defines which fields can be updated:

- `name` - Coffee bean name
- `roast_level` - Light, Medium, Dark, etc.
- `roast_profile` - Espresso, Filter, Omni
- `price` - Price in local currency
- `weight` - Weight in grams
- `currency` - Currency code
- `is_decaf` - Decaffeinated status
- `cupping_score` - Cupping score (70-100)
- `description` - Product description
- `in_stock` - Stock availability
- `tasting_notes` - List of flavor notes
- `scraped_at` - Timestamp when data was scraped
- `scraper_version` - Version of scraper used

**Note**: Fields like `origins`, `image_url`, and `raw_data` cannot be updated via diffjson and require full JSON files.

### Force Full Update CLI Option

Scrapers that implement diffjson stock updates should also support the `--force-full-update` option to allow users to override the efficient updating and perform a complete scrape of all products.

The CLI automatically detects if a scraper supports this option by checking the method signature:

```python
# This signature enables the --force-full-update option
async def scrape(self, force_full_update: bool = False) -> list[CoffeeBean]:
    if force_full_update:
        logger.info("Force full update requested - skipping diffjson updates")
        # Perform full scraping for all products
    else:
        # Use efficient diffjson updates
```

When users run with `--force-full-update`:
- All products are fully scraped regardless of previous data
- No diffjson files are created
- All product data is refreshed

### Scraper Implementation Example

```python
async def create_price_update(self, product_url: str) -> Optional[Path]:
    """Create a custom diffjson file with only price and stock updates."""

    # Fetch current price and stock status
    soup = await self.fetch_page(product_url)

    price_elem = soup.find('span', class_='price-current')
    price = self.extract_price(price_elem.get_text()) if price_elem else None

    stock_elem = soup.find('div', class_='stock-status')
    in_stock = 'in-stock' in stock_elem.get('class', []) if stock_elem else None

    if price is None and in_stock is None:
        return None

    # Create diffjson update
    update_data = {
        "url": product_url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "scraper_version": "2.0"
    }

    if price is not None:
        update_data["price"] = price
    if in_stock is not None:
        update_data["in_stock"] = in_stock

    # Validate using Pydantic schema
    try:
        diff_update = CoffeeBeanDiffUpdate.model_validate(update_data)
    except Exception as e:
        self.logger.error(f"Invalid diffjson data for {product_url}: {e}")
        return None

    # Save diffjson file using the base method
    filename = self._generate_diffjson_filename(product_url)
    output_path = self.output_dir / filename

    with open(output_path, 'w') as f:
        # Convert HttpUrl to string before JSON serialization
        data_to_save = diff_update.model_dump(exclude_none=True)
        if 'url' in data_to_save and hasattr(data_to_save['url'], '__str__'):
            data_to_save['url'] = str(data_to_save['url'])
        json.dump(data_to_save, f, indent=2)

    self.logger.info(f"Created custom diffjson update: {output_path}")
    return output_path
```

Note: The built-in `create_diffjson_stock_updates()` method handles most common use cases automatically, so custom implementations are only needed for specialized updates.

### Loading Diffjson Updates

The Kissaten API automatically processes diffjson files during data loading:

1. **Discovery**: Finds all `*.diffjson` files in the data directory
2. **Validation**: Uses `CoffeeBeanDiffUpdate` schema to validate each file
3. **Matching**: Matches the `url` field to existing coffee beans
4. **Updating**: Updates only the specified fields in the database
5. **Currency conversion**: Recalculates USD prices if price/currency changed

### Best Practices

1. **Use built-in methods**: The `create_diffjson_stock_updates()` method handles most use cases
2. **Always include `scraped_at`**: Track when the update was made
3. **Validate data**: Use the Pydantic schema to ensure data quality
4. **Use meaningful filenames**: The base class generates appropriate filenames automatically
5. **Update `scraper_version`**: Track which version created the update
6. **Check required fields**: `url` is required to identify the target bean
7. **Handle missing beans**: Diffjson updates are skipped if no matching bean exists
8. **Combine with full scrapes**: Use diffjson for frequent updates, full JSON for complete data
9. **Handle HttpUrl serialization**: Convert Pydantic HttpUrl objects to strings before JSON serialization
10. **Support force full update**: Add `force_full_update` parameter to your `scrape()` method

### Error Handling

```python
# The API will log validation errors and skip invalid files
# Example error: "Skipping update.diffjson: validation failed - price must be positive"

# Your scraper should handle errors gracefully
try:
    diff_update = CoffeeBeanDiffUpdate.model_validate(update_data)
    # Save file...
except ValidationError as e:
    self.logger.warning(f"Skipping invalid update for {product_url}: {e}")
    return None
```

## Advanced Features

### Screenshot-Based Extraction

For sites with complex visual layouts or JavaScript-rendered content:

```python
# Use Playwright to capture both content and screenshot
product_soup, screenshot_bytes = await self.fetch_page_with_screenshot(product_url, use_playwright=True)

# AI can analyze both HTML and visual elements
bean = await self.ai_extractor.extract_coffee_data(
    html_content, product_url, screenshot_bytes, use_optimized_mode=True
)
```

**When to use screenshots:**
- Product pages with image-based pricing
- Complex visual layouts
- JavaScript-heavy sites
- Sites where important info is in graphics/images

### Extraction Mode Selection

**Standard Mode** (default):
- Progressive fallback strategy
- Cost-effective for simple sites
- 4 attempts: lite → lite → full → full+screenshot

**Optimized Mode** (`use_optimized_mode=True`):
- Always uses full model + screenshots
- Best for complex sites like AMOC
- 3 attempts: all full+screenshot
- Higher success rate, higher cost

```python
# Enable optimized mode for complex sites
bean = await self.ai_extractor.extract_coffee_data(
    html_content, product_url, screenshot_bytes, use_optimized_mode=True
)
```

### Playwright Integration

The base scraper provides Playwright support for JavaScript-heavy sites:

```python
# Basic page fetch with Playwright
soup = await self.fetch_page(url, use_playwright=True)

# Page fetch with screenshot capture
soup, screenshot_bytes = await self.fetch_page_with_screenshot(url, use_playwright=True)

# Take standalone screenshot
screenshot_bytes = await self.take_screenshot(url, full_page=True)
```

## Need Help?

- Check the existing `CartwheelCoffeeScraper` for a simple example
- Check the `AmocCoffeeScraper` for a complex example with screenshots
- Use AI extraction (`requires_api_key=True`) for complex sites
- The `BaseScraper` class provides helpful utility methods:
  - `clean_text()` - normalize text content
  - `extract_price()` - extract numeric prices
  - `extract_weight()` - convert weights to grams
  - `resolve_url()` - convert relative to absolute URLs
  - `fetch_page()` - fetch with optional Playwright support
  - `fetch_page_with_screenshot()` - fetch page and capture screenshot
  - `take_screenshot()` - capture screenshot of any URL

## Adding to Production

1. **Test thoroughly** with the actual website
2. **Check rate limiting** - don't overwhelm the site
3. **Validate output** - ensure data quality
4. **Update documentation** - add to the main README
5. **Consider contributing** - submit a PR to help others!
