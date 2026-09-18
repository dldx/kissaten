"""Unit tests for the Cofmos scraper (fixture-based, no network).

The fixture mirrors the real WooCommerce /kava/ category listing HTML of
cofmos.lt (konte theme li.product cards with "sold-out" badge markers).
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.cofmos import CofmosScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> CofmosScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return CofmosScraper(api_key="test-api-key")


def _listing_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "cofmos_kava.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("cofmos")
    assert info is not None
    assert info.roaster_name == "Cofmos"
    assert info.currency == "EUR"
    assert info.country == "Lithuania"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Cofmos"


async def test_store_urls_use_kava_category():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == ["https://cofmos.lt/kava/"]


async def test_extracts_in_stock_product_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://cofmos.lt/kava/")
    assert sorted(urls) == [
        "https://cofmos.lt/produktai/brazil-capadocia/",
        "https://cofmos.lt/produktai/fermentation-project/",
    ]


async def test_sold_out_card_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://cofmos.lt/kava/")
    # The Ethiopia Aricha card carries the sold-out badge ("Nebėra")
    assert "https://cofmos.lt/produktai/ethiopia-aricha/" not in urls


async def test_equipment_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://cofmos.lt/kava/")
    assert all("aeropress" not in u for u in urls)


async def test_fermentation_project_kit_is_kept(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://cofmos.lt/kava/")
    assert "https://cofmos.lt/produktai/fermentation-project/" in urls


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://cofmos.lt/kava/")
    assert urls == []


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://cofmos.lt/produktai/test-bean/",
        roaster="Cofmos",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "EUR"
