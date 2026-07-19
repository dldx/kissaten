import pytest
from bs4 import BeautifulSoup

from kissaten.scrapers.shopify_base import ShopifyJsonScraper


class MockShopifyScraper(ShopifyJsonScraper):
    def __init__(self):
        super().__init__(
            roaster_name="Proper Roaster",
            base_url="https://proper-roaster.com",
            products_json_urls=["https://proper-roaster.com/products.json"],
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
                    {"option1": "1kg", "price": "50.00", "available": False},
                ],
            },
            {
                "id": 2,
                "title": "Sold Out Coffee",
                "handle": "sold-out-coffee-beans",
                "body_html": "<p>Empty bags</p>",
                "variants": [{"option1": "250g", "price": "15.00", "available": False}],
            },
            {
                "id": 3,
                "title": "T-Shirt",
                "handle": "t-shirt",
                "body_html": "Wear this",
                "variants": [{"option1": "Large", "price": "20.00", "available": True}],
            },
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
    assert '<script type="application/json" id="shopify-product-json">' in html
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
    scraper.cache_product_pages = False
    scraper._currency_detected = True  # skip collection-page fetch in test
    scraper.ai_extractor = mocker.AsyncMock()

    # Mock _extract_bean_with_ai to return a dummy coffee bean
    from datetime import datetime

    from kissaten.schemas import CoffeeBean

    mock_bean = CoffeeBean(
        name="Test Bean",
        roaster="Proper Roaster",
        url="https://proper-roaster.com/products/test-bean",
        origins=[{"country": "Ethiopia"}],
        price_options=[{"weight": 250, "price": 15.0}],
        scraped_timestamp=datetime.now(),
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
    scraper._currency_detected = True  # skip collection-page fetch in test
    scraper.ai_extractor = mocker.AsyncMock()

    # Mock _extract_bean_with_ai to return a dummy coffee bean
    from datetime import datetime

    from kissaten.schemas import CoffeeBean

    mock_bean = CoffeeBean(
        name="Test Bean",
        roaster="Proper Roaster",
        url="https://proper-roaster.com/products/test-bean",
        origins=[{"country": "Ethiopia"}],
        price_options=[{"weight": 250, "price": 15.0}],
        scraped_timestamp=datetime.now(),
    )

    mocker.patch.object(scraper, "_extract_bean_with_ai", new_callable=mocker.AsyncMock, return_value=mock_bean)
    mocker.patch.object(scraper, "save_bean_with_image", new_callable=mocker.AsyncMock)
    mocker.patch.object(scraper, "fetch_page_with_screenshot", new_callable=mocker.AsyncMock)

    product_urls = ["https://proper-roaster.com/products/test-bean"]

    await scraper._scrape_new_products(product_urls)

    # Verify fetch_page_with_screenshot WAS called because cache_product_pages is True
    scraper.fetch_page_with_screenshot.assert_any_call(
        "https://proper-roaster.com/products/test-bean", use_playwright=True
    )
    # Verify _extract_bean_with_ai was still called
    scraper._extract_bean_with_ai.assert_called_once()


@pytest.mark.asyncio
async def test_web_bot_auth_injected(scraper, mocker):
    # Set env vars or mock them to verify WebBotAuth is active
    scraper.bot_private_key_pem = "-----BEGIN PRIVATE KEY-----\nMC4CAQAwBQYDK2VwBCIEIP...\n-----END PRIVATE KEY-----"
    scraper.signature_agent_url = "https://kissaten.app"
    scraper.bot_key_id = "test-key-id"

    # Mock get_signed_headers to return a test dictionary
    mock_signed_headers = {
        "Signature-Agent": '"https://kissaten.app"',
        "Signature-Input": "sig2=...",
        "Signature": "sig2=:...:",
    }
    mocker.patch.object(scraper, "get_signed_headers", return_value=mock_signed_headers)

    import httpx

    def handle_request(request):
        # Assert headers have been injected
        assert request.headers["Signature-Agent"] == '"https://kissaten.app"'
        assert request.headers["Signature-Input"] == "sig2=..."
        assert request.headers["Signature"] == "sig2=:...:"
        return httpx.Response(200, json={"success": True})

    scraper.client = httpx.AsyncClient(auth=scraper.client.auth, transport=httpx.MockTransport(handle_request))

    response = await scraper.client.get("https://proper-roaster.com/test-endpoint")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_base_scraper_429_retry_limit(scraper, mocker):
    import httpx

    attempts = 0

    def mock_response(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(429, text="Too Many Requests")

    transport = httpx.MockTransport(mock_response)
    scraper.client = httpx.AsyncClient(transport=transport)
    scraper.max_retries = 2

    # Mock asyncio.sleep so the test runs instantly
    mocker.patch("asyncio.sleep")
    # Mock Playwright to raise exception so it keeps retrying and hits retry limit
    playwright_mock = mocker.patch.object(
        scraper, "_fetch_with_playwright", side_effect=Exception("Playwright failed too")
    )

    # Call fetch_page_with_screenshot which has the retry logic on 429
    soup, screenshot = await scraper.fetch_page_with_screenshot("https://proper-roaster.com/test-429")

    assert soup is None
    assert screenshot is None
    # Only 1 request goes through HTTPX (the initial 429), then 2 retries go through Playwright
    assert attempts == 1
    assert playwright_mock.call_count == 2


@pytest.mark.asyncio
async def test_base_scraper_429_upgrades_to_playwright(scraper, mocker):
    import httpx

    # Mock client to return 429 once, then we fall back to Playwright
    # (Since Playwright is mocked to succeed, we should get the mock page content back)
    def mock_response(request):
        return httpx.Response(429, text="Too Many Requests")

    transport = httpx.MockTransport(mock_response)
    scraper.client = httpx.AsyncClient(transport=transport)
    scraper.max_retries = 2

    mocker.patch("asyncio.sleep")
    mocker.patch.object(
        scraper, "_fetch_with_playwright", return_value="<html><body>Mock Playwright Content</body></html>"
    )
    mocker.patch.object(scraper, "take_screenshot", return_value=b"screenshot")

    soup, screenshot = await scraper.fetch_page_with_screenshot("https://proper-roaster.com/test-playwright-upgrade")

    assert soup is not None
    assert soup.body.text == "Mock Playwright Content"
    assert screenshot == b"screenshot"


@pytest.mark.asyncio
async def test_shopify_scraper_429_retry_limit(scraper, mocker):
    import httpx

    attempts = 0

    def mock_response(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(429, text="Too Many Requests")

    transport = httpx.MockTransport(mock_response)
    scraper.client = httpx.AsyncClient(transport=transport)
    scraper.max_retries = 2

    mocker.patch("asyncio.sleep")

    # Call _fetch_all_shopify_products which has its own retry logic
    products = await scraper._fetch_all_shopify_products("https://proper-roaster.com/products.json")

    assert products == []
    # Initial request (retry=0) + max_retries(2) = 3 attempts total
    assert attempts == 3


@pytest.mark.asyncio
async def test_base_scraper_429_forces_playwright_for_subsequent_requests(scraper, mocker):
    import httpx

    httpx_calls = 0

    def mock_response(request):
        nonlocal httpx_calls
        httpx_calls += 1
        return httpx.Response(429, text="Too Many Requests")

    transport = httpx.MockTransport(mock_response)
    scraper.client = httpx.AsyncClient(transport=transport)
    scraper.max_retries = 2

    mocker.patch("asyncio.sleep")
    playwright_mock = mocker.patch.object(
        scraper, "_fetch_with_playwright", return_value="<html><body>Mock Page</body></html>"
    )
    mocker.patch.object(scraper, "take_screenshot", return_value=b"screenshot")

    # First fetch: will hit 429, set _force_playwright = True, and retry with Playwright
    soup1, _ = await scraper.fetch_page_with_screenshot("https://proper-roaster.com/first-page")
    assert soup1 is not None
    assert scraper._force_playwright is True
    assert httpx_calls == 1
    assert playwright_mock.call_count == 1

    # Second fetch: because _force_playwright is True, it should go straight to Playwright
    # and NOT make any more HTTPX requests!
    soup2, _ = await scraper.fetch_page_with_screenshot("https://proper-roaster.com/second-page")
    assert soup2 is not None
    assert httpx_calls == 1  # Still 1 (no new httpx calls!)
    assert playwright_mock.call_count == 2  # Incremented to 2!


class TestUrlNormalizationDedup:
    """Regression tests for the URL encoding dedup bug.

    Shopify's products.json returns handles with raw non-ASCII characters
    (e.g. Japanese `サマーブレンドコーヒー豆-200ｇ`), but AI extraction stores
    bean URLs in percent-encoded form (e.g.
    `%E3%82%B5%E3%83%9E%E3%83%BC%E3%83%96%E3%83%AC%E3%83%B3%E3%83%89...`).
    The dedup logic must treat these two forms as equivalent so that beans
    scraped once are not re-extracted every session.
    """

    @pytest.fixture
    def dedup_scraper(self):
        return MockShopifyScraper()

    def test_normalize_url_decodes_percent_encoded(self, dedup_scraper):
        encoded = "https://example.com/products/%E3%82%B5%E3%83%9E%E3%83%BC"
        decoded = "https://example.com/products/サマー"
        assert dedup_scraper._normalize_url(encoded) == decoded

    def test_normalize_url_is_idempotent(self, dedup_scraper):
        url = "https://example.com/products/%E3%82%B5%E3%83%9E"
        once = dedup_scraper._normalize_url(url)
        twice = dedup_scraper._normalize_url(once)
        assert once == twice

    def test_normalize_url_preserves_ascii(self, dedup_scraper):
        url = "https://example.com/products/csakura"
        assert dedup_scraper._normalize_url(url) == url

    def test_normalize_url_handles_empty_and_none(self, dedup_scraper):
        assert dedup_scraper._normalize_url("") == ""
        assert dedup_scraper._normalize_url(None) is None

    def test_mark_then_check_with_raw_handle_matches_encoded(self, dedup_scraper, tmp_path):
        """A bean marked with the raw Japanese handle should be recognized
        as already scraped when the same URL comes back percent-encoded
        (the form AI extraction produces from the canonical page URL)."""
        raw_url = "https://shop.example.com/products/サマーブレンドコーヒー豆-200ｇ"
        encoded_url = "https://shop.example.com/products/%E3%82%B5%E3%83%9E%E3%83%BC%E3%83%96%E3%83%AC%E3%83%B3%E3%83%89%E3%82%B3%E3%83%BC%E3%83%92%E3%83%BC%E8%B1%86-200%EF%BD%87"

        # Simulate that we scraped the bean using the encoded form (as AI would save it)
        dedup_scraper._mark_bean_as_scraped(encoded_url)

        # Now the raw handle (as Shopify products.json would return) must be recognized
        assert dedup_scraper._is_bean_already_scraped_anywhere(raw_url)
        assert dedup_scraper._is_bean_already_scraped_historically(raw_url)
        # And symmetrically: marking with raw should match encoded lookup
        dedup_scraper._all_sessions_bean_files.clear()
        dedup_scraper._current_session_bean_files.clear()
        dedup_scraper._mark_bean_as_scraped(raw_url)
        assert dedup_scraper._is_bean_already_scraped_anywhere(encoded_url)

    def test_load_existing_beans_from_all_sessions_normalizes(self, dedup_scraper, tmp_path):
        """A bean JSON file storing the percent-encoded URL form should be
        loaded such that the raw Japanese handle matches in dedup checks."""
        encoded_url = "https://shop.example.com/products/%E3%82%B5%E3%83%9E%E3%83%BC"
        raw_url = "https://shop.example.com/products/サマー"

        # Simulate a previously scraped bean file with the encoded URL
        roaster_dir = tmp_path / "roasters" / "proper_roaster" / "20250101"
        roaster_dir.mkdir(parents=True)
        bean_file = roaster_dir / "test_bean_000001.json"
        bean_file.write_text('{"url": "' + encoded_url + '", "name": "Test"}')

        dedup_scraper._load_existing_beans_from_all_sessions(tmp_path)

        # The loaded set must contain the normalized (decoded) URL
        assert raw_url in dedup_scraper._all_sessions_bean_files
        assert encoded_url not in dedup_scraper._all_sessions_bean_files

        # And the raw handle must be recognized as already scraped
        assert dedup_scraper._is_bean_already_scraped_historically(raw_url)
        assert dedup_scraper._is_bean_already_scraped_historically(encoded_url)
        assert dedup_scraper._is_bean_already_scraped_anywhere(raw_url)
