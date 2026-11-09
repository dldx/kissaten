"""Tests for the Freda scraper (Shopify products.json via ShopifyJsonScraper)."""

import json
from pathlib import Path

from kissaten.scrapers.freda import FredaScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).parent.parent / "fixtures" / "freda_coffee_beans_products.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_registry_entry():
    info = get_registry().get_scraper_info("freda")
    assert info is not None
    assert info.roaster_name == "Freda"
    assert info.website == "https://freda.coffee"
    assert info.currency == "GBP"


def test_listing_url_points_at_live_coffee_beans_collection():
    """The legacy all-coffee-copy handle was emptied roaster-side; the
    scraper must target the live curated ``coffee-beans`` collection."""
    scraper = FredaScraper()
    urls = scraper.products_json_urls
    assert urls == ["https://freda.coffee/collections/coffee-beans/products.json"]
    assert "all-coffee-copy" not in urls[0]


async def test_extract_product_urls_from_coffee_beans_fixture(monkeypatch):
    scraper = FredaScraper()
    products = _load_fixture()["products"]
    assert len(products) == 7

    async def fake_fetch(products_json_url: str) -> list[dict]:
        assert products_json_url == "https://freda.coffee/collections/coffee-beans/products.json"
        return products

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    result = await scraper._extract_product_urls_from_store(
        "https://freda.coffee/collections/coffee-beans/products.json"
    )
    handles = {u.rsplit("/", 1)[-1] for u in result}
    assert handles == {
        "black-dog",
        "black-rain",
        "cajamarca-peru",
        "decaf",
        "gotiti-ethiopia",
        "la-bolsa-guatemala",
        "lalesa-ethiopia-1",
    }
    for u in result:
        assert u.startswith("https://freda.coffee/products/")


def test_preprocess_product_url_strips_collection_segment():
    scraper = FredaScraper()
    url = scraper.preprocess_product_url("https://freda.coffee/collections/coffee-beans/products/black-dog")
    assert url == "https://freda.coffee/products/black-dog"
    assert (
        scraper.preprocess_product_url("https://freda.coffee/products/black-dog")
        == "https://freda.coffee/products/black-dog"
    )
