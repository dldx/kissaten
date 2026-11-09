"""Fixture-based tests for the Austrått Kaffebrenneri scraper (Scraper 3).

The live store page changed from a ``/categories/kaffe`` category page to a
Next.js ``/products`` listing with UUID product slugs. These tests exercise
``_extract_product_urls_from_store`` against a realistic fixture of the new
page, verifying:
  * product URLs are found on the new ``/products`` page,
  * sold-out cards ("Ikke på lager" / "Utsolgt") are skipped,
  * the equipment bundle ("Espresso og baristamaskin") is excluded via
    normalized title matching even though its URL is a UUID slug,
  * subscription-only products are excluded via normalized title matching.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from bs4 import BeautifulSoup

from kissaten.scrapers.austraatt_kaffebrenneri import AustraattKaffebrenneriScraper

FIXTURE = Path(__file__).parent.parent / "fixtures" / "austraatt_kaffebrenneri_products.html"


def _load_fixture_soup() -> BeautifulSoup:
    return BeautifulSoup(FIXTURE.read_text(encoding="utf-8"), "lxml")


@pytest.fixture
def scraper() -> AustraattKaffebrenneriScraper:
    return AustraattKaffebrenneriScraper(api_key="test-fake-key")


def test_normalize_card_text():
    """_normalize_card_text slugifies Norwegian/English product names."""
    scraper = AustraattKaffebrenneriScraper(api_key="test-fake-key")
    assert scraper._normalize_card_text("Espresso og baristamaskin") == "espresso-og-baristamaskin"
    assert scraper._normalize_card_text("Kaffe fra Sør- og Mellom Amerika 1kg") == (
        "kaffe-fra-sør-og-mellom-amerika-1kg"
    )
    assert scraper._normalize_card_text("Abonnement tilgjengelig") == "abonnement-tilgjengelig"


def test_get_card_title_prefers_img_alt():
    """_get_card_title extracts the title from the card image's alt attribute."""
    scraper = AustraattKaffebrenneriScraper(api_key="test-fake-key")
    soup = _load_fixture_soup()
    cards = soup.select('div:has(> a[href*="/products/"])')
    assert cards, "fixture must contain product cards"

    title = scraper._get_card_title(cards[0])
    assert title == "Kenya, Kirinyaga AA"


def test_get_store_urls_returns_new_products_page(scraper):
    """get_store_urls returns the new Next.js /products listing page."""
    urls = asyncio.run(scraper.get_store_urls())
    assert urls == ["https://www.austraattkaffebrenneri.no/products"]


def test_extract_product_urls_from_store_filters_stock_and_equipment(scraper):
    """In-stock coffees are found; sold-out and equipment cards are skipped."""
    soup = _load_fixture_soup()
    scraper.fetch_page = AsyncMock(return_value=soup)

    urls = asyncio.run(scraper._extract_product_urls_from_store("https://www.austraattkaffebrenneri.no/products"))

    # In-stock coffees present (plain slug + UUID slug)
    assert "https://www.austraattkaffebrenneri.no/products/kenya-kirinyaga-aa" in urls
    assert "https://www.austraattkaffebrenneri.no/products/404e7fb8-c9ea-4a65-a41f-20b68adbec72" in urls
    # Equipment bundle excluded via normalized title matching (UUID URL can't match URL pattern)
    assert "https://www.austraattkaffebrenneri.no/products/83f2ab3a-d2e8-494c-9d73-7d2bbafe3690" not in urls
    # Subscription-only product excluded
    assert "https://www.austraattkaffebrenneri.no/products/abonnement-tilgjengelig" not in urls
    # Sold-out products skipped ("Ikke på lager" and "Utsolgt")
    assert "https://www.austraattkaffebrenneri.no/products/utsolgt-kaffe" not in urls
    assert "https://www.austraattkaffebrenneri.no/products/solgt-ut-kaffe" not in urls
    # Exactly the two in-stock coffee products
    assert len(urls) == 2


def test_extract_product_urls_handles_fetch_failure(scraper):
    """A None fetch result yields no URLs without raising."""
    scraper.fetch_page = AsyncMock(return_value=None)
    urls = asyncio.run(scraper._extract_product_urls_from_store("https://www.austraattkaffebrenneri.no/products"))
    assert urls == []
