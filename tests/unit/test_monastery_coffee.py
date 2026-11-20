"""Tests for the Monastery Coffee scraper (Shopify JSON, no network)."""

from kissaten.scrapers.monastery_coffee import MonasteryCoffeeScraper
from kissaten.scrapers.registry import get_registry


def _make_scraper() -> MonasteryCoffeeScraper:
    return MonasteryCoffeeScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("monastery-coffee")
    assert info is not None
    assert info.roaster_name == "Monastery Coffee"
    assert info.currency == "AUD"
    assert info.country == "Australia"
    assert info.website == "https://monasterycoffee.com.au"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Monastery Coffee"


def test_preprocess_product_url_strips_collection():
    scraper = _make_scraper()
    url = "https://monasterycoffee.com.au/collections/current-offerings/products/borbon-passiflora-semi-washed-colombia"
    assert (
        scraper.preprocess_product_url(url)
        == "https://monasterycoffee.com.au/products/borbon-passiflora-semi-washed-colombia"
    )


async def test_extract_skips_excluded_handles(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return [
            {
                "handle": "gedeb-wuri-washed-ethiopia",
                "title": "Gedeb Wuri Washed Ethiopia",
                "variants": [{"available": True}],
            },
            {"handle": "monthly-subscription", "title": "Coffee Subscription", "variants": [{"available": True}]},
            {"handle": "ethiopia-brewing-guide-book", "title": "Brewing Guide Book", "variants": [{"available": True}]},
        ]

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(
        "https://monasterycoffee.com.au/collections/current-offerings/products.json"
    )
    assert urls == ["https://monasterycoffee.com.au/products/gedeb-wuri-washed-ethiopia"]


def test_home_currency_pinned():
    scraper = _make_scraper()
    assert scraper.store_currency == "AUD"
    assert scraper._currency_detected is True
