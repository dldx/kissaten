"""Unit tests for the Cedar Coffee Roasters scraper.

Tests run against a **captured fixture** of the live ``coffee`` collection
(11 products on capture), so catalogue drift — a pods product leaking back
in, a URL-format change — fails the test and is visible as a fixture diff.

Covered per-scraper behaviour:
- The ``exclude_slugs`` gate on the captured collection (keeps 10 of 11:
  single origins, blends and decaf; drops the compostable coffee pods).
- The any-available-variant stock rule.
- Store currency pinned to ZAR and ``Accept-Language`` removed, so Shopify
  Markets geo-conversion served to a datacenter IP cannot re-stamp prices.
- Product URLs canonicalised to the no-collection ``/products/<handle>``
  form used by the live site.
"""

import json
from pathlib import Path

import pytest

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.cedar import CedarScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "cedar_coffee_products.json"
PRODUCTS_JSON_URL = "https://cedarcoffeeroasters.com/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


def _product(handle: str, title: str, available: bool = True) -> dict:
    return {
        "handle": handle,
        "title": title,
        "product_type": "Coffee",
        "variants": [{"price": "189.00", "available": available}],
    }


def _install_fixture(scraper: CedarScraper) -> None:
    async def fake_fetch(url: str) -> list[dict]:
        return _fixture_products()

    scraper._fetch_all_shopify_products = fake_fetch  # type: ignore[method-assign]


def _make_bean(url: str) -> CoffeeBean:
    return CoffeeBean(
        name="Ethiopia Miriga Village Washed", roaster="Cedar Coffee Roasters", url=url, origins=[], price_options=[]
    )


@pytest.fixture
def scraper():
    return CedarScraper()


class TestExtractProductUrlsFromStore:
    """The captured-catalogue gate: curated coffee collection, pods out."""

    @pytest.mark.asyncio
    async def test_captured_catalogue_keeps_bean_set(self, scraper):
        _install_fixture(scraper)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        # 11 captured products, the compostable-pods product dropped.
        assert len(urls) == 10
        # Every kept URL is the canonical no-collection form.
        assert all("/collections/" not in u and u.startswith("https://cedarcoffeeroasters.com/products/") for u in urls)

        # Representative members: single origin, blend and decaf.
        assert "https://cedarcoffeeroasters.com/products/ethiopia-murgo-washed" in urls
        assert "https://cedarcoffeeroasters.com/products/cedar-blend" in urls
        assert "https://cedarcoffeeroasters.com/products/milky-way-seasonal-blend" in urls
        assert "https://cedarcoffeeroasters.com/products/colombia-decaf-1" in urls

    @pytest.mark.asyncio
    async def test_drops_compostable_pods(self, scraper):
        _install_fixture(scraper)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert not any("pods" in u for u in urls)
        assert "https://cedarcoffeeroasters.com/products/cedar-milky-way-compostable-pods" not in urls

    @pytest.mark.asyncio
    async def test_excludes_non_coffee_slugs_if_they_leak_in(self, scraper, mocker):
        # Synthetic: the curated collection is bean-only today, but a future
        # equipment/merch entry must still be gated by the slug net.
        products = [
            _product("ethiopia-murgo-washed", "Ethiopia Miriga Village Washed"),
            _product("moccamaster-kbg-select", "Moccamaster KBG Select"),
            _product("cedar-online-gift-card-1", "Cedar Online Gift Card"),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert urls == ["https://cedarcoffeeroasters.com/products/ethiopia-murgo-washed"]

    @pytest.mark.asyncio
    async def test_marks_in_stock_from_any_available_variant(self, scraper, mocker):
        # A product with one sold-out variant but one available variant is in
        # stock; a product with none available is not.
        products = [
            _product("ethiopia-murgo-washed", "Ethiopia Miriga Village Washed"),
            _product("kenya-thunguri-ab", "Kenya Thunguri AB", available=False),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert scraper._shopify_stock_status["https://cedarcoffeeroasters.com/products/ethiopia-murgo-washed"] is True
        assert scraper._shopify_stock_status["https://cedarcoffeeroasters.com/products/kenya-thunguri-ab"] is False

    def test_preprocess_product_url_strips_collection(self, scraper):
        assert (
            scraper.preprocess_product_url(
                "https://cedarcoffeeroasters.com/collections/coffee/products/cedar-blend"
            )
            == "https://cedarcoffeeroasters.com/products/cedar-blend"
        )


class TestCurrencyPinning:
    """ZAR pinned so geo-converted prices can never be stamped onto beans."""

    def test_currency_detected_is_true_in_init(self, scraper):
        # _currency_detected=True prevents _scrape_new_products from refetching
        # the collection page and letting a presentment currency in.
        assert scraper._currency_detected is True
        assert scraper.store_currency == "ZAR"
        assert "Accept-Language" not in scraper.headers
        assert "Accept-Language" not in scraper.client._base_headers

    def test_geo_converted_page_cannot_override_zar(self, scraper):
        from bs4 import BeautifulSoup

        # Even a page advertising a converted currency must yield ZAR.
        soup = BeautifulSoup('<html><body><meta property="og:price:currency" content="USD"></body></html>', "lxml")
        assert scraper._extract_currency_from_html(soup) == "ZAR"

    def test_postprocess_forces_zar(self, scraper):
        bean = _make_bean("https://cedarcoffeeroasters.com/products/cedar-blend")
        bean.currency = "USD"
        out = scraper.postprocess_extracted_bean(bean)
        assert out.currency == "ZAR"
