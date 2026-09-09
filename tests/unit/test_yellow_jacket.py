"""Unit tests for the Yellow Jacket Coffee scraper.

The primary test runs against a **captured fixture** of the live ``all``
collection (37 products on capture: ~29 beans/blends/drip packs plus 8 pieces
of equipment), so catalogue drift — a new brew-tool product, a URL-format
change — fails the test and is visible as a fixture diff. Regenerate with:

    curl -fsSL "https://yellowjacketcoffee.co.za/collections/all/products.json?limit=250" \\
      > tests/fixtures/yellow-jacket_all_products.json

Covered per-scraper behaviour:
- The ``all`` collection gate via ``exclude_slugs`` (drops scales, V60s,
  cloths, filter holders and water sachets; keeps the beans, the house blends
  and the Filter Drip Pack, which flows to the review queue if the AI
  extractor recognises it as a tasting kit).
- The any-available-variant stock rule (synthetic).
- Store currency pinned to ZAR and ``Accept-Language`` removed, so Shopify
  Markets geo-conversion served to a datacenter IP cannot re-stamp prices.
- Product URLs are canonicalised to the no-collection ``/products/<handle>``
  form (collection-prefixed URLs 301-redirect there on the live site).
"""

import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.yellow_jacket import YellowJacketScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "yellow-jacket_all_products.json"
PRODUCTS_JSON_URL = "https://yellowjacketcoffee.co.za/collections/all/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


def _product(handle: str, title: str, available: bool = True) -> dict:
    return {
        "handle": handle,
        "title": title,
        "variants": [{"price": "280.00", "available": available}],
    }


def _install_fixture(scraper: YellowJacketScraper) -> None:
    async def fake_fetch(url: str) -> list[dict]:
        return _fixture_products()

    scraper._fetch_all_shopify_products = fake_fetch  # type: ignore[method-assign]


def _make_bean(url: str) -> CoffeeBean:
    return CoffeeBean(
        name="Kenya - Kii AA - Washed", roaster="Yellow Jacket Coffee", url=url, origins=[], price_options=[]
    )


@pytest.fixture
def scraper():
    return YellowJacketScraper()


class TestExtractProductUrlsFromStore:
    """The captured-catalogue gate: exclude_slugs drops equipment, beans stay."""

    @pytest.mark.asyncio
    async def test_captured_catalogue_keeps_coffee_drops_equipment(self, scraper):
        _install_fixture(scraper)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        # 37 captured products: the 7 equipment items are dropped, the 30
        # coffee items (single origins, house blends, 1kg bags, the Filter
        # Drip Pack) are kept.
        assert len(urls) == 30
        # URLs use the canonical no-collection form (matches the live site's
        # 301 redirects).
        assert all(
            "/collections/" not in u and u.startswith("https://yellowjacketcoffee.co.za/products/") for u in urls
        )
        # Genuine equipment never leaks back in.
        assert not any("espresso-scale" in u for u in urls)
        assert not any("filter-holder" in u for u in urls)
        assert not any("v60" in u for u in urls)
        assert not any("third-wave-water" in u for u in urls)
        assert not any("/products/barista" in u for u in urls)

        # Representative members of the live set: single origin, house blend
        # (which no curated sub-collection covers), 1kg bag and the drip pack.
        assert "https://yellowjacketcoffee.co.za/products/kenya-kii-aa-washed" in urls
        assert "https://yellowjacketcoffee.co.za/products/komodo" in urls
        assert "https://yellowjacketcoffee.co.za/products/circus-bear-shop-1" in urls
        assert "https://yellowjacketcoffee.co.za/products/filter-drip-pack-seasonal-coffees-1" in urls

    @pytest.mark.asyncio
    async def test_marks_in_stock_from_any_available_variant(self, scraper, mocker):
        # A product with one sold-out variant but one available variant is in
        # stock; a product with none available is not.
        products = [
            _product("kenya-kii-aa-washed", "Kenya - Kii AA - Washed"),
            _product("komodo", "Komodo", available=False),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert scraper._shopify_stock_status["https://yellowjacketcoffee.co.za/products/kenya-kii-aa-washed"] is True
        assert scraper._shopify_stock_status["https://yellowjacketcoffee.co.za/products/komodo"] is False


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
        # Even a page advertising a converted currency must yield ZAR.
        soup = BeautifulSoup('<html><body><meta property="og:price:currency" content="USD"></body></html>', "lxml")
        assert scraper._extract_currency_from_html(soup) == "ZAR"

    def test_postprocess_forces_zar(self, scraper):
        bean = _make_bean("https://yellowjacketcoffee.co.za/products/kenya-kii-aa-washed")
        bean.currency = "USD"
        out = scraper.postprocess_extracted_bean(bean)
        assert out.currency == "ZAR"
