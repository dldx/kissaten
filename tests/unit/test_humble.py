"""Unit tests for the Humble Coffee scraper.

The primary test runs against a **captured fixture** of the live ``coffee``
collection (9 products on capture), so catalogue drift — a catering or pod
product leaking in, a URL-format change — fails the test and is visible as a
fixture diff. Regenerate by re-curling
``https://www.humblecoffee.co.za/collections/coffee/products.json`` into
``tests/fixtures/humble_coffee_products.json`` after a site change.

Covered per-scraper behaviour:
- The curated-collection gate + ``exclude_slugs`` (keeps 8 of 9: single
  origins, blends and a decaf; drops the Nespresso pod box which Shopify
  itself classifies as product_type "Coffee").
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
from kissaten.scrapers.humble import HumbleScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "humble_coffee_products.json"
PRODUCTS_JSON_URL = "https://www.humblecoffee.co.za/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


def _product(handle: str, title: str, product_type: str = "Coffee", available: bool = True) -> dict:
    return {
        "handle": handle,
        "title": title,
        "product_type": product_type,
        "variants": [{"price": "205.00", "available": available}],
    }


def _install_fixture(scraper: HumbleScraper) -> None:
    async def fake_fetch(url: str) -> list[dict]:
        return _fixture_products()

    scraper._fetch_all_shopify_products = fake_fetch  # type: ignore[method-assign]


def _make_bean(url: str) -> CoffeeBean:
    return CoffeeBean(name="LALESA - ETHIOPIA", roaster="Humble Coffee", url=url, origins=[], price_options=[])


@pytest.fixture
def scraper():
    return HumbleScraper()


class TestExtractProductUrlsFromStore:
    """The captured-catalogue gate: curated coffee collection, pods out."""

    @pytest.mark.asyncio
    async def test_captured_catalogue_keeps_coffee_set(self, scraper):
        _install_fixture(scraper)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        # 9 captured products, the Nespresso pod box dropped.
        assert len(urls) == 8
        # Every kept URL is the canonical no-collection form.
        assert all(
            "/collections/" not in u and u.startswith("https://www.humblecoffee.co.za/products/") for u in urls
        )

        # Representative members: single origin, blend, decaf.
        assert "https://www.humblecoffee.co.za/products/lalesa-ethiopia" in urls
        assert "https://www.humblecoffee.co.za/products/humble-house-blend" in urls
        assert "https://www.humblecoffee.co.za/products/el-tucan-decaf-mexico" in urls
        # Pods never leak back in.
        assert not any("pods" in u for u in urls)

    @pytest.mark.asyncio
    async def test_excludes_pods_despite_coffee_product_type(self, scraper, mocker):
        # The pod box carries product_type "Coffee" in the captured catalogue;
        # synthetic entries prove the slug net (and the base name gate) drops
        # the genuine non-bean items.
        products = [
            _product("lalesa-ethiopia", "LALESA - ETHIOPIA"),
            _product("humble-pods-nespresso-compatible", "Humble Pods Nespresso Compatible"),
            _product("humble-gift-card", "Humble Gift Card", product_type=""),
            _product("re-usable-humble-cup", "Re-usable Humble Cup", product_type=""),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert urls == ["https://www.humblecoffee.co.za/products/lalesa-ethiopia"]

    @pytest.mark.asyncio
    async def test_marks_in_stock_from_any_available_variant(self, scraper, mocker):
        # A product with one sold-out variant but one available variant is in
        # stock; a product with none available is not.
        products = [
            _product("lalesa-ethiopia", "LALESA - ETHIOPIA"),
            _product("kinama-hill-burundi", "KINAMA HILL - BURUNDI", available=False),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert scraper._shopify_stock_status["https://www.humblecoffee.co.za/products/lalesa-ethiopia"] is True
        assert scraper._shopify_stock_status["https://www.humblecoffee.co.za/products/kinama-hill-burundi"] is False

    def test_preprocess_product_url_strips_collection(self, scraper):
        assert (
            scraper.preprocess_product_url(
                "https://www.humblecoffee.co.za/collections/coffee/products/lalesa-ethiopia"
            )
            == "https://www.humblecoffee.co.za/products/lalesa-ethiopia"
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
        bean = _make_bean("https://www.humblecoffee.co.za/products/lalesa-ethiopia")
        bean.currency = "USD"
        out = scraper.postprocess_extracted_bean(bean)
        assert out.currency == "ZAR"
