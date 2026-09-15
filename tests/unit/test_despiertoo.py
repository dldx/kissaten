"""Unit tests for the Despiertoo scraper (fixture-based, no network).

Despiertoo is a Wix storefront: the homepage gallery uses ``product-item-root``
cards (sold-out markers in Spanish: "Agotado"/"Agotada"), and product detail
pages embed all content inside ``div[data-hook="product-page"]``.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.despiertoo import DespiertooScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

HOME_URL = "https://www.despiertoo.com/"
PRODUCT_URL = "https://www.despiertoo.com/product-page/colombia-chiroso"


def _make_scraper() -> DespiertooScraper:
    return DespiertooScraper(api_key="test-api-key")


def _home_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "despiertoo_home.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("despiertoo")
    assert info is not None
    assert info.roaster_name == "Despiertoo"
    assert info.currency == "EUR"
    assert info.country == "Spain"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Despiertoo"


async def test_store_urls_use_homepage_gallery():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [HOME_URL]


async def test_extracts_in_stock_coffee_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _home_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(HOME_URL)

    assert "https://www.despiertoo.com/product-page/colombia-waterbomb" in urls
    assert all("/product-page/" in u for u in urls)


async def test_sold_out_card_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _home_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(HOME_URL)

    # The fermentation-project card carries "Preventa Web Agotada" in its aria-label
    assert "https://www.despiertoo.com/product-page/fermentation-project" not in urls


async def test_equipment_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _home_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(HOME_URL)

    joined = " ".join(urls)
    assert "asobu-orb" not in joined


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(HOME_URL)
    assert urls == []


async def test_fetch_page_product_page_narrows_to_product_container(monkeypatch):
    scraper = _make_scraper()
    full_soup = BeautifulSoup((FIXTURES / "despiertoo_product.html").read_text(), "lxml")

    async def fake_base_fetch_page(self, url: str, **kwargs) -> BeautifulSoup:
        return full_soup

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_base_fetch_page)

    compact = await scraper.fetch_page(PRODUCT_URL)

    html = str(compact)
    # Kept: the Wix product-page container
    assert 'data-hook="product-page"' in html
    assert "Colombia Chiroso" in compact.get_text()
    # Dropped: nav noise outside the container
    assert "NOISE NAV" not in html
    assert "NOISE FOOTER" not in html


async def test_fetch_page_listing_url_returns_unmodified_soup(monkeypatch):
    scraper = _make_scraper()
    home_soup = _home_soup()

    async def fake_base_fetch_page(self, url: str, **kwargs) -> BeautifulSoup:
        return home_soup

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_base_fetch_page)

    compact = await scraper.fetch_page(HOME_URL)
    assert compact is home_soup


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Colombia Chiroso",
        url=PRODUCT_URL,
        roaster="Despiertoo",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "EUR"
