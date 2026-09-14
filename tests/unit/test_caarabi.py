"""Unit tests for the Caarabi Coffee Roasters Shopify scraper.

Fully self-contained (no network): products.json responses are stubbed and the
AI extractor is monkeypatched out, mirroring the approach in
``tests/unit/test_shopify_url_canonicalization.py``.
"""

import pytest

# Importing the module registers the scraper with the global registry.
import kissaten.scrapers.caarabi  # noqa: F401
from kissaten.scrapers.registry import get_registry


def _product(handle: str, title: str, available: bool = True, product_type: str = "Coffee") -> dict:
    return {
        "handle": handle,
        "title": title,
        "product_type": product_type,
        "tags": ["Coffee"],
        "variants": [
            {
                "title": "200 gms / Whole Bean",
                "price": "950.00",
                "available": available,
            }
        ],
    }


@pytest.fixture
def scraper(monkeypatch):
    from kissaten import ai as ai_module
    from kissaten.scrapers import caarabi

    # Avoid constructing a real AI extractor (needs an API key + Agent).
    monkeypatch.setattr(ai_module, "CoffeeDataExtractor", lambda api_key=None: None)
    return caarabi.CaarabiCoffeeRoastersScraper()


class TestRegistry:
    def test_registered_with_expected_metadata(self):
        info = get_registry().get_scraper_info("caarabi")
        assert info is not None
        assert info.display_name == "Caarabi Coffee Roasters"
        assert info.roaster_name == "Caarabi Coffee Roasters"
        assert info.currency == "INR"
        assert info.country == "India"
        assert info.website == "https://caarabicoffee.com"

    def test_roaster_name_matches_registry(self, scraper):
        """super().__init__ roaster_name must byte-match @register_scraper."""
        info = get_registry().get_scraper_info("caarabi")
        assert scraper.roaster_name == info.roaster_name == "Caarabi Coffee Roasters"


class TestScraperConfig:
    def test_currency_pinned_to_inr(self, scraper):
        assert scraper.store_currency == "INR"
        assert scraper._currency_detected is True

    def test_json_only_mode(self, scraper):
        """body_html carries all bean details, so no product pages are fetched."""
        assert scraper.scrape_product_pages is False
        assert scraper.use_optimized_mode is True
        assert scraper.cache_product_pages is False

    @pytest.mark.asyncio
    async def test_products_json_url_uses_curated_collection(self, scraper):
        assert scraper.products_json_urls == [
            "https://caarabicoffee.com/collections/shop-coffee-online/products.json"
        ]
        assert await scraper.get_store_urls() == scraper.products_json_urls


class TestUrlCanonicalization:
    def test_collection_prefixed_url_canonicalized(self, scraper):
        url = "https://caarabicoffee.com/collections/shop-coffee-online/products/ratnagiri-washed-aaa"
        assert scraper.preprocess_product_url(url) == "https://caarabicoffee.com/products/ratnagiri-washed-aaa"

    def test_canonicalize_url_collapses_collection(self, scraper):
        assert (
            scraper._canonicalize_url(
                "https://caarabicoffee.com/collections/shop-coffee-online/products/baarbara-washed-aa"
            )
            == "https://caarabicoffee.com/products/baarbara-washed-aa"
        )

    def test_plain_product_url_unchanged(self, scraper):
        url = "https://caarabicoffee.com/products/espresso-sunshine-blend"
        assert scraper.preprocess_product_url(url) == url


class TestExtractProductUrls:
    def _stub_products(self, scraper, products_by_url):
        async def fake_fetch(products_json_url):
            return products_by_url.get(products_json_url, [])

        scraper._fetch_all_shopify_products = fake_fetch

    @pytest.mark.asyncio
    async def test_extracts_canonical_urls_with_metadata(self, scraper):
        self._stub_products(
            scraper,
            {
                scraper.products_json_urls[0]: [
                    _product("ratnagiri-washed-aaa", "Ratnagiri Washed AAA"),
                    _product("kumergode-fruit-ferment", "Kumergode Fruit Ferment"),
                ]
            },
        )

        urls = await scraper._extract_product_urls_from_store(scraper.products_json_urls[0])

        assert urls == [
            "https://caarabicoffee.com/products/ratnagiri-washed-aaa",
            "https://caarabicoffee.com/products/kumergode-fruit-ferment",
        ]
        # Product data + stock status keyed by the canonical URL
        assert set(scraper._shopify_product_data) == set(urls)
        assert set(scraper._shopify_stock_status) == set(urls)
        assert all(scraper._shopify_stock_status[u] for u in urls)

    @pytest.mark.asyncio
    async def test_stock_status_reflects_variant_availability(self, scraper):
        self._stub_products(
            scraper,
            {
                scraper.products_json_urls[0]: [
                    _product("in-stock-bean", "In Stock Bean", available=True),
                    _product("sold-out-bean", "Sold Out Bean", available=False),
                ]
            },
        )

        urls = await scraper._extract_product_urls_from_store(scraper.products_json_urls[0])

        assert scraper._shopify_stock_status["https://caarabicoffee.com/products/in-stock-bean"] is True
        assert scraper._shopify_stock_status["https://caarabicoffee.com/products/sold-out-bean"] is False

    @pytest.mark.asyncio
    async def test_excluded_slugs_are_skipped(self, scraper):
        self._stub_products(
            scraper,
            {
                scraper.products_json_urls[0]: [
                    _product("ratnagiri-washed-aaa", "Ratnagiri Washed AAA"),
                    _product("caarabi-gift-card", "Caarabi Gift Card"),
                    _product("coffee-subscription-monthly", "Monthly Subscription"),
                ]
            },
        )

        urls = await scraper._extract_product_urls_from_store(scraper.products_json_urls[0])

        assert urls == ["https://caarabicoffee.com/products/ratnagiri-washed-aaa"]
        assert "https://caarabicoffee.com/products/caarabi-gift-card" not in scraper._shopify_stock_status

    @pytest.mark.asyncio
    async def test_discover_dedupes_across_collections_via_canonical_url(self, scraper, tmp_path, monkeypatch):
        """The same handle in two collections must yield one canonical URL."""
        product = _product("ratnagiri-washed-aaa", "Ratnagiri Washed AAA")
        self._stub_products(
            scraper,
            {
                "https://caarabicoffee.com/collections/shop-coffee-online/products.json": [product],
                "https://caarabicoffee.com/collections/microlot/products.json": [product],
            },
        )
        scraper.products_json_urls.append("https://caarabicoffee.com/collections/microlot/products.json")
        monkeypatch.chdir(tmp_path)

        urls = await scraper.discover_all_product_urls()

        assert urls == ["https://caarabicoffee.com/products/ratnagiri-washed-aaa"]
