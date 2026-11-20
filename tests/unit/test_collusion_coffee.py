"""Tests for the Collusion Coffee scraper (Shopify JSON, no network)."""

from kissaten.scrapers.collusion_coffee import CollusionCoffeeScraper
from kissaten.scrapers.registry import get_registry


def _make_scraper() -> CollusionCoffeeScraper:
    return CollusionCoffeeScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("collusion-coffee")
    assert info is not None
    assert info.roaster_name == "Collusion Coffee"
    assert info.currency == "AUD"
    assert info.country == "Australia"
    assert info.website == "https://collusioncoffee.com"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Collusion Coffee"


def test_preprocess_product_url_strips_collection():
    scraper = _make_scraper()
    url = "https://collusioncoffee.com/collections/coffee/products/filter-colombia-adriana-gonzalez-washed-pink-bourbon"
    assert scraper.preprocess_product_url(url) == (
        "https://collusioncoffee.com/products/filter-colombia-adriana-gonzalez-washed-pink-bourbon"
    )


async def test_extract_skips_excluded_handles_and_duplicates(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return [
            {
                "handle": "filter-colombia-adriana-gonzalez-washed-pink-bourbon",
                "title": "Filter Colombia Adriana Gonzalez Washed Pink Bourbon",
                "variants": [{"available": True}],
            },
            # Accidental Shopify admin duplicate ("-copy" handle) must be dropped
            {
                "handle": "filter-ethiopia-mensur-abahika-washed-g2-jarc-74110-copy",
                "title": "Filter Ethiopia Copy",
                "variants": [{"available": True}],
            },
            {"handle": "merch-tote", "title": "Tote Bag", "variants": [{"available": True}]},
            {
                "handle": "espresso-roast-subscription",
                "title": "Espresso Roast Subscription",
                "variants": [{"available": True}],
            },
        ]

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(
        "https://collusioncoffee.com/collections/coffee/products.json"
    )
    assert urls == ["https://collusioncoffee.com/products/filter-colombia-adriana-gonzalez-washed-pink-bourbon"]


def test_home_currency_pinned():
    scraper = _make_scraper()
    assert scraper.store_currency == "AUD"
    assert scraper._currency_detected is True
