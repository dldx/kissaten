"""Tests for the Brew Methods scraper (Shopify JSON, no network)."""

from kissaten.scrapers.brew_methods import BrewMethodsScraper
from kissaten.scrapers.registry import get_registry


def _make_scraper() -> BrewMethodsScraper:
    return BrewMethodsScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("brew-methods")
    assert info is not None
    assert info.roaster_name == "Brew Methods"
    assert info.currency == "AUD"
    assert info.country == "Australia"
    assert info.website == "https://brewmethods.com.au"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Brew Methods"


def test_preprocess_product_url_strips_collection():
    scraper = _make_scraper()
    url = "https://brewmethods.com.au/collections/coffee/products/hinata-seasonal-blend"
    assert scraper.preprocess_product_url(url) == "https://brewmethods.com.au/products/hinata-seasonal-blend"


async def test_extract_skips_excluded_handles(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return [
            {"handle": "hinata-seasonal-blend", "title": "Hinata Seasonal Blend", "variants": [{"available": True}]},
            {"handle": "fellow-ode-grinder", "title": "Fellow Ode Grinder", "variants": [{"available": True}]},
            {"handle": "coffee-subscription", "title": "Coffee Subscription", "variants": [{"available": True}]},
        ]

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://brewmethods.com.au/collections/coffee/products.json")
    assert urls == ["https://brewmethods.com.au/products/hinata-seasonal-blend"]


def test_home_currency_pinned():
    scraper = _make_scraper()
    assert scraper.store_currency == "AUD"
    assert scraper._currency_detected is True
