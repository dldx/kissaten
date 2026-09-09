"""Unit tests for the Origin Coffee Roasting scraper.

The primary test runs against a **captured fixture** of the live
``coffee-beans`` collection (7 products on capture), so catalogue drift — a
tea or equipment product leaking in, a URL-format change — fails the test and
is visible as a fixture diff. Regenerate by re-curling
``https://originroasting.co.za/collections/coffee-beans/products.json`` into
``tests/fixtures/origin_roasting_coffee-beans_products.json`` after a site
change.

Covered per-scraper behaviour:
- The curated ``coffee-beans`` collection gate + ``exclude_slugs`` (keeps all
  7 captured products; synthetic entries prove the slug net filters).
- The any-available-variant stock rule (synthetic — the captured catalogue
  happens to have every kept product in stock).
- Store currency pinned to ZAR and ``Accept-Language`` removed, so Shopify
  Markets geo-conversion served to a datacenter IP cannot re-stamp prices.
- Product URLs canonicalised to the no-collection ``/products/<handle>`` form.
- ``preprocess_product_soup`` prunes the page to the ``div.accordion-wrapper``
  block that holds the COFFEE DETAILS spec + narrative accordions (the
  products.json body_html is thin, so this pruning is what keeps page-scrape
  token cost under control).
"""

import json
from pathlib import Path

import pytest

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.origin_roasting import OriginRoastingScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "origin_roasting_coffee-beans_products.json"
PRODUCTS_JSON_URL = "https://originroasting.co.za/collections/coffee-beans/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


def _product(handle: str, title: str, available: bool = True) -> dict:
    return {
        "handle": handle,
        "title": title,
        "product_type": "",
        "variants": [{"price": "300.00", "available": available}],
    }


def _install_fixture(scraper: OriginRoastingScraper) -> None:
    async def fake_fetch(url: str) -> list[dict]:
        return _fixture_products()

    scraper._fetch_all_shopify_products = fake_fetch  # type: ignore[method-assign]


def _make_bean(url: str) -> CoffeeBean:
    return CoffeeBean(name="Maghrib Ans XV", roaster="Origin Coffee Roasting", url=url, origins=[], price_options=[])


@pytest.fixture
def scraper():
    return OriginRoastingScraper()


class TestExtractProductUrlsFromStore:
    """The captured-catalogue gate: curated coffee-beans collection."""

    @pytest.mark.asyncio
    async def test_captured_catalogue_keeps_full_coffee_set(self, scraper):
        _install_fixture(scraper)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        # All 7 captured coffee products are kept: single origins, Yemeni
        # limited reserve, seasonal blend and decaf.
        assert len(urls) == 7
        # Every kept URL is the canonical no-collection form.
        assert all("/collections/" not in u and u.startswith("https://originroasting.co.za/products/") for u in urls)

        # Representative members.
        assert "https://originroasting.co.za/products/maghrib-ans-xv" in urls
        assert "https://originroasting.co.za/products/winter-blend-1" in urls
        assert "https://originroasting.co.za/products/suke-quto-decaf" in urls
        assert "https://originroasting.co.za/products/al-mahjar-peaberry" in urls

    @pytest.mark.asyncio
    async def test_excludes_genuine_non_coffee_slugs(self, scraper, mocker):
        # The captured collection is coffee-only; synthetic entries prove the
        # slug net still filters if the collection is ever broadened.
        products = [
            _product("winter-blend-1", "Winter Blend"),
            _product("origin-gift-card", "Origin Gift Card"),
            _product("chemex-6-cup", "Chemex 6 Cup"),
            _product("green-tea-sakura", "Green Tea - Sakura"),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert urls == ["https://originroasting.co.za/products/winter-blend-1"]

    @pytest.mark.asyncio
    async def test_marks_in_stock_from_any_available_variant(self, scraper, mocker):
        # A product with one sold-out variant but one available variant is in
        # stock; a product with none available is not.
        products = [
            _product("winter-blend-1", "Winter Blend"),
            _product("maghrib-ans-xv", "Maghrib Ans XV", available=False),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert scraper._shopify_stock_status["https://originroasting.co.za/products/winter-blend-1"] is True
        assert scraper._shopify_stock_status["https://originroasting.co.za/products/maghrib-ans-xv"] is False

    def test_preprocess_product_url_strips_collection(self, scraper):
        assert (
            scraper.preprocess_product_url(
                "https://originroasting.co.za/collections/coffee-beans/products/maghrib-ans-xv"
            )
            == "https://originroasting.co.za/products/maghrib-ans-xv"
        )


class TestProductSoupPruning:
    """Page extraction is pruned to the accordion block (token efficiency)."""

    def test_preprocess_soup_keeps_only_accordion_wrapper(self, scraper):
        from bs4 import BeautifulSoup

        html = """
        <html><body>
          <nav>SHOP WHOLESALE BARISTA ACADEMY ABOUT US</nav>
          <div class="newsletter-popup">Sign up and get 10% off</div>
          <div class="accordion-wrapper">
            <div class="accordion-content">
              COFFEE DETAILS Origin: Bani Ofair, Dhamar, Yemen Altitude: 1900-2200 masl
              Body: heavy Acidity: berries, semi dry Roast: light Varietals: Yemenia
            </div>
            <div class="accordion-content x-hidden">About this coffee ...</div>
          </div>
          <div class="you-might-also-like">Winter Blend, Green Tea, Aeropress Filters</div>
          <footer>Sign up for newsletter</footer>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        pruned = scraper.preprocess_product_soup(soup)

        text = pruned.get_text(" ", strip=True)
        assert "COFFEE DETAILS" in text
        assert "Bani Ofair" in text
        # Irrelevant page chrome is gone.
        assert "newsletter" not in text.lower()
        assert "you might also like" not in text.lower()

    def test_preprocess_soup_falls_back_to_full_page(self, scraper):
        from bs4 import BeautifulSoup

        # A page without the accordion block is returned untouched so the
        # injected Shopify JSON context still carries name/price/variants.
        soup = BeautifulSoup("<html><body><p>minimal page</p></body></html>", "lxml")
        pruned = scraper.preprocess_product_soup(soup)
        assert pruned is soup


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
        bean = _make_bean("https://originroasting.co.za/products/maghrib-ans-xv")
        bean.currency = "USD"
        out = scraper.postprocess_extracted_bean(bean)
        assert out.currency == "ZAR"
