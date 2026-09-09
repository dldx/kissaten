"""Unit tests for the Espresso Lab Microroasters scraper.

Tests run against a **captured fixture** of the live ``coffee-1`` collection
(19 products on capture, all bean products), so catalogue drift — a sundries
product leaking back in, a URL-format change — fails the test and is visible
as a fixture diff.

Covered per-scraper behaviour:
- The ``exclude_slugs`` safety net (the curated ``coffee-1`` collection is
  bean-only today — the equipment sundries, books and pins live in
  ``collections/all`` — but a drift must still be gated; all 19 captured
  products are kept).
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
from kissaten.scrapers.espresso_lab import EspressoLabScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "espresso-lab_coffee-1_products.json"
PRODUCTS_JSON_URL = "https://espressolabmicroroasters.com/collections/coffee-1/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


def _product(handle: str, title: str, available: bool = True) -> dict:
    return {
        "handle": handle,
        "title": title,
        "product_type": "Coffee",
        "variants": [{"price": "240.00", "available": available}],
    }


def _install_fixture(scraper: EspressoLabScraper) -> None:
    async def fake_fetch(url: str) -> list[dict]:
        return _fixture_products()

    scraper._fetch_all_shopify_products = fake_fetch  # type: ignore[method-assign]


def _make_bean(url: str) -> CoffeeBean:
    return CoffeeBean(
        name="KENYA, Konyu, Kirinyanga", roaster="Espresso Lab Microroasters", url=url, origins=[], price_options=[]
    )


@pytest.fixture
def scraper():
    return EspressoLabScraper()


class TestExtractProductUrlsFromStore:
    """The captured-catalogue gate: coffee-1 is bean-only, sundries net ready."""

    @pytest.mark.asyncio
    async def test_captured_catalogue_keeps_all_coffees(self, scraper):
        _install_fixture(scraper)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        # All 19 captured products are bean coffees and kept.
        assert len(urls) == 19
        # Every kept URL is the canonical no-collection form.
        assert all(
            "/collections/" not in u and u.startswith("https://espressolabmicroroasters.com/products/") for u in urls
        )

        # Representative members: single origins and the rotating house product.
        assert "https://espressolabmicroroasters.com/products/kiamwangi-nyeri-kenya" in urls
        assert "https://espressolabmicroroasters.com/products/los-pirineos-berlin-usulutan-el-salvador" in urls
        assert "https://espressolabmicroroasters.com/products/hello-my-name-is-coffee" in urls

    @pytest.mark.asyncio
    async def test_excludes_sundries_if_they_leak_in(self, scraper, mocker):
        # Synthetic: the sundries (equipment, books, pins, capsules) live in
        # ``collections/all`` today, but a drift into ``coffee-1`` must still
        # be gated by the slug net.
        products = [
            _product("kiamwangi-nyeri-kenya", "KENYA, Konyu, Kirinyanga"),
            _product("sundries-aeropress", "Aeropress"),
            _product("sundries-the-world-atlas-of-coffee-from-beans-to-brewing", "The World Atlas of Coffee"),
            _product("kinu-hand-grinders", "Kinu Hand Grinders"),
            _product("sibarist-filters", "Sibarist Filters"),
            _product("espressolab-pin", "Espresso Lab Pin"),
            _product("capsule-coffee-tadese-wuke-yirgacheffe-ethiopia", "Capsule Coffee"),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert urls == ["https://espressolabmicroroasters.com/products/kiamwangi-nyeri-kenya"]

    @pytest.mark.asyncio
    async def test_marks_in_stock_from_any_available_variant(self, scraper, mocker):
        # A product with one sold-out variant but one available variant is in
        # stock; a product with none available is not.
        products = [
            _product("kiamwangi-nyeri-kenya", "KENYA, Konyu, Kirinyanga"),
            _product("peru-chontali-cajamarca", "PERU, Dreyde Perez Delgado, Chontali, Cajamarca", available=False),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        kenya_url = "https://espressolabmicroroasters.com/products/kiamwangi-nyeri-kenya"
        assert scraper._shopify_stock_status[kenya_url] is True
        assert (
            scraper._shopify_stock_status["https://espressolabmicroroasters.com/products/peru-chontali-cajamarca"]
            is False
        )

    def test_preprocess_product_url_strips_collection(self, scraper):
        assert (
            scraper.preprocess_product_url(
                "https://espressolabmicroroasters.com/collections/coffee-1/products/kiamwangi-nyeri-kenya"
            )
            == "https://espressolabmicroroasters.com/products/kiamwangi-nyeri-kenya"
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
        bean = _make_bean("https://espressolabmicroroasters.com/products/kiamwangi-nyeri-kenya")
        bean.currency = "USD"
        out = scraper.postprocess_extracted_bean(bean)
        assert out.currency == "ZAR"
