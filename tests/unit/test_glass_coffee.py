"""Unit tests for the Glass Coffee scraper (fixture-based, no network).

The fixture is a trimmed copy of the live ``/collections/coffee`` listing
(Shopify Dawn-style theme) with the ``a.product-card`` cards inside
``.product-grid`` and the "Sold out" badge the live site renders.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.scrapers.glass_coffee import GlassCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> GlassCoffeeScraper:
    return GlassCoffeeScraper(api_key="test-api-key")


def _listing_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "glass_coffee_shop.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("glass-coffee")
    assert info is not None
    assert info.roaster_name == "Glass Coffee"
    assert info.currency == "GBP"
    assert info.country == "United Kingdom"
    assert info.requires_api_key is True
    assert info.status == "available"


async def test_store_urls_use_plain_coffee_collection():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    # The availability-filtered URL previously rendered an empty grid on
    # page 2; the scraper now relies on the plain collection + client-side
    # sold-out filtering.
    assert urls == ["https://glasscoffee.co.uk/collections/coffee"]


async def test_extracts_product_urls_from_grid(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://glasscoffee.co.uk/collections/coffee")
    assert urls, "expected non-empty product URL list from fixture"
    assert all(u.startswith("https://glasscoffee.co.uk/products/") for u in urls)
    assert "https://glasscoffee.co.uk/products/bambito-estate-caturra-catuai-washed" in urls


async def test_sold_out_card_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://glasscoffee.co.uk/collections/coffee")
    assert "https://glasscoffee.co.uk/products/red-fruits" not in urls


async def test_urls_are_deduped_and_query_stripped(monkeypatch):
    soup = _listing_soup()
    # Duplicate a card and add a tracking query to exercise dedupe/strip.
    grid = soup.select_one(".product-grid")
    card = soup.select_one(".product-grid a.product-card[href*='/products/']")
    dup = BeautifulSoup(str(card), "lxml").select_one("a.product-card")
    dup["href"] = dup["href"] + "?variant=123"
    grid.append(dup.parent)

    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://glasscoffee.co.uk/collections/coffee")
    assert len(urls) == len(set(urls))


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://glasscoffee.co.uk/collections/coffee")
    assert urls == []


async def test_missing_grid_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return BeautifulSoup("<html><body><h1>Empty</h1></body></html>", "lxml")

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://glasscoffee.co.uk/collections/coffee")
    assert urls == []
