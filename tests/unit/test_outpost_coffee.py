"""Tests for the Outpost Coffee scraper (Shopify HTML listing, BaseScraper)."""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.scrapers.outpost_coffee import OutpostCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).parent.parent / "fixtures" / "outpost_coffee_collection_all.html"


def _load_soup() -> BeautifulSoup:
    return BeautifulSoup(FIXTURE.read_text(encoding="utf-8"), "html.parser")


def test_registry_entry():
    info = get_registry().get_scraper_info("outpost-coffee")
    assert info is not None
    assert info.roaster_name == "Outpost Coffee Roasters"
    assert info.website == "https://outpost.coffee"
    assert info.currency == "GBP"


async def test_store_url_targets_all_collection():
    """The dedicated ``coffees`` collection is empty roaster-side; the
    scraper must list products from the store-wide ``all`` collection."""
    scraper = OutpostCoffeeScraper()
    store_urls = await scraper.get_store_urls()
    assert store_urls == ["https://outpost.coffee/collections/all"]


async def test_extract_keeps_coffee_and_filters_equipment_merch(monkeypatch):
    scraper = OutpostCoffeeScraper()
    soup = _load_soup()

    async def fake_fetch_page(url, retries=0, use_playwright=False):
        assert url == "https://outpost.coffee/collections/all"
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch_page)
    urls = await scraper._extract_product_urls_from_store("https://outpost.coffee/collections/all")

    slugs = {u.rstrip("/").rsplit("/", 1)[-1] for u in urls}

    # Coffee products must be kept
    assert {"broken-promise", "cheat-code-001", "cool-kids-001", "low-rider"} <= slugs

    # Equipment, papers, merch and non-coffee extras must be filtered out
    for excluded in [
        "aeropress-clear",
        "aeropress-filter-papers-350",
        "hario-v60-plastic-dripper",
        "la-marzocco-linea-mini",
        "gift-card",
        "op-c-running-cap",
        "op-c-tote-bag",
    ]:
        assert excluded not in slugs
