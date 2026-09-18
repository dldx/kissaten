"""Unit tests for the Cafe Domestique scraper (fixture-based, no network).

The fixture mirrors the real Big Cartel /products listing page of
cafedomestique.bigcartel.com (product-list cards with "sold" class markers).
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.cafe_domestique import CafeDomestiqueScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> CafeDomestiqueScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return CafeDomestiqueScraper(api_key="test-api-key")


def _listing_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "cafe_domestique_products.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("cafe-domestique")
    assert info is not None
    assert info.roaster_name == "Cafe Domestique"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Cafe Domestique"


async def test_store_urls_use_products_listing():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == ["https://cafedomestique.bigcartel.com/products"]


async def test_extracts_in_stock_product_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://cafedomestique.bigcartel.com/products")
    assert "https://cafedomestique.bigcartel.com/product/single-origin-ethiopia" in urls


async def test_sold_out_card_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://cafedomestique.bigcartel.com/products")
    # The Fermentation Project tasting kit card carries the "sold" class
    assert (
        "https://cafedomestique.bigcartel.com/product/pre-order-fermentation-project-tasting-kit-cafe-pickup-or-shipping"
        not in urls
    )


async def test_coming_soon_card_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://cafedomestique.bigcartel.com/products")
    # "Coming soon" text (no "sold" class) is also treated as unavailable
    assert "https://cafedomestique.bigcartel.com/product/house-blend" not in urls


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://cafedomestique.bigcartel.com/products")
    assert urls == []


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://cafedomestique.bigcartel.com/product/test-bean",
        roaster="Cafe Domestique",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "USD"
