"""Unit tests for the Micrology Coffee Roasters scraper (fixture-based, no network).

The fixture is a trimmed copy of the live ``collections/coffee-beans``
products.json (5 bean products incl. the roasters-pick sampler pack +
gift subscription / gift card items).
"""

import json
from pathlib import Path

from kissaten.scrapers.micrology import MicrologyScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

PRODUCTS_JSON_URL = "https://micrology.com.au/collections/coffee-beans/products.json"


def _fixture_products() -> list[dict]:
    return json.loads((FIXTURES / "micrology_products.json").read_text())["products"]


def _make_scraper() -> MicrologyScraper:
    return MicrologyScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("micrology")
    assert info is not None
    assert info.roaster_name == "Micrology Coffee Roasters"
    assert info.display_name == "Micrology Coffee Roasters"
    assert info.currency == "AUD"
    assert info.country == "Australia"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    info = get_registry().get_scraper_info("micrology")
    assert scraper.roaster_name == info.roaster_name


async def test_store_urls():
    scraper = _make_scraper()
    assert await scraper.get_store_urls() == [PRODUCTS_JSON_URL]


async def test_extracts_beans_keeps_sampler_and_excludes_subscriptions(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return _fixture_products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # 5 bean products kept (incl. the sampler pack, which must NOT be dropped —
    # it is flagged as a tasting kit downstream); subscriptions and gift cards
    # dropped.
    assert len(urls) == 5
    assert "https://micrology.com.au/products/sample-pack-roasters-pick-espresso" in urls
    assert "https://micrology.com.au/products/blue-note" in urls
    assert not any("subscription" in u for u in urls)
    assert not any("gift-card" in u for u in urls)


async def test_canonicalizes_to_no_collection_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return [_fixture_products()[0]]

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert urls == ["https://micrology.com.au/products/blue-note"]
