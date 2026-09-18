"""Unit tests for the Talavera Coffee scraper (fixture-based, no network).

Fixtures are trimmed copies of the real Squarespace shop page (JS-rendered grid
with the embedded escaped product JSON blob) and product detail page (meta tags
+ static-context variants JSON).
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.talavera_coffee import TalaveraCoffeeScraper

FIXTURES = Path(__file__).parent.parent / "fixtures"

SHOP_URL = "https://www.talaveracoffee.com/shop"
PRODUCT_URL = "https://www.talaveracoffee.com/shop/p/gabriel-aureliano-oaxaca-mx"


def _make_scraper() -> TalaveraCoffeeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return TalaveraCoffeeScraper(api_key="test-api-key")


def _shop_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "talavera_shop.html").read_text(), "lxml")


def _product_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "talavera_product.html").read_text(), "lxml")


async def test_registry_entry():
    info = get_registry().get_scraper_info("talavera-coffee")
    assert info is not None
    assert info.roaster_name == "Talavera Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Talavera Coffee"


async def test_store_urls_use_shop_page():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == ["https://www.talaveracoffee.com/shop"]


def test_parse_shop_product_blob():
    records = TalaveraCoffeeScraper._parse_shop_product_blob((FIXTURES / "talavera_shop.html").read_text())
    by_slug = dict(records)
    assert by_slug["amor-y-corazon"] == 6
    assert by_slug["roasters-choice-sampler-set"] == 9223372036854775807
    assert by_slug["azulito-lindo"] == 0


def test_parse_shop_product_blob_uses_product_level_quantity():
    # The gabriel-aureliano record embeds a variant-level qtyInStock (41) before
    # urlSlug; the product-level value (61) must win.
    records = TalaveraCoffeeScraper._parse_shop_product_blob((FIXTURES / "talavera_shop.html").read_text())
    by_slug = dict(records)
    assert by_slug["gabriel-aureliano-oaxaca-mx"] == 61


async def test_extracts_product_urls_from_shop_fixture(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(SHOP_URL)
    assert "https://www.talaveracoffee.com/shop/p/amor-y-corazon" in urls
    assert "https://www.talaveracoffee.com/shop/p/gabriel-aureliano-oaxaca-mx" in urls
    # The sampler set is extracted (flagged as a tasting kit downstream).
    assert "https://www.talaveracoffee.com/shop/p/roasters-choice-sampler-set" in urls
    # Every extracted URL uses the /shop/p/ path format.
    assert all("/shop/p/" in u for u in urls)
    assert len(urls) == 3


async def test_sold_out_products_are_skipped(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(SHOP_URL)
    # qtyInStock == 0 in the embedded blob.
    assert "https://www.talaveracoffee.com/shop/p/azulito-lindo" not in urls


async def test_non_coffee_products_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(SHOP_URL)
    # Sticker, gift card (base class) and the live-cupping event ticket
    # (base class "cupping" service pattern) are excluded.
    assert "https://www.talaveracoffee.com/shop/p/talavera-mug-sticker" not in urls
    assert "https://www.talaveracoffee.com/shop/p/gift-card" not in urls
    assert (
        "https://www.talaveracoffee.com/shop/p/the-fermentation-project-live-cupping-at-timberline-crossing" not in urls
    )


async def test_sampler_url_is_flagged_as_tasting_kit():
    scraper = _make_scraper()
    assert scraper.is_tasting_kit_url("https://www.talaveracoffee.com/shop/p/roasters-choice-sampler-set")


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(SHOP_URL)
    assert urls == []


async def test_parse_static_context_with_trailing_statements():
    # The real static-context script ends with statements after the JSON blob;
    # the brace-matching parser must still recover the product variants.
    soup = _product_soup()
    data = TalaveraCoffeeScraper._parse_static_context(soup)
    assert data is not None
    product = data["product"]
    assert product["urlSlug"] == "gabriel-aureliano-oaxaca-mx"
    assert len(product["variants"]) == 2


async def test_extract_variants_formats_grind_options():
    soup = _product_soup()
    variants = TalaveraCoffeeScraper._extract_variants(soup)
    assert variants is not None
    text = variants.get_text()
    assert "Variants:" in text
    assert "Wholebean" in text
    assert "Ground" in text
    assert "Price: 22.0 USD" in text


async def test_fetch_page_narrows_to_meta_and_variants(monkeypatch):
    scraper = _make_scraper()

    async def fake_base_fetch(self, url, **kwargs):
        return _product_soup()

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_base_fetch)

    compact = await scraper.fetch_page(PRODUCT_URL, use_playwright=False)
    text = str(compact)
    # og:title / product:* meta tags are kept.
    assert 'property="og:title"' in text
    assert 'property="product:price:currency"' in text
    assert "USD" in text
    # Parsed variants are surfaced as text.
    assert "Variants:" in text
    assert "Wholebean" in text
    # The rest of the page (nav/footer/scripts) is stripped.
    assert "polyfiller" not in text

    # Listing pages are left untouched.
    listing = await scraper.fetch_page(SHOP_URL, use_playwright=False)
    assert "Variants:" not in listing.get_text()


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://www.talaveracoffee.com/shop/p/test-bean",
        roaster="Talavera Coffee",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "USD"
