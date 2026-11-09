"""Fixture-based tests for the Mr Wush Wush scraper (Scraper 2).

The storefront moved from a Wix store (with Spanish slug URLs and a Chilean
currency metadata assumption) to a Shopify store with ``/collections/...``
listing pages and ``/products/<handle>`` product URLs. These tests exercise
``_extract_product_urls_from_store`` against a realistic fixture of the new
Shopify collection page, verifying:
  * the store URLs point at the new Shopify collections,
  * product URLs (``/products/...``) are found on the collection pages.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from bs4 import BeautifulSoup

from kissaten.scrapers.mr_wush_wush import MrWushWushCoffeeScraper

FIXTURE = Path(__file__).parent.parent / "fixtures" / "mr_wush_wush_collection.html"


def _load_fixture_soup() -> BeautifulSoup:
    return BeautifulSoup(FIXTURE.read_text(encoding="utf-8"), "lxml")


@pytest.fixture
def scraper() -> MrWushWushCoffeeScraper:
    return MrWushWushCoffeeScraper(api_key="test-fake-key")


def test_store_urls_point_at_shopify_collections(scraper):
    """get_store_urls returns the new Shopify collection pages."""
    urls = asyncio.run(scraper.get_store_urls())
    assert urls == [
        "https://mrwushwush.com/collections/tradicionales",
        "https://mrwushwush.com/collections/exoticos",
        "https://mrwushwush.com/collections/elite",
        "https://mrwushwush.com/collections/culturing",
    ]


def test_extract_product_urls_from_shopify_collection(scraper):
    """Product URLs are found via the Shopify /products/ selector."""
    soup = _load_fixture_soup()
    scraper.fetch_page = AsyncMock(return_value=soup)

    urls = asyncio.run(scraper._extract_product_urls_from_store("https://mrwushwush.com/collections/tradicionales"))

    expected = [
        "https://mrwushwush.com/products/cafe-tradicional-regional-tolima-lavado",
        "https://mrwushwush.com/products/bourbon-rojo-lavado-cafe-tradicional",
        "https://mrwushwush.com/products/caturra-natural-cafe-tradicional-rioblanco",
    ]
    assert sorted(urls) == sorted(expected)


def test_extract_product_urls_handles_fetch_failure(scraper):
    """A None fetch result yields no URLs without raising."""
    scraper.fetch_page = AsyncMock(return_value=None)
    urls = asyncio.run(scraper._extract_product_urls_from_store("https://mrwushwush.com/collections/tradicionales"))
    assert urls == []
