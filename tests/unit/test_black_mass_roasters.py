"""Unit tests for the Black Mass Roasters scraper.

The primary test runs against a **captured fixture** of the live
``view-all-live-offerings`` collection (24 products on capture, all
``product_type == "Coffee"``), so catalogue drift — a renamed product_type, a
new release, a subscription handle leaking back in, a URL-format change —
fails the test and is visible as a fixture diff. Regenerate with
``.venv/bin/python tests/fixtures/capture.py`` after a site change (see the
fixture module docstring).

Covered per-scraper behaviour:
- The ``product_type == "Coffee"`` + ``exclude_slugs`` gate on the captured
  collection (keeps 18 of 24: singles, blends, decaf, multi-bag bundles;
  drops the 6 "Blend Subscription" handles).
- The any-available-variant stock rule (synthetic — the captured catalogue
  happens to have every kept product in stock).
- Store currency pinned to AUD and ``Accept-Language`` removed, so Shopify
  Markets geo-conversion served to a datacenter IP cannot re-stamp prices.

Not unit-tested here: base-class behaviour already covered by
``test_tasting_kit_flags.py`` and ``test_shopify_url_canonicalization.py`` —
the 2-line URL-regexp mirror and the base ``_apply_product_flags`` helper are
not Black-Mass-specific. The AI extractor's kit detection for the unbranded
bundles cannot be exercised hermetically and is out of scope for unit
tests.
"""

import json
from pathlib import Path

import pytest

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.black_mass_roasters import BlackMassRoastersScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "blackmass_view-all-live-offerings_products.json"
PRODUCTS_JSON_URL = "https://blackmassroasters.com/collections/view-all-live-offerings/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


def _product(handle: str, title: str, product_type: str = "Coffee", available: bool = True) -> dict:
    return {
        "handle": handle,
        "title": title,
        "product_type": product_type,
        "variants": [{"price": "27.00", "available": available}],
    }


def _install_fixture(scraper: BlackMassRoastersScraper) -> None:
    async def fake_fetch(url: str) -> list[dict]:
        return _fixture_products()

    scraper._fetch_all_shopify_products = fake_fetch  # type: ignore[method-assign]


def _make_bean(url: str) -> CoffeeBean:
    return CoffeeBean(
        name="VITRIOLIC HISS, Honduras", roaster="Black Mass Roasters", url=url, origins=[], price_options=[]
    )


@pytest.fixture
def scraper():
    return BlackMassRoastersScraper()


class TestExtractProductUrlsFromStore:
    """The captured-catalogue gate: Coffee type, subscriptions out, bundles in."""

    @pytest.mark.asyncio
    async def test_captured_catalogue_keeps_live_coffee_set(self, scraper):
        _install_fixture(scraper)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        # 24 captured products, 6 "Blend Subscription" handles dropped.
        assert len(urls) == 18
        # Every kept URL is the canonical no-collection form.
        assert all("/collections/" not in u and u.startswith("https://blackmassroasters.com/products/") for u in urls)
        # Subscriptions never leak back in.
        assert not any("subscription" in u for u in urls)

        # Representative members of the live set: single origin, blend, decaf
        # and the multi-bag bundles that flow to the review queue.
        assert "https://blackmassroasters.com/products/vitriolic-hiss-honduras" in urls
        assert "https://blackmassroasters.com/products/cathedral-blend" in urls
        assert "https://blackmassroasters.com/products/spiritual-alchemy-decaf" in urls
        assert "https://blackmassroasters.com/products/roasters-choice-bundle-triune" in urls
        assert "https://blackmassroasters.com/products/trio-blend" in urls

    @pytest.mark.asyncio
    async def test_drops_non_coffee_product_types(self, scraper, mocker):
        # Synthetic: the captured collection is all Coffee-type, but a future
        # collection entry must still be gated on the type before the slug net.
        products = [
            _product("vitriolic-hiss-honduras", "VITRIOLIC HISS, Honduras"),
            _product("3x-tee", "3X Tee", product_type="T-Shirts"),
            _product("chaos-mug", "Chaos Mug", product_type="Accessories"),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert urls == ["https://blackmassroasters.com/products/vitriolic-hiss-honduras"]

    @pytest.mark.asyncio
    async def test_marks_in_stock_from_any_available_variant(self, scraper, mocker):
        # A product with one sold-out variant but one available variant is in
        # stock; a product with none available is not.
        products = [
            _product("vitriolic-hiss-honduras", "VITRIOLIC HISS, Honduras"),
            _product("abhorrent-passage-kenya", "ABHORRENT PASSAGE, Kenya", available=False),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert scraper._shopify_stock_status["https://blackmassroasters.com/products/vitriolic-hiss-honduras"] is True
        assert scraper._shopify_stock_status["https://blackmassroasters.com/products/abhorrent-passage-kenya"] is False


class TestCurrencyPinning:
    """AUD pinned so geo-converted prices can never be stamped onto beans."""

    def test_currency_detected_is_true_in_init(self, scraper):
        # _currency_detected=True prevents _scrape_new_products from refetching
        # the collection page and letting a presentment currency in.
        assert scraper._currency_detected is True
        assert scraper.store_currency == "AUD"
        assert "Accept-Language" not in scraper.headers
        assert "Accept-Language" not in scraper.client._base_headers

    def test_geo_converted_page_cannot_override_aud(self, scraper):
        from bs4 import BeautifulSoup

        # Even a page advertising a converted currency must yield AUD.
        soup = BeautifulSoup('<html><body><meta property="og:price:currency" content="USD"></body></html>', "lxml")
        assert scraper._extract_currency_from_html(soup) == "AUD"

    def test_postprocess_forces_aud(self, scraper):
        bean = _make_bean("https://blackmassroasters.com/products/vitriolic-hiss-honduras")
        bean.currency = "USD"
        out = scraper.postprocess_extracted_bean(bean)
        assert out.currency == "AUD"
