"""Unit tests for the Eiland Coffee Roasters scraper (fixture-based, no network).

Fixtures are trimmed copies of the real Squarespace listing page (product
blocks) and product detail page (meta tags + static-context variants JSON).
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.eiland_coffee import EilandCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

SHOP_URL = "https://www.eilandcoffee.com/shop"
PRODUCT_URL = "https://www.eilandcoffee.com/coffee-stock-room/ethiopia-sidama-ardi-natural-process"


def _make_scraper() -> EilandCoffeeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return EilandCoffeeScraper(api_key="test-api-key")


def _shop_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "eiland_shop.html").read_text(), "lxml")


def _product_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "eiland_product.html").read_text(), "lxml")


async def test_registry_entry():
    info = get_registry().get_scraper_info("eiland-coffee")
    assert info is not None
    assert info.roaster_name == "Eiland Coffee Roasters"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Eiland Coffee Roasters"


async def test_store_urls_include_shop_and_fermentation_project():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [
        "https://www.eilandcoffee.com/shop",
        "https://www.eilandcoffee.com/fermentationproject",
    ]


async def test_extracts_product_urls_from_shop_fixture(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(SHOP_URL)
    assert "https://www.eilandcoffee.com/coffee-stock-room/ethiopia-sidama-ardi-natural-process" in urls
    assert "https://www.eilandcoffee.com/coffee-stock-room/costa-rica-la-pastora-african-washed" in urls
    # Every extracted URL uses the /coffee-stock-room/ path format.
    assert all("/coffee-stock-room/" in u for u in urls)
    assert len(urls) == 2


async def test_sold_out_card_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(SHOP_URL)
    assert "https://www.eilandcoffee.com/coffee-stock-room/green-room-blend" not in urls


async def test_non_coffee_products_are_excluded(monkeypatch):
    scraper = _make_scraper()
    soup = BeautifulSoup(
        """
        <div class="product-block">
          <a href="/coffee-stock-room/gift-card">Gift Card</a>
        </div>
        <div class="product-block">
          <a href="/coffee-stock-room/live-cupping-at-the-roastery">Live Cupping at the Roastery</a>
        </div>
        <div class="product-block">
          <a href="/coffee-stock-room/fermentation-project-kit">Fermentation Project Kit</a>
        </div>
        """,
        "lxml",
    )

    async def fake_fetch(url, **kwargs):
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(SHOP_URL)
    # Gift card and the live-cupping event ticket are excluded; the Fermentation
    # Project kit is NOT excluded (tasting-kit flagging is automatic downstream).
    assert urls == ["https://www.eilandcoffee.com/coffee-stock-room/fermentation-project-kit"]


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
    data = EilandCoffeeScraper._parse_static_context(soup)
    assert data is not None
    product = data["product"]
    assert product["urlSlug"] == "ethiopia-sidama-ardi-natural-process"
    assert len(product["variants"]) == 3


async def test_extract_variants_formats_grind_options():
    soup = _product_soup()
    variants = EilandCoffeeScraper._extract_variants(soup)
    assert variants is not None
    text = variants.get_text()
    assert "Variants:" in text
    assert "Whole Bean" in text
    assert "Price: 21.0 USD" in text
    assert "instock" in text


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
    assert "French Press" in text
    # The rest of the page (nav/footer/scripts) is stripped.
    assert "polyfiller" not in text

    # Listing pages are left untouched.
    listing = await scraper.fetch_page(SHOP_URL, use_playwright=False)
    assert "Variants:" not in listing.get_text()


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://www.eilandcoffee.com/coffee-stock-room/test-bean",
        roaster="Eiland Coffee Roasters",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "USD"
