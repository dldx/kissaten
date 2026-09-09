"""Unit tests for the Now Coffee scraper.

Tests run against **captured fixtures** of the live ``single-origins`` and
``blends`` collections (6 + 3 products on capture), so catalogue drift — a
drip-bag product leaking back in, a URL-format change — fails the test and is
visible as a fixture diff.

Covered per-scraper behaviour:
- The two curated bean collections (the union is the site's whole bean
  catalogue; ``collections/all`` additionally carries barista training
  courses, socks and mushroom coffee which live outside them).
- The ``exclude_slugs`` gate (keeps 5 of 6 single origins — the coffee drip
  bags are a single-serve sachet format, not whole beans — plus all 3 blends).
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
from kissaten.scrapers.now_coffee import NowCoffeeScraper

SINGLE_ORIGINS_FIXTURE = (
    Path(__file__).resolve().parent.parent / "fixtures" / "now-coffee_single-origins_products.json"
)
BLENDS_FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "now-coffee_blends_products.json"
SINGLE_ORIGINS_URL = "https://nowcoffee.co.za/collections/single-origins/products.json"
BLENDS_URL = "https://nowcoffee.co.za/collections/blends/products.json"


def _fixture_products(fixture: Path) -> list[dict]:
    return json.loads(fixture.read_text())["products"]


def _product(handle: str, title: str, available: bool = True) -> dict:
    return {
        "handle": handle,
        "title": title,
        "product_type": "",
        "variants": [{"price": "160.00", "available": available}],
    }


def _install_fixture(scraper: NowCoffeeScraper, fixture: Path) -> None:
    async def fake_fetch(url: str) -> list[dict]:
        return _fixture_products(fixture)

    scraper._fetch_all_shopify_products = fake_fetch  # type: ignore[method-assign]


def _make_bean(url: str) -> CoffeeBean:
    return CoffeeBean(name="INCEPTION | BLEND", roaster="Now Coffee", url=url, origins=[], price_options=[])


@pytest.fixture
def scraper():
    return NowCoffeeScraper()


class TestExtractProductUrlsFromStore:
    """The captured-catalogue gate: two curated bean collections, drip bags out."""

    @pytest.mark.asyncio
    async def test_single_origins_collection_keeps_bean_set(self, scraper):
        _install_fixture(scraper, SINGLE_ORIGINS_FIXTURE)

        urls = await scraper._extract_product_urls_from_store(SINGLE_ORIGINS_URL)

        # 6 captured products, the coffee drip-bags product dropped.
        assert len(urls) == 5
        # Every kept URL is the canonical no-collection form.
        assert all("/collections/" not in u and u.startswith("https://nowcoffee.co.za/products/") for u in urls)

        assert "https://nowcoffee.co.za/products/alo-honey-ethiopia-special-release" in urls
        assert "https://nowcoffee.co.za/products/la-isla-sl28-costa-rica" in urls
        assert "https://nowcoffee.co.za/products/lekker-decaf-colombia" in urls
        assert "https://nowcoffee.co.za/products/las-flores-red-bourbon-decaf-natural-special-release" in urls

    @pytest.mark.asyncio
    async def test_single_origins_drops_drip_bags(self, scraper):
        _install_fixture(scraper, SINGLE_ORIGINS_FIXTURE)

        urls = await scraper._extract_product_urls_from_store(SINGLE_ORIGINS_URL)

        assert not any("drip-bag" in u for u in urls)
        assert "https://nowcoffee.co.za/products/coffee-drip-bags" not in urls

    @pytest.mark.asyncio
    async def test_blends_collection_keeps_all_blends(self, scraper):
        _install_fixture(scraper, BLENDS_FIXTURE)

        urls = await scraper._extract_product_urls_from_store(BLENDS_URL)

        assert len(urls) == 3
        assert "https://nowcoffee.co.za/products/inception-blend" in urls
        assert "https://nowcoffee.co.za/products/just-now-blend" in urls
        assert "https://nowcoffee.co.za/products/zonke-blend" in urls

    @pytest.mark.asyncio
    async def test_excludes_non_coffee_slugs_if_they_leak_in(self, scraper, mocker):
        # Synthetic: the curated collections carry no courses/socks today, but
        # a future drift of the ``now-coffee`` catch-all collection in must
        # still be gated by the slug net.
        products = [
            _product("inception-blend", "INCEPTION | BLEND"),
            _product("home-barista-course", "Home Barista Course"),
            _product("versus-socks-now-coffee-v2", "Versus Socks Now Coffee v2"),
            _product("mushroom-coffee", "Mushroom Coffee"),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        urls = await scraper._extract_product_urls_from_store(BLENDS_URL)

        assert urls == ["https://nowcoffee.co.za/products/inception-blend"]

    @pytest.mark.asyncio
    async def test_marks_in_stock_from_any_available_variant(self, scraper, mocker):
        # A product with one sold-out variant but one available variant is in
        # stock; a product with none available is not.
        products = [
            _product("inception-blend", "INCEPTION | BLEND"),
            _product("zonke-blend", "ZONKE | BLEND", available=False),
        ]
        mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

        await scraper._extract_product_urls_from_store(BLENDS_URL)

        assert scraper._shopify_stock_status["https://nowcoffee.co.za/products/inception-blend"] is True
        assert scraper._shopify_stock_status["https://nowcoffee.co.za/products/zonke-blend"] is False

    def test_preprocess_product_url_strips_collection(self, scraper):
        assert (
            scraper.preprocess_product_url(
                "https://nowcoffee.co.za/collections/single-origins/products/inception-blend"
            )
            == "https://nowcoffee.co.za/products/inception-blend"
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
        bean = _make_bean("https://nowcoffee.co.za/products/inception-blend")
        bean.currency = "USD"
        out = scraper.postprocess_extracted_bean(bean)
        assert out.currency == "ZAR"
