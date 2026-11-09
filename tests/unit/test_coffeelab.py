"""Unit tests for the Coffee Lab scraper (fixture-based, no network).

Coffee Lab (coffeelab.pl, Warsaw) migrated from PrestaShop to WooCommerce:
products live under ``/en/product/<slug>/`` and the coffee category listing
is ``/en/product-cat/coffee-en/`` (paginated with ``/page/N/`` paths).

The fixture is a trimmed copy of the real server-rendered WooCommerce
listing (``div.shop-archive__products`` with ``li.product-card`` items).
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.scrapers.coffeelab import CoffeeLabScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> CoffeeLabScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return CoffeeLabScraper(api_key="test-api-key")


def _category_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "coffeelab_shop.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("coffeelab")
    assert info is not None
    assert info.roaster_name == "Coffee Lab"
    assert info.currency == "PLN"
    assert info.country == "Poland"
    assert info.requires_api_key is True
    assert info.status == "available"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Coffee Lab"


async def test_store_urls_use_woocommerce_category():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [
        "https://coffeelab.pl/en/product-cat/coffee-en/",
        "https://coffeelab.pl/en/product-cat/coffee-en/page/2/",
    ]


async def test_extracts_product_urls_from_category_fixture(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _category_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://coffeelab.pl/en/product-cat/coffee-en/")
    # Every extracted URL uses the WooCommerce /en/product/ path format.
    assert urls
    assert all(u.startswith("https://coffeelab.pl/en/product/") for u in urls)
    assert "https://coffeelab.pl/en/product/colombia-el-indio-decaf/" in urls
    assert "https://coffeelab.pl/en/product/brazil-cemorrado-sweet-edition/" in urls
    assert "https://coffeelab.pl/en/product/autumn-uganda-jukia/" in urls
    # Deduplicated: image + title anchors point at the same product.
    assert len(urls) == len(set(urls))


async def test_excludes_zestaw_brewlab_tasting_set(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _category_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://coffeelab.pl/en/product-cat/coffee-en/")
    # The BREWLAB tasting set must be excluded from bean URLs.
    assert "https://coffeelab.pl/en/product/zestaw-brewlab/" not in urls
