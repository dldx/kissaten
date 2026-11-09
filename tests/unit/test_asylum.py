"""Unit tests for the Asylum Coffee scraper.

Asylum Coffee (asylumcoffee.co.uk) migrated off Wix to a custom Atom Sites
storefront: every ``/category/*`` URL 301-redirects to the homepage ``/#shop``
section, where the whole coffee catalogue is server-rendered as
``article.card`` elements with ``data-product-id`` / ``data-available``
attributes and ``/products/<slug>`` links. These tests run against a captured
homepage fixture (``tests/fixtures/asylum_coffee_home.html``) and verify the
single-store-URL scheme, card extraction, the /products/ path filter and GBP
currency pinning.
"""

import asyncio
from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.scrapers.asylum import STORE_URL, AsylumScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "asylum_coffee_home.html"


def _fixture_soup() -> BeautifulSoup:
    return BeautifulSoup(FIXTURE.read_text(), "lxml")


def test_registered_in_registry():
    registry = get_registry()
    assert registry.is_registered("asylum")
    info = registry.get_scraper_info("asylum")
    assert info is not None
    assert info.scraper_class is AsylumScraper
    assert info.currency == "GBP"
    assert info.country == "United Kingdom"
    assert info.status == "available"


def test_store_url_is_homepage_shop_grid():
    """The former Wix /category/* pages now 301 to the homepage; the single
    store URL must be the server-rendered homepage shop grid."""
    scraper = AsylumScraper()
    urls = asyncio.run(scraper.get_store_urls())
    assert urls == [STORE_URL]
    assert urls == ["https://asylumcoffee.co.uk/"]
    assert not any("/category/" in u for u in urls)


def test_extract_product_urls_from_homepage_cards(monkeypatch):
    """All in-stock /products/<slug> links on the shop grid are returned,
    deduplicated and resolved to absolute URLs."""
    scraper = AsylumScraper()
    soup = _fixture_soup()
    monkeypatch.setattr(scraper, "fetch_page", _async_return(soup))

    urls = asyncio.run(scraper._extract_product_urls_from_store(STORE_URL))

    # The captured fixture has 14 distinct product cards, all in stock.
    assert len(urls) == 14
    assert all(u.startswith("https://asylumcoffee.co.uk/products/") for u in urls)
    assert all(not u.startswith("https://www.") for u in urls)
    assert "/products/mirazu-geisha" in urls[0]
    # No duplicates
    assert len(set(urls)) == len(urls)
    # Non-coffee category links (e.g. /products/utstyr) never leak in
    assert not any(u.rstrip("/").endswith(("/utstyr", "/coffee")) for u in urls)


def test_extract_skips_sold_out_cards_by_attribute(monkeypatch):
    """A card carrying data-available="false" is skipped before URL filtering."""
    scraper = AsylumScraper()
    soup = _fixture_soup()
    first_card = soup.select("article.card")[0]
    first_card["data-available"] = "false"
    monkeypatch.setattr(scraper, "fetch_page", _async_return(soup))

    urls = asyncio.run(scraper._extract_product_urls_from_store(STORE_URL))
    assert len(urls) == 13
    sold_out_slug = first_card.select_one('a[href*="/products/"]')["href"].split("?")[0]
    assert sold_out_slug not in urls


def test_extract_skips_sold_out_cards_by_badge_text(monkeypatch):
    """A card whose text carries a sold-out marker is skipped."""
    scraper = AsylumScraper()
    soup = _fixture_soup()
    first_card = soup.select("article.card")[0]
    slug = first_card.select_one('a[href*="/products/"]')["href"].split("?")[0]
    first_card.append(BeautifulSoup('<span class="card__tag">Sold out</span>', "lxml").span)
    monkeypatch.setattr(scraper, "fetch_page", _async_return(soup))

    urls = asyncio.run(scraper._extract_product_urls_from_store(STORE_URL))
    assert len(urls) == 13
    assert slug not in urls


def test_postprocess_pins_gbp():
    """The site sells exclusively in GBP; the bean currency is pinned."""

    class _Bean:
        currency = "USD"

    scraper = AsylumScraper()
    bean = scraper.postprocess_extracted_bean(_Bean())
    assert bean.currency == "GBP"


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner
