"""Unit tests for the Rosetta Roastery scraper.

The primary test runs against a **captured fixture** of the live ``coffee``
collection (15 products on capture), so catalogue drift — a new non-bean
product leaking in, a capsule product returning, a URL-format change — fails
the test and is visible as a fixture diff. Regenerate by re-curling
``https://www.rosettaroastery.com/collections/coffee/products.json`` into
``tests/fixtures/rosetta_coffee_products.json`` after a site change.

Covered per-scraper behaviour:
- The curated-collection gate + ``exclude_slugs`` (keeps 14 of 15: singles,
  blends, decaf, drip sachets and the multi-bag Signature Selection set;
  drops the compostable coffee capsules).
- The any-available-variant stock rule (synthetic — the captured catalogue
  happens to have every kept product in stock).
- Store currency pinned to ZAR and ``Accept-Language`` removed, so Shopify
  Markets geo-conversion served to a datacenter IP cannot re-stamp prices.
- Product URLs canonicalised to the no-collection ``/products/<handle>`` form.
"""

import json
from pathlib import Path

import pytest

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.rosetta import RosettaScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "rosetta_coffee_products.json"
PRODUCTS_JSON_URL = "https://www.rosettaroastery.com/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


def _product(handle: str, title: str, available: bool = True) -> dict:
    return {
        "handle": handle,
        "title": title,
        "product_type": "coffee",
        "variants": [{"price": "300.00", "available": available}],
    }


def _install_fixture(scraper: RosettaScraper) -> None:
    async def fake_fetch(url: str) -> list[dict]:
        return _fixture_products()

    scraper._fetch_all_shopify_products = fake_fetch  # type: ignore[method-assign]


def _make_bean(url: str) -> CoffeeBean:
    return CoffeeBean(name="La Chirimoya, Peru", roaster="Rosetta Roastery", url=url, origins=[], price_options=[])


@pytest.fixture
def scraper():
    return RosettaScraper()


class TestExtractProductUrlsFromStore:
    """The captured-catalogue gate: curated coffee collection, capsules out."""

    @pytest.mark.asyncio
    async def test_captured_catalogue_keeps_coffee_set(self, scraper):
        _install_fixture(scraper)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        # 15 captured products, the compostable coffee capsules dropped.
        assert len(urls) == 14
        # Every kept URL is the canonical no-collection form.
        assert all(
            "/collections/" not in u and u.startswith("https://www.rosettaroastery.com/products/") for u in urls
        )

        # Representative members: single origin, blend set, decaf, drip sachets.
        assert "https://www.rosettaroastery.com/products/la-chirimoya-peru" in urls
        assert "https://www.rosettaroastery.com/products/signature-selection" in urls
        assert "https://www.rosettaroastery.com/products/decaffeinated-shakisso-24-25-ethiopia" in urls
        assert "https://www.rosettaroastery.com/products/drip-sachets-10-pack-mix-box" in urls
        # Capsules never leak back in.
        assert not any("capsules" in u for u in urls)

    @pytest.mark.asyncio
    async def test_excludes_genuine_non_coffee_slugs(self, scraper, mocker):
        products = [
            _product("la-chirimoya-peru", "La Chirimoya, Peru"),
            _product("copy-of-compostable-coffee-capsules", "Compostable Coffee Capsules"),
            _product("rosetta-subscription", "Coffee Subscription"),
            _product("rosetta-gift-card", "Gift Card"),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert urls == ["https://www.rosettaroastery.com/products/la-chirimoya-peru"]

    @pytest.mark.asyncio
    async def test_marks_in_stock_from_any_available_variant(self, scraper, mocker):
        # A product with one sold-out variant but one available variant is in
        # stock; a product with none available is not.
        products = [
            _product("la-chirimoya-peru", "La Chirimoya, Peru"),
            _product("wete-konga-ethiopia", "Wete Konga, Ethiopia", available=False),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert scraper._shopify_stock_status["https://www.rosettaroastery.com/products/la-chirimoya-peru"] is True
        assert scraper._shopify_stock_status["https://www.rosettaroastery.com/products/wete-konga-ethiopia"] is False

    def test_preprocess_product_url_strips_collection(self, scraper):
        assert (
            scraper.preprocess_product_url(
                "https://www.rosettaroastery.com/collections/coffee/products/la-chirimoya-peru"
            )
            == "https://www.rosettaroastery.com/products/la-chirimoya-peru"
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
        bean = _make_bean("https://www.rosettaroastery.com/products/la-chirimoya-peru")
        bean.currency = "USD"
        out = scraper.postprocess_extracted_bean(bean)
        assert out.currency == "ZAR"
