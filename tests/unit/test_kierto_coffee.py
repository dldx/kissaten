"""Tests for the Kierto Coffee scraper (Shopify JSON, no network)."""

from kissaten.scrapers.kierto_coffee import KiertoCoffeeScraper
from kissaten.scrapers.registry import get_registry


def _make_scraper() -> KiertoCoffeeScraper:
    return KiertoCoffeeScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("kierto-coffee")
    assert info is not None
    assert info.roaster_name == "Kierto Coffee"
    assert info.currency == "AUD"
    assert info.country == "Australia"
    assert info.website == "https://kierto.coffee"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Kierto Coffee"


def test_preprocess_product_url_strips_collection():
    scraper = _make_scraper()
    url = (
        "https://kierto.coffee/collections/coffee/products/"
        "costa-rica-canet-musician-series-beethoven-yellow-caturra-enzyme-washed"
    )
    assert scraper.preprocess_product_url(url) == (
        "https://kierto.coffee/products/costa-rica-canet-musician-series-beethoven-yellow-caturra-enzyme-washed"
    )


async def test_extract_skips_excluded_handles_and_duplicates(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return [
            {
                "handle": "costa-rica-canet-musician-series-beethoven-yellow-caturra-enzyme-washed",
                "title": "Costa Rica Canet Beethoven Yellow Caturra",
                "variants": [{"available": True}],
            },
            # Accidental Shopify admin duplicate ("-copy" handle) must be dropped
            {
                "handle": "ethiopia-alo-coffee-tri-up-sky-project-infinity-dark-room-washed-74158-copy",
                "title": "Ethiopia Alo Copy",
                "variants": [{"available": True}],
            },
            {"handle": "events-tshirt", "title": "T-shirt", "variants": [{"available": True}]},
        ]

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://kierto.coffee/collections/coffee/products.json")
    assert urls == [
        "https://kierto.coffee/products/costa-rica-canet-musician-series-beethoven-yellow-caturra-enzyme-washed"
    ]


def test_home_currency_pinned():
    scraper = _make_scraper()
    assert scraper.store_currency == "AUD"
    assert scraper._currency_detected is True
