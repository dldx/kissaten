"""Unit tests for the out-of-stock update guards.

Regression tests for the 2026-07-27/28 proxy-outage incident: scrapers whose
listing fetch failed still wrote ``*_out_of_stock.diffjson`` files for every
historically known bean, flipping the whole database out of stock. The guards
tested here suppress out-of-stock updates whenever the listing fetch is
untrustworthy (failed store page, failed products.json, or an empty current
URL list with non-empty history).
"""

import pytest

from kissaten.scrapers._curl_http import RequestError
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.shopify_base import ShopifyJsonScraper

KNOWN_URLS = [
    "https://proper-roaster.com/products/ethiopia-yirgacheffe",
    "https://proper-roaster.com/products/colombia-huila",
    "https://proper-roaster.com/products/kenya-aa",
]


class MockPlainScraper(BaseScraper):
    """Minimal concrete BaseScraper for testing the generic diffjson path."""

    def __init__(self):
        super().__init__(
            roaster_name="Proper Roaster",
            base_url="https://proper-roaster.com",
            rate_limit_delay=0,
        )

    async def get_store_urls(self) -> list[str]:
        return ["https://proper-roaster.com/collections/all"]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        return []


class MockShopifyScraper(ShopifyJsonScraper):
    def __init__(self, **kwargs):
        kwargs.setdefault("rate_limit_delay", 0)
        super().__init__(
            roaster_name="Proper Roaster",
            base_url="https://proper-roaster.com",
            products_json_urls=["https://proper-roaster.com/products.json"],
            **kwargs,
        )


@pytest.fixture
def plain_scraper():
    scraper = MockPlainScraper()
    scraper.start_session()
    scraper._all_sessions_bean_files = set(KNOWN_URLS)
    return scraper


@pytest.fixture
def shopify_scraper():
    scraper = MockShopifyScraper()
    scraper.start_session()
    scraper._all_sessions_bean_files = set(KNOWN_URLS)
    return scraper


def _out_of_stock_files(output_dir):
    return list(output_dir.glob("roasters/**/*_out_of_stock.diffjson"))


def _in_stock_files(output_dir):
    return [
        p
        for p in output_dir.glob("roasters/**/*.diffjson")
        if not p.name.endswith("_out_of_stock.diffjson")
    ]


class TestHardFloor:
    """A2: _create_out_of_stock_updates refuses to wipe the whole catalogue."""

    @pytest.mark.asyncio
    async def test_refuses_empty_current_urls_with_history(self, plain_scraper, tmp_path):
        await plain_scraper._create_out_of_stock_updates([], tmp_path)

        assert _out_of_stock_files(tmp_path) == []
        assert any("Refusing to mark all" in e for e in plain_scraper.session.errors)

    @pytest.mark.asyncio
    async def test_allows_empty_current_urls_without_history(self, plain_scraper, tmp_path):
        plain_scraper._all_sessions_bean_files = set()

        await plain_scraper._create_out_of_stock_updates([], tmp_path)

        assert _out_of_stock_files(tmp_path) == []
        assert plain_scraper.session.errors == []

    @pytest.mark.asyncio
    async def test_marks_missing_products_out_of_stock_normally(self, plain_scraper, tmp_path):
        await plain_scraper._create_out_of_stock_updates(KNOWN_URLS[:2], tmp_path)

        files = _out_of_stock_files(tmp_path)
        assert len(files) == 1
        assert plain_scraper.session.errors == []


class TestBaseScraperGuard:
    """A1: create_diffjson_stock_updates skips out-of-stock updates when a
    listing fetch failed during the session."""

    @pytest.mark.asyncio
    async def test_skips_out_of_stock_when_listing_failed(self, plain_scraper, tmp_path):
        plain_scraper._failed_listing_urls = ["https://proper-roaster.com/collections/all"]

        in_stock, out_of_stock = await plain_scraper.create_diffjson_stock_updates(KNOWN_URLS[:1], tmp_path)

        assert (in_stock, out_of_stock) == (1, 0)
        assert _out_of_stock_files(tmp_path) == []
        # In-stock updates are still written for what was actually seen.
        assert len(_in_stock_files(tmp_path)) == 1
        assert any("Skipped out-of-stock updates" in e for e in plain_scraper.session.errors)

    @pytest.mark.asyncio
    async def test_marks_out_of_stock_without_failures(self, plain_scraper, tmp_path):
        in_stock, out_of_stock = await plain_scraper.create_diffjson_stock_updates(KNOWN_URLS[:1], tmp_path)

        assert (in_stock, out_of_stock) == (1, 2)
        assert len(_out_of_stock_files(tmp_path)) == 2
        assert plain_scraper.session.errors == []

    @pytest.mark.asyncio
    async def test_failed_listing_urls_reset_each_session(self, plain_scraper):
        plain_scraper._failed_listing_urls = ["https://stale.example.com"]

        plain_scraper.start_session()

        assert plain_scraper._failed_listing_urls == []


class TestShopifyGuard:
    """A3: the Shopify override records products.json failures and suppresses
    out-of-stock updates accordingly."""

    @pytest.mark.asyncio
    async def test_skips_out_of_stock_when_products_json_failed(self, shopify_scraper, tmp_path):
        shopify_scraper._failed_listing_urls = ["https://proper-roaster.com/products.json"]
        shopify_scraper._shopify_stock_status = {KNOWN_URLS[0]: True}

        in_stock, out_of_stock = await shopify_scraper.create_diffjson_stock_updates(KNOWN_URLS[:1], tmp_path)

        assert (in_stock, out_of_stock) == (1, 0)
        assert _out_of_stock_files(tmp_path) == []
        assert len(_in_stock_files(tmp_path)) == 1
        assert any("Skipped out-of-stock updates" in e for e in shopify_scraper.session.errors)

    @pytest.mark.asyncio
    async def test_marks_out_of_stock_without_failures(self, shopify_scraper, tmp_path):
        shopify_scraper._shopify_stock_status = {KNOWN_URLS[0]: True, KNOWN_URLS[1]: False}

        in_stock, out_of_stock = await shopify_scraper.create_diffjson_stock_updates(KNOWN_URLS[:2], tmp_path)

        # url0 in stock; url1 (unavailable variant) and url2 (gone from catalog) out of stock
        assert (in_stock, out_of_stock) == (1, 2)
        assert len(_out_of_stock_files(tmp_path)) == 2

    @pytest.mark.asyncio
    async def test_fetch_all_shopify_products_records_failure(self, monkeypatch):
        scraper = MockShopifyScraper(max_retries=1)
        scraper.start_session()

        async def _raise_connect_error(*args, **kwargs):
            raise RequestError("boom")

        monkeypatch.setattr(scraper.client, "get", _raise_connect_error)

        products = await scraper._fetch_all_shopify_products("https://proper-roaster.com/products.json")

        assert products == []
        assert scraper._failed_listing_urls == ["https://proper-roaster.com/products.json"]

    @pytest.mark.asyncio
    async def test_scrape_records_empty_store_page_as_failed(self, shopify_scraper, monkeypatch):
        # A products.json fetch that yields zero products (network failure
        # surfaces as an empty list) must be recorded as a failed listing.
        async def _no_products(*args, **kwargs):
            return []

        monkeypatch.setattr(shopify_scraper, "_fetch_all_shopify_products", _no_products)

        beans = await shopify_scraper.scrape()

        assert beans == []
        assert shopify_scraper._failed_listing_urls == ["https://proper-roaster.com/products.json"]
        assert shopify_scraper.session.beans_found == 0
