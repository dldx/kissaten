"""Unit tests for the Father Coffee scraper.

The primary test runs against a **captured fixture** (trimmed to 11
representative products) of the live ``coffee`` collection (42 products on
capture: microlots, special releases, Rare Release® lots, blends and one
Seasonal Capsules product), so catalogue drift — a capsules entry, a URL-format
change, the duplicate "-copy" handle quirk — fails the test and is visible as
a fixture diff. Regenerate with:

    curl -fsSL "https://www.father.coffee/collections/coffee/products.json?limit=250" \\
      > tests/fixtures/father-coffee_coffee_products.json

Covered per-scraper behaviour:
- The curated ``coffee`` collection gate (keeps beans, drops the Seasonal
  Capsules product via the ``capsules`` exclude slug).
- The any-available-variant stock rule (synthetic).
- Store currency pinned to ZAR and ``Accept-Language`` removed, so Shopify
  Markets geo-conversion served to a datacenter IP cannot re-stamp prices.
- Product URLs keep the collection-prefixed form the live site links with
  (``/collections/coffee/products/<handle>`` — no canonicalization override).
- ``preprocess_product_soup`` prunes the page to the description +
  collapsible-tab blocks (the Product Details accordion carries
  producer/region/variety/altitude/process metafields the JSON lacks).
"""

import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.father_coffee import FatherCoffeeScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "father-coffee_coffee_products.json"
PRODUCTS_JSON_URL = "https://www.father.coffee/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


def _product(handle: str, title: str, available: bool = True) -> dict:
    return {
        "handle": handle,
        "title": title,
        "variants": [{"price": "289.00", "available": available}],
    }


def _install_fixture(scraper: FatherCoffeeScraper) -> None:
    async def fake_fetch(url: str) -> list[dict]:
        return _fixture_products()

    scraper._fetch_all_shopify_products = fake_fetch  # type: ignore[method-assign]


def _make_bean(url: str) -> CoffeeBean:
    return CoffeeBean(name="Karimikui AA, Kirinyaga", roaster="Father Coffee", url=url, origins=[], price_options=[])


@pytest.fixture
def scraper():
    return FatherCoffeeScraper()


class TestExtractProductUrlsFromStore:
    """The captured-catalogue gate: curated coffee collection, capsules out."""

    @pytest.mark.asyncio
    async def test_captured_catalogue_keeps_coffee_drops_capsules(self, scraper):
        _install_fixture(scraper)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        # 11 captured products: the Seasonal Capsules entry is dropped, the
        # 10 beans (microlots, special releases, blends, decaf) are kept.
        assert len(urls) == 10
        # URLs keep the collection-prefixed form the live site links with.
        assert all(u.startswith("https://www.father.coffee/collections/coffee/products/") for u in urls)
        assert not any("capsules" in u for u in urls)

        # Representative members of the live set: microlot, special release,
        # blend and decaf.
        assert "https://www.father.coffee/collections/coffee/products/karimikui-aa" in urls
        assert "https://www.father.coffee/collections/coffee/products/la-llama-coco-natural-geisha-caranavi" in urls
        assert "https://www.father.coffee/collections/coffee/products/heirloom-blend" in urls
        assert "https://www.father.coffee/collections/coffee/products/atunkaa-washed-sugarcane-decaf-cauca" in urls

    @pytest.mark.asyncio
    async def test_marks_in_stock_from_any_available_variant(self, scraper, mocker):
        # A product with one sold-out variant but one available variant is in
        # stock; a product with none available is not.
        products = [
            _product("karimikui-aa", "Karimikui AA, Kirinyaga"),
            _product("heirloom-blend", "Heirloom Blend", available=False),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert scraper._shopify_stock_status[
            "https://www.father.coffee/collections/coffee/products/karimikui-aa"
        ] is True
        assert scraper._shopify_stock_status[
            "https://www.father.coffee/collections/coffee/products/heirloom-blend"
        ] is False


class TestProductPagePruning:
    """The soup pruner keeps the metafield accordion + description, drops chrome."""

    def test_prunes_to_details_blocks(self, scraper):
        html = """
        <html><body>
          <nav><a href="/">Home</a><a href="/collections/brew-gear">Brew Gear</a></nav>
          <div class="product-block-description"><p>Juicy Kenyan AA.</p></div>
          <div class="product-block-collapsible-tab"><details><summary>Product Details</summary>
            <ul class="metafield-single_line_text_field-array">
              <li class="metafield-single_line_text_field">Producer: Rungeto Farmers Cooperative Society</li>
              <li class="metafield-single_line_text_field">Altitude: 1700-1900masl</li>
            </ul>
          </details></div>
          <footer><p>Copyright Father Coffee</p></footer>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")

        pruned = scraper.preprocess_product_soup(soup)

        text = pruned.get_text()
        assert "Rungeto Farmers Cooperative Society" in text
        assert "1700-1900masl" in text
        assert "Juicy Kenyan AA." in text
        # Page chrome is gone.
        assert "Brew Gear" not in text
        assert "Copyright Father Coffee" not in text
        # A valid body is preserved for the Shopify JSON context injection.
        assert pruned.body is not None

    def test_returns_soup_unchanged_when_no_blocks(self, scraper):
        soup = BeautifulSoup("<html><body><p>Fallback page</p></body></html>", "lxml")
        pruned = scraper.preprocess_product_soup(soup)
        assert "Fallback page" in pruned.get_text()


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
        bean = _make_bean("https://www.father.coffee/collections/coffee/products/karimikui-aa")
        bean.currency = "USD"
        out = scraper.postprocess_extracted_bean(bean)
        assert out.currency == "ZAR"
