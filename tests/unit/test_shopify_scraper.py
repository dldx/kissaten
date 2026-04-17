import pytest
from pathlib import Path
from bs4 import BeautifulSoup
from kissaten.scrapers.shopify_base import ShopifyJsonScraper

class MockShopifyScraper(ShopifyJsonScraper):
    def __init__(self):
        super().__init__(
            roaster_name="Proper Roaster",
            base_url="https://proper-roaster.com",
            products_json_urls=["https://proper-roaster.com/products.json"]
        )

@pytest.fixture
def scraper():
    return MockShopifyScraper()

@pytest.fixture
def mock_products_json():
    return {
        "products": [
            {
                "id": 1,
                "title": "Delicious Coffee",
                "handle": "delicious-coffee-beans",
                "body_html": "<p>Best coffee ever</p>",
                "tags": ["coffee", "ethiopia"],
                "variants": [
                    {"option1": "250g", "price": "15.00", "available": True},
                    {"option1": "1kg", "price": "50.00", "available": False}
                ]
            },
            {
                "id": 2,
                "title": "Sold Out Coffee",
                "handle": "sold-out-coffee-beans",
                "body_html": "<p>Empty bags</p>",
                "variants": [
                    {"option1": "250g", "price": "15.00", "available": False}
                ]
            },
            {
                "id": 3,
                "title": "T-Shirt",
                "handle": "t-shirt",
                "body_html": "Wear this",
                "variants": [
                    {"option1": "Large", "price": "20.00", "available": True}
                ]
            }
        ]
    }

@pytest.mark.asyncio
async def test_extract_product_urls_logic(scraper, mock_products_json, mocker):
    # Mock the _fetch_all_shopify_products to return our test data
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=mock_products_json["products"])

    urls = await scraper._extract_product_urls_from_store("https://proper-roaster.com/products.json")

    # Matches: delicious-coffee-beans, sold-out-coffee-beans. T-shirt should be filtered out.
    assert len(urls) == 2
    assert "https://proper-roaster.com/products/delicious-coffee-beans" in urls
    assert "https://proper-roaster.com/products/sold-out-coffee-beans" in urls

    # Check stock status population
    assert scraper._shopify_stock_status["https://proper-roaster.com/products/delicious-coffee-beans"] is True
    assert scraper._shopify_stock_status["https://proper-roaster.com/products/sold-out-coffee-beans"] is False

def test_format_shopify_context(scraper, mock_products_json):
    product = mock_products_json["products"][0]
    html = scraper._format_shopify_context(product)

    # Verify it contains the script tag with JSON
    assert "<script type=\"application/json\" id=\"shopify-product-json\">" in html
    assert "delicious-coffee-beans" in html
    assert "250g" in html
    assert "15.00" in html

def test_inject_shopify_context(scraper, mock_products_json):
    product = mock_products_json["products"][0]
    soup = BeautifulSoup("<html><body><div id='real-content'>Real</div></body></html>", "lxml")

    modified_soup = scraper._inject_shopify_context(soup, product)

    assert modified_soup.find("div", id="shopify-structured-data") is not None
    assert modified_soup.find("div", id="real-content") is not None
    # Ensure it's at the top of the body
    assert modified_soup.body.contents[0].name == "div"
    assert modified_soup.body.contents[0]["id"] == "shopify-structured-data"

@pytest.mark.asyncio
async def test_scrape_new_products_no_fetch(scraper, mocker):
    # Setup scraper to not fetch pages
    scraper.scrape_product_pages = False
    scraper.ai_extractor = mocker.AsyncMock()

    # Mock _extract_bean_with_ai to return a dummy coffee bean
    from kissaten.schemas import CoffeeBean
    from datetime import datetime
    mock_bean = CoffeeBean(
        name="Test Bean",
        roaster="Proper Roaster",
        url="https://proper-roaster.com/products/test-bean",
        origins=[{"country": "Ethiopia"}],
        price_options=[{"weight": 250, "price": 15.0}],
        scraped_timestamp=datetime.now()
    )

    mocker.patch.object(scraper, "_extract_bean_with_ai", new_callable=mocker.AsyncMock, return_value=mock_bean)
    mocker.patch.object(scraper, "save_bean_with_image", new_callable=mocker.AsyncMock)
    mocker.patch.object(scraper, "fetch_page_with_screenshot", new_callable=mocker.AsyncMock)

    product_urls = ["https://proper-roaster.com/products/test-bean"]

    beans = await scraper._scrape_new_products(product_urls)

    # Verify _extract_bean_with_ai was called
    scraper._extract_bean_with_ai.assert_called_once()

    # Verify the soup passed to _extract_bean_with_ai was "empty" (just basic html/body structure)
    args, kwargs = scraper._extract_bean_with_ai.call_args
    soup = kwargs.get("soup") or args[1]
    assert soup.find("body") is not None
    assert len(soup.find("body").find_all()) == 0  # No elements inside body yet

    # Verify fetch_page_with_screenshot was NOT called since cache_product_pages is False
    scraper.fetch_page_with_screenshot.assert_not_called()
    assert len(beans) == 1

@pytest.mark.asyncio
async def test_scrape_new_products_with_cache(scraper, mocker):
    # Setup scraper to not fetch pages for AI but cache them for docs
    scraper.scrape_product_pages = False
    scraper.cache_product_pages = True
    scraper.ai_extractor = mocker.AsyncMock()

    # Mock _extract_bean_with_ai to return a dummy coffee bean
    from kissaten.schemas import CoffeeBean
    from datetime import datetime
    mock_bean = CoffeeBean(
        name="Test Bean",
        roaster="Proper Roaster",
        url="https://proper-roaster.com/products/test-bean",
        origins=[{"country": "Ethiopia"}],
        price_options=[{"weight": 250, "price": 15.0}],
        scraped_timestamp=datetime.now()
    )

    mocker.patch.object(scraper, "_extract_bean_with_ai", new_callable=mocker.AsyncMock, return_value=mock_bean)
    mocker.patch.object(scraper, "save_bean_with_image", new_callable=mocker.AsyncMock)
    mocker.patch.object(scraper, "fetch_page_with_screenshot", new_callable=mocker.AsyncMock)

    product_urls = ["https://proper-roaster.com/products/test-bean"]

    await scraper._scrape_new_products(product_urls)

    # Verify fetch_page_with_screenshot WAS called because cache_product_pages is True
    scraper.fetch_page_with_screenshot.assert_called_once_with(
        "https://proper-roaster.com/products/test-bean", use_playwright=True
    )
    # Verify _extract_bean_with_ai was still called
    scraper._extract_bean_with_ai.assert_called_once()

