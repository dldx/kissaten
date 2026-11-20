"""Tests for the Anamorphic Coffee scraper (Shopify JSON, no network)."""

from kissaten.scrapers.anamorphic_coffee import AnamorphicCoffeeScraper
from kissaten.scrapers.registry import get_registry


def _make_scraper() -> AnamorphicCoffeeScraper:
    return AnamorphicCoffeeScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("anamorphic-coffee")
    assert info is not None
    assert info.roaster_name == "Anamorphic Coffee"
    assert info.currency == "AUD"
    assert info.country == "Australia"
    assert info.website == "https://anamorphiccoffee.com"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Anamorphic Coffee"


def test_preprocess_product_url_strips_collection():
    scraper = _make_scraper()
    url = "https://anamorphiccoffee.com/collections/coffee/products/la-betania"
    assert scraper.preprocess_product_url(url) == "https://anamorphiccoffee.com/products/la-betania"


async def test_extract_skips_excluded_handles(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return [
            {"handle": "la-betania", "title": "La Betania Washed Colombia", "variants": [{"available": True}]},
            {"handle": "merch-tote-bag", "title": "Tote Bag", "variants": [{"available": True}]},
            {"handle": "gift-card", "title": "Gift Card", "variants": [{"available": True}]},
        ]

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(
        "https://anamorphiccoffee.com/collections/coffee/products.json"
    )
    assert urls == ["https://anamorphiccoffee.com/products/la-betania"]


def test_home_currency_pinned():
    scraper = _make_scraper()
    assert scraper.store_currency == "AUD"
    assert scraper._currency_detected is True
