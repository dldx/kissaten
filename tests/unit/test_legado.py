"""Unit tests for the Legado scraper.

The primary test runs against a **captured fixture** of the live
``coffee-beans`` collection (7 products on capture, all
``product_type == "Retail Coffee"``), so catalogue drift — a new event package
or merch product leaking in, a URL-format change — fails the test and is
visible as a fixture diff. Regenerate with:

    curl -fsSL "https://legadocoffee.com/collections/coffee-beans/products.json" \\
      > tests/fixtures/legado_coffee-beans_products.json

Covered per-scraper behaviour:
- The curated ``coffee-beans`` collection gate (keeps all 7: single origins
  and blends; the ``exclude_slugs`` net is a defensive guard against the
  event/catering packages that live in the broader ``all`` collection).
- The any-available-variant stock rule (synthetic — the captured catalogue
  happens to have every product in stock).
- Store currency pinned to ZAR and ``Accept-Language`` removed, so Shopify
  Markets geo-conversion served to a datacenter IP cannot re-stamp prices.
- Product URLs keep the collection-prefixed form the live site links with
  (``/collections/coffee-beans/products/<handle>`` — no canonicalization
  override).
"""

import json
from pathlib import Path

import pytest

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.legado import LegadoScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "legado_coffee-beans_products.json"
PRODUCTS_JSON_URL = "https://legadocoffee.com/collections/coffee-beans/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


def _product(handle: str, title: str, product_type: str = "Retail Coffee", available: bool = True) -> dict:
    return {
        "handle": handle,
        "title": title,
        "product_type": product_type,
        "variants": [{"price": "195.00", "available": available}],
    }


def _install_fixture(scraper: LegadoScraper) -> None:
    async def fake_fetch(url: str) -> list[dict]:
        return _fixture_products()

    scraper._fetch_all_shopify_products = fake_fetch  # type: ignore[method-assign]


def _make_bean(url: str) -> CoffeeBean:
    return CoffeeBean(name="Guatemala SHB - Fully Washed", roaster="Legado", url=url, origins=[], price_options=[])


@pytest.fixture
def scraper():
    return LegadoScraper()


class TestExtractProductUrlsFromStore:
    """The captured-catalogue gate: the curated coffee-beans collection."""

    @pytest.mark.asyncio
    async def test_captured_catalogue_keeps_all_coffee(self, scraper):
        _install_fixture(scraper)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        # 7 captured products, all retail coffee (single origins + blends).
        assert len(urls) == 7
        # URLs keep the collection-prefixed form the live site links with.
        assert all(u.startswith("https://legadocoffee.com/collections/coffee-beans/products/") for u in urls)

        # Representative members of the live set: single origins and blends.
        assert "https://legadocoffee.com/collections/coffee-beans/products/brazil-cerrado-natural" in urls
        assert "https://legadocoffee.com/collections/coffee-beans/products/guatemala-el-rincon" in urls
        assert "https://legadocoffee.com/collections/coffee-beans/products/espresso-blend" in urls
        assert "https://legadocoffee.com/collections/coffee-beans/products/journeyman-blend" in urls

    @pytest.mark.asyncio
    async def test_exclude_slugs_drop_events_and_merch(self, scraper, mocker):
        # Synthetic: the broader `all` collection also holds event/catering
        # packages; the defensive exclude_slugs net must drop them.
        products = [
            _product("brazil-cerrado-natural", "Brazil Cerrado - Natural"),
            _product("evening-event-canapes-drinks", "Catered Evening Event"),
            _product("morning-event-venue-only", "Morning Event – Venue Only"),
            _product("legado-gift-card", "Legado Gift Card"),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert urls == ["https://legadocoffee.com/collections/coffee-beans/products/brazil-cerrado-natural"]

    @pytest.mark.asyncio
    async def test_marks_in_stock_from_any_available_variant(self, scraper, mocker):
        # A product with one sold-out variant but one available variant is in
        # stock; a product with none available is not.
        products = [
            _product("brazil-cerrado-natural", "Brazil Cerrado - Natural"),
            _product("rwanda", "Rwanda Dahwe - Natural", available=False),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert scraper._shopify_stock_status[
            "https://legadocoffee.com/collections/coffee-beans/products/brazil-cerrado-natural"
        ] is True
        assert (
            scraper._shopify_stock_status["https://legadocoffee.com/collections/coffee-beans/products/rwanda"] is False
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
        bean = _make_bean("https://legadocoffee.com/collections/coffee-beans/products/guatemala-el-rincon")
        bean.currency = "USD"
        out = scraper.postprocess_extracted_bean(bean)
        assert out.currency == "ZAR"
