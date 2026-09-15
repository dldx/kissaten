"""Unit tests for the Craft Decaf scraper (fixture-based, no network).

The fixture is a trimmed copy of the store's real products.json payload.
"""

import json
from pathlib import Path

from kissaten.scrapers.craft_decaf import CraftDecafScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://craftdecaf.com/collections/all-products/products.json"
EXPECTED_STORE_URLS = ["https://craftdecaf.com/collections/all-products/products.json"]


def _make_scraper() -> CraftDecafScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return CraftDecafScraper(api_key="test-api-key")


def _fixture_products() -> list[dict]:
    data = json.loads((FIXTURES / "craft_decaf_products.json").read_text())
    return data["products"]


async def _extract_urls(scraper, monkeypatch):
    products = _fixture_products()

    async def fake_fetch(products_json_url):
        return products

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    return await scraper._extract_product_urls_from_store(STORE_URL)


def test_registry_entry():
    info = get_registry().get_scraper_info("craft-decaf")
    assert info is not None
    assert info.name == "craft-decaf"
    assert info.roaster_name == "Craft Decaf"
    assert info.display_name == "Craft Decaf"
    assert info.currency == "GBP"
    assert info.country == "United Kingdom"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Craft Decaf"
    info = get_registry().get_scraper_info("craft-decaf")
    assert info is not None
    assert scraper.roaster_name == info.roaster_name


def test_store_currency_pinned():
    scraper = _make_scraper()
    assert scraper.store_currency == "GBP"
    assert scraper._currency_detected is True


async def test_store_urls():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == EXPECTED_STORE_URLS


async def test_extracts_canonical_product_urls(monkeypatch):
    scraper = _make_scraper()
    urls = await _extract_urls(scraper, monkeypatch)

    # Canonical no-collection URL form, matching the site's product sitemap.
    assert all(u.startswith("https://craftdecaf.com") and "/products/" in u for u in urls)
    assert not any("/collections/" in u for u in urls)

    # The two subscription products must be excluded; taster packs stay.
    assert "https://craftdecaf.com/products/popayan-colombia-decaf" in urls
    assert "https://craftdecaf.com/products/triple-taster-pack-10-off" in urls
    assert "https://craftdecaf.com/products/slomo-colombia-half-caf" in urls


async def test_postprocess_pins_currency():
    from kissaten.schemas import CoffeeBean

    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://craftdecaf.com/products/test-bean/",
        roaster="Craft Decaf",
        origins=[],
        price_options=[],
        currency="GBP",  # wrong on purpose; postprocess must overwrite
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out is not None
    assert out.currency == "GBP"


async def test_excludes_non_coffee_products(monkeypatch):
    scraper = _make_scraper()
    urls = await _extract_urls(scraper, monkeypatch)

    assert not any("decaf-coffee-subscription" in u for u in urls)
