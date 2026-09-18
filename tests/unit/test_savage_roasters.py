"""Unit tests for the Savage Roasters scraper (fixture-based, no network).

Savage runs the Shopify Dawn theme but disables products.json (404), so
discovery uses the server-rendered /collections/all HTML with the Dawn
``?filter.v.availability=1`` in-stock filter plus card-level "Épuisé" checks.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.savage_roasters import SavageRoastersScraper

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://www.savageroasters.coffee/collections/all?filter.v.availability=1"


def _make_scraper() -> SavageRoastersScraper:
    return SavageRoastersScraper(api_key="test-api-key")


def _collection_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "savage_collection.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("savage-roasters")
    assert info is not None
    assert info.roaster_name == "Savage Roasters"
    assert info.currency == "EUR"
    assert info.country == "France"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Savage Roasters"


async def test_store_urls_use_availability_filter():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [STORE_URL]
    assert "filter.v.availability=1" in urls[0]


async def test_extracts_in_stock_coffee_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _collection_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert "https://www.savageroasters.coffee/products/ethiopie-chelbesa" in urls
    assert all("/products/" in u for u in urls)


async def test_sold_out_cards_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _collection_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert "https://www.savageroasters.coffee/products/guatemala-sold-out-lot" not in urls
    # The Fermentation Project kit card is currently sold out on the live site
    # ("épuisé" badge), so it is skipped by the stock check until restocked.
    assert (
        "https://www.savageroasters.coffee/products/the-fermentation-project-by-james-hoffmann-lucia-solis-testing-kit"
        not in urls
    )


async def test_in_stock_tasting_kit_is_kept(monkeypatch):
    """The Fermentation Project kit slug must pass URL filtering when in stock."""
    scraper = _make_scraper()
    soup = BeautifulSoup(
        "<html><body><ul>"
        '<li><div class="card-wrapper product-card-wrapper">'
        '<a href="/products/the-fermentation-project-by-james-hoffmann-lucia-solis-testing-kit">'
        "The Fermentation Project tasting set</a>"
        "<span>32,00 &euro;</span>"
        "</div></li>"
        "</ul></body></html>",
        "lxml",
    )

    async def fake_fetch(url, **kwargs):
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert (
        "https://www.savageroasters.coffee/products/the-fermentation-project-by-james-hoffmann-lucia-solis-testing-kit"
        in urls
    )


async def test_merch_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _collection_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert all("tee-shirt" not in u for u in urls)


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)
    assert urls == []


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Éthiopie - Yirgacheffe Chelbesa",
        url="https://www.savageroasters.coffee/products/ethiopie-chelbesa",
        roaster="Savage Roasters",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "EUR"
