"""Tests for the Central Coast Coffee scraper (Shopify JSON, no network)."""


from kissaten.scrapers.central_coast_coffee import CentralCoastCoffeeScraper
from kissaten.scrapers.registry import get_registry


def _make_scraper() -> CentralCoastCoffeeScraper:
    return CentralCoastCoffeeScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("central-coast-coffee")
    assert info is not None
    assert info.roaster_name == "Central Coast Coffee"
    assert info.currency == "AUD"
    assert info.country == "Australia"
    assert info.website == "https://centralcoastcoffee.com.au"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Central Coast Coffee"


def test_preprocess_product_url_strips_collection():
    scraper = _make_scraper()
    url = "https://centralcoastcoffee.com.au/collections/roasted-coffee-beans/products/coastal-blend"
    assert scraper.preprocess_product_url(url) == "https://centralcoastcoffee.com.au/products/coastal-blend"


async def test_extract_skips_excluded_handles(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return [
            {"handle": "coastal-blend", "title": "Coastal Blend", "variants": [{"available": True}]},
            {"handle": "monthly-subscription", "title": "Coffee Subscription", "variants": [{"available": True}]},
            {"handle": "fellow-stagg-kettle", "title": "Fellow Stagg Kettle", "variants": [{"available": True}]},
        ]

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(
        "https://centralcoastcoffee.com.au/collections/roasted-coffee-beans/products.json"
    )
    assert urls == ["https://centralcoastcoffee.com.au/products/coastal-blend"]


def test_home_currency_pinned():
    scraper = _make_scraper()
    assert scraper.store_currency == "AUD"
    assert scraper._currency_detected is True
