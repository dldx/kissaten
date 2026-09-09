"""Unit tests for the Sorcery Coffee Roasters scraper.

Tests run against a **captured fixture** of the live ``collections/all``
endpoint (8 products on capture: 7 bean coffees plus compostable coffee
pods), so catalogue drift — a pods product multiplying, a URL-format change —
fails the test and is visible as a fixture diff.

Covered per-scraper behaviour:
- The ``exclude_slugs`` gate on the captured catalogue (keeps 7 of 8: single
  origins from Colombia, Guatemala and Nicaragua; drops the pods).
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
from kissaten.scrapers.sorcery import SorceryScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "sorcery_all_products.json"
PRODUCTS_JSON_URL = "https://sorcerycoffee.co.za/collections/all/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


def _product(handle: str, title: str, available: bool = True) -> dict:
    return {
        "handle": handle,
        "title": title,
        "product_type": "",
        "variants": [{"price": "390.00", "available": available}],
    }


def _install_fixture(scraper: SorceryScraper) -> None:
    async def fake_fetch(url: str) -> list[dict]:
        return _fixture_products()

    scraper._fetch_all_shopify_products = fake_fetch  # type: ignore[method-assign]


def _make_bean(url: str) -> CoffeeBean:
    return CoffeeBean(
        name="COLOMBIA - MAYPOP", roaster="Sorcery Coffee Roasters", url=url, origins=[], price_options=[]
    )


@pytest.fixture
def scraper():
    return SorceryScraper()


class TestExtractProductUrlsFromStore:
    """The captured-catalogue gate: bean coffees kept, pods out."""

    @pytest.mark.asyncio
    async def test_captured_catalogue_keeps_bean_set(self, scraper):
        _install_fixture(scraper)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        # 8 captured products, the compostable-pods product dropped.
        assert len(urls) == 7
        # Every kept URL is the canonical no-collection form.
        assert all("/collections/" not in u and u.startswith("https://sorcerycoffee.co.za/products/") for u in urls)

        # Representative members: the Colombia range plus other origins.
        assert "https://sorcerycoffee.co.za/products/colombia-maypop" in urls
        assert "https://sorcerycoffee.co.za/products/colombia-el-puente-natural" in urls
        assert "https://sorcerycoffee.co.za/products/guatemala-huehuetenango-washed" in urls
        assert "https://sorcerycoffee.co.za/products/nicaragua-matagalpa" in urls

    @pytest.mark.asyncio
    async def test_drops_compostable_pods(self, scraper):
        _install_fixture(scraper)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert not any("pods" in u for u in urls)
        assert "https://sorcerycoffee.co.za/products/compostable-coffee-pods" not in urls

    @pytest.mark.asyncio
    async def test_marks_in_stock_from_any_available_variant(self, scraper, mocker):
        # A product with one sold-out variant but one available variant is in
        # stock; a product with none available is not.
        products = [
            _product("colombia-maypop", "COLOMBIA - MAYPOP"),
            _product("colombia-tabi-washed", "COLOMBIA - TABI , WASHED", available=False),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert scraper._shopify_stock_status["https://sorcerycoffee.co.za/products/colombia-maypop"] is True
        assert scraper._shopify_stock_status["https://sorcerycoffee.co.za/products/colombia-tabi-washed"] is False

    def test_preprocess_product_url_strips_collection(self, scraper):
        assert (
            scraper.preprocess_product_url(
                "https://sorcerycoffee.co.za/collections/all/products/colombia-maypop"
            )
            == "https://sorcerycoffee.co.za/products/colombia-maypop"
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
        bean = _make_bean("https://sorcerycoffee.co.za/products/colombia-maypop")
        bean.currency = "USD"
        out = scraper.postprocess_extracted_bean(bean)
        assert out.currency == "ZAR"
