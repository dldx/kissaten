"""Tests for the NORD scraper (Shopify JSON, no network)."""

from kissaten.scrapers.nord_coffee import NordCoffeeScraper
from kissaten.scrapers.registry import get_registry


def _make_scraper() -> NordCoffeeScraper:
    return NordCoffeeScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("nord-coffee")
    assert info is not None
    assert info.roaster_name == "NORD"
    assert info.currency == "AUD"
    assert info.country == "Australia"
    assert info.website == "https://nord.coffee"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "NORD"


def test_preprocess_product_url_strips_collection():
    scraper = _make_scraper()
    url = "https://nord.coffee/collections/frontpage/products/emerson-narvaez-washed-geisha"
    assert scraper.preprocess_product_url(url) == "https://nord.coffee/products/emerson-narvaez-washed-geisha"


async def test_extract_skips_excluded_handles(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return [
            {
                "handle": "emerson-narvaez-washed-geisha",
                "title": "Emerson Narvaez Washed Geisha",
                "variants": [{"available": True}],
            },
            {"handle": "brewing-equipment-kit", "title": "Brewing Equipment Kit", "variants": [{"available": True}]},
            {"handle": "tshirt", "title": "T-shirt", "variants": [{"available": True}]},
        ]

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://nord.coffee/collections/frontpage/products.json")
    assert urls == ["https://nord.coffee/products/emerson-narvaez-washed-geisha"]


def test_home_currency_pinned():
    scraper = _make_scraper()
    assert scraper.store_currency == "AUD"
    assert scraper._currency_detected is True
