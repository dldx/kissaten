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
async def test_shopify_scraper_escalates_quickly_on_429(scraper, mocker):
    """After the ladder fix, the first 429 escalates to Playwright
    immediately (5s backoff). The old ladder did ``max_retries`` httpx
    attempts with 5/10/20s backoff before any escalation.
    """
    import httpx

    attempts = 0

    def mock_response(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(429, text="Too Many Requests")

    transport = httpx.MockTransport(mock_response)
    scraper.client = httpx.AsyncClient(transport=transport)
    scraper.max_retries = 3

    mocker.patch("asyncio.sleep")
    mocker.patch.object(
        scraper,
        "_fetch_with_playwright",
        return_value='<html><body><pre>{"products":[]}</pre></body></html>',
    )

    products = await scraper._fetch_all_shopify_products("https://proper-roaster.com/products.json")

    assert products == []
    # Only 1 httpx attempt before escalation. Old ladder did 1 + max_retries = 4.
    assert attempts == 1


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


class TestShopify429Escalation:
    """Regression tests for the 429→Playwright escalation ladder in
    ``ShopifyJsonScraper._fetch_all_shopify_products``.

    Tracked bugs (see ``openwiki/operations/playwright-escalation-investigation-2026-07.md``):
      1. Wasteful retries: do all ``max_retries`` httpx attempts with 5/10/20s
         backoff before escalating.
      2. Single Playwright attempt, no retry inside Playwright.
      3. Fall-through to ``response.raise_for_status()`` with ``response``
         unbound when the Playwright branch sets ``data``.
      4. Instance-level ``_force_playwright`` flag never resets, so a recovered
         host stays stuck on Playwright for every subsequent page.
    """

    @pytest.fixture
    def esc_scraper(self):
        return MockShopifyScraper()

    @staticmethod
    def _shopify_html(payload: dict) -> str:
        """Render a tiny HTML page whose body contains ``<pre>{json}</pre>``,
        matching the form the production code parses out of Playwright output."""
        import json as _json

        return f"<html><body><pre>{_json.dumps(payload)}</pre></body></html>"

    @staticmethod
    def _products_payload(n: int = 1) -> dict:
        return {
            "products": [
                {
                    "id": i,
                    "title": f"Bean {i}",
                    "handle": f"bean-{i}",
                    "body_html": "<p>x</p>",
                    "variants": [{"option1": "250g", "price": "10.00", "available": True}],
                }
                for i in range(n)
            ]
        }

    @pytest.mark.asyncio
    async def test_escalates_on_first_429(self, esc_scraper, mocker):
        """Bug 1: ladder should escalate after a single httpx 429, not after
        ``max_retries`` httpx attempts."""
        import httpx

        attempts = 0

        def mock_response(request):
            nonlocal attempts
            attempts += 1
            return httpx.Response(429, text="local_rate_limited")

        transport = httpx.MockTransport(mock_response)
        esc_scraper.client = httpx.AsyncClient(transport=transport)
        esc_scraper.max_retries = 3

        sleep_mock = mocker.patch("asyncio.sleep")
        mocker.patch.object(
            esc_scraper,
            "_fetch_with_playwright",
            return_value=self._shopify_html(self._products_payload(1)),
        )

        products = await esc_scraper._fetch_all_shopify_products("https://proper-roaster.com/products.json")

        # Only 1 httpx attempt should have happened (the initial 429). The
        # 3 extra httpx attempts on the old ladder are what we're removing.
        assert attempts == 1
        assert len(products) == 1
        # Total backoff: 5s (httpx escalation) + 5s/10s (Playwright retries
        # beyond first attempt). Old ladder would have done 5+10+20=35s on
        # httpx alone.
        total_sleep = sum(call.args[0] for call in sleep_mock.call_args_list)
        assert total_sleep <= 15.0, f"expected ≤15s total backoff, got {total_sleep}s"

    @pytest.mark.asyncio
    async def test_playwright_success_on_escalation_is_not_discarded(self, esc_scraper, mocker):
        """Bug 3 (real form): when httpx returns 429 four times, the
        escalation path calls Playwright and parses ``data`` from it — but
        control then falls through to ``response.raise_for_status()`` with
        ``response`` still pointing at the 429 response from the last httpx
        attempt. That raises HTTPError and discards the successful Playwright
        parse. ``_fetch_all_shopify_products`` returns ``[]`` and records the
        listing as failed even though Playwright just succeeded.
        """
        import httpx

        transport = httpx.MockTransport(lambda req: httpx.Response(429, text="blocked"))
        esc_scraper.client = httpx.AsyncClient(transport=transport)
        esc_scraper.max_retries = 3

        mocker.patch("asyncio.sleep")

        payload = self._products_payload(2)
        pw_mock = mocker.patch.object(esc_scraper, "_fetch_with_playwright", return_value=self._shopify_html(payload))

        products = await esc_scraper._fetch_all_shopify_products("https://proper-roaster.com/products.json")

        # Playwright returned valid JSON; the function must surface it.
        # On the buggy code, products is [] and the listing is recorded as
        # failed because response.raise_for_status() throws on the leftover 429.
        assert pw_mock.call_count == 1
        assert len(products) == 2
        assert products[0]["handle"] == "bean-0"
        assert products[1]["handle"] == "bean-1"
        assert esc_scraper._failed_listing_urls == []

    @pytest.mark.asyncio
    async def test_subsequent_page_with_force_playwright_uses_pw(self, esc_scraper, mocker):
        """Sanity check: pre-set ``_force_playwright = True`` is ignored by
        the new per-page ladder (each page re-attempts httpx first)."""
        import httpx

        # Pre-setting the flag must NOT cause the new code to skip httpx.
        # httpx is mocked to return 200 directly so we can confirm it gets
        # called and Playwright is not.
        transport = httpx.MockTransport(lambda req: httpx.Response(200, json=self._products_payload(1)))
        esc_scraper.client = httpx.AsyncClient(transport=transport)
        esc_scraper._force_playwright = True

        pw_mock = mocker.patch.object(esc_scraper, "_fetch_with_playwright", return_value=self._shopify_html({}))
        mocker.patch("asyncio.sleep")

        products = await esc_scraper._fetch_all_shopify_products("https://proper-roaster.com/products.json")

        # httpx served the page; Playwright was not invoked.
        assert pw_mock.call_count == 0
        assert len(products) == 1

    @pytest.mark.asyncio
    async def test_retries_inside_playwright(self, esc_scraper, mocker):
        """Bug 2: when the Playwright attempt itself fails, retry up to
        ``max_retries`` times with backoff before giving up."""
        import httpx

        # httpx returns 429 to force escalation
        transport = httpx.MockTransport(lambda req: httpx.Response(429, text="blocked"))
        esc_scraper.client = httpx.AsyncClient(transport=transport)
        esc_scraper.max_retries = 2

        mocker.patch("asyncio.sleep")

        # First two Playwright calls raise, third succeeds
        payload = self._products_payload(1)
        pw_mock = mocker.patch.object(
            esc_scraper,
            "_fetch_with_playwright",
            side_effect=[
                Exception("transient 1"),
                Exception("transient 2"),
                self._shopify_html(payload),
            ],
        )

        products = await esc_scraper._fetch_all_shopify_products("https://proper-roaster.com/products.json")

        assert len(products) == 1
        assert pw_mock.call_count == 3

    @pytest.mark.asyncio
    async def test_resets_force_playwright_after_pw_success(self, esc_scraper, mocker):
        """Bug 4: after Playwright succeeds on page 1, page 2 should
        re-attempt httpx instead of being permanently pinned to Playwright."""
        from urllib.parse import parse_qs, urlparse

        import httpx

        httpx_attempts = 0

        def mock_response(request):
            nonlocal httpx_attempts
            httpx_attempts += 1
            page = int(parse_qs(urlparse(str(request.url)).query).get("page", ["1"])[0])
            if page == 1:
                # Page 1: 429 → triggers escalation to Playwright.
                return httpx.Response(429, text="blocked")
            # Page 2: healthy, short page (< limit) so pagination terminates.
            return httpx.Response(200, json=self._products_payload(1))

        transport = httpx.MockTransport(mock_response)
        esc_scraper.client = httpx.AsyncClient(transport=transport)
        esc_scraper.max_retries = 2

        mocker.patch("asyncio.sleep")

        # Page 1 Playwright returns a full page (250 == limit) so the loop
        # proceeds to page 2.
        pw_mock = mocker.patch.object(
            esc_scraper,
            "_fetch_with_playwright",
            return_value=self._shopify_html(self._products_payload(250)),
        )

        products = await esc_scraper._fetch_all_shopify_products("https://proper-roaster.com/products.json")

        # Page 1: 1 httpx (429) + 1 Playwright (200, 250 products).
        # Page 2: 1 httpx (200, 1 product < limit → break).
        # Old ladder would have pinned to Playwright for page 2 → 1 httpx,
        # 2 Playwright calls. New ladder: 2 httpx, 1 Playwright.
        assert httpx_attempts == 2
        assert pw_mock.call_count == 1
        assert len(products) == 251


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
