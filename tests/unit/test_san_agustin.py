"""Unit tests for the San Agustín scraper (fixture-based, no network).

The fixture is a trimmed copy of the real WooCommerce category listing
(``/categoria-producto/el-mejor-cafe-del-mundo/``) with the per-card
``outofstock`` classes and "Agotado" labels the live site emits.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.san_agustin import SanAgustinScraper

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> SanAgustinScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return SanAgustinScraper(api_key="test-api-key")


def _listing_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "san_agustin_coffee.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("san-agustin")
    assert info is not None
    assert info.roaster_name == "San Augustín Tostadores De Café"
    assert info.currency == "EUR"
    assert info.country == "Spain"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "San Augustín Tostadores De Café"


async def test_store_urls():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == ["https://www.sanagustin.com/categoria-producto/el-mejor-cafe-del-mundo/"]


async def test_extracts_product_urls_from_listing_fixture(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(
        "https://www.sanagustin.com/categoria-producto/el-mejor-cafe-del-mundo/"
    )
    # Every extracted URL uses the /producto/ permalink format.
    assert all("/producto/" in u for u in urls)
    assert "https://www.sanagustin.com/producto/la-cabana-origen/" in urls


async def test_sold_out_card_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(
        "https://www.sanagustin.com/categoria-producto/el-mejor-cafe-del-mundo/"
    )
    # The Fermentation Project card is out of stock (outofstock class + Agotado label).
    assert "https://www.sanagustin.com/producto/fermentation-project-james-hoffmann/" not in urls


async def test_equipment_and_sweets_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(
        "https://www.sanagustin.com/categoria-producto/el-mejor-cafe-del-mundo/"
    )
    assert not any("molino" in u for u in urls)
    assert not any("dulces" in u for u in urls)
    assert urls == ["https://www.sanagustin.com/producto/la-cabana-origen/"]


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(
        "https://www.sanagustin.com/categoria-producto/el-mejor-cafe-del-mundo/"
    )
    assert urls == []


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://www.sanagustin.com/producto/test-bean/",
        roaster="San Augustín Tostadores De Café",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "EUR"
