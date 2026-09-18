"""Unit tests for the Kafina scraper (fixture-based, no network).

The fixture is a trimmed copy of the store's real products.json payload.
"""

import json
from pathlib import Path

from kissaten.scrapers.kafina import KafinaScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://kafinacoffee.fr/collections/produits-dispoibles/products.json"
EXPECTED_STORE_URLS = ["https://kafinacoffee.fr/collections/produits-dispoibles/products.json"]


def _make_scraper() -> KafinaScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return KafinaScraper(api_key="test-api-key")


def _fixture_products() -> list[dict]:
    data = json.loads((FIXTURES / "kafina_products.json").read_text())
    return data["products"]


async def _extract_urls(scraper, monkeypatch):
    products = _fixture_products()

    async def fake_fetch(products_json_url):
        return products

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    return await scraper._extract_product_urls_from_store(STORE_URL)


def test_registry_entry():
    info = get_registry().get_scraper_info("kafina")
    assert info is not None
    assert info.name == "kafina"
    assert info.roaster_name == "Kafina"
    assert info.display_name == "Kafina"
    assert info.currency == "EUR"
    assert info.country == "France"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Kafina"
    info = get_registry().get_scraper_info("kafina")
    assert info is not None
    assert scraper.roaster_name == info.roaster_name


def test_store_currency_pinned():
    scraper = _make_scraper()
    assert scraper.store_currency == "EUR"
    assert scraper._currency_detected is True


async def test_store_urls():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == EXPECTED_STORE_URLS


async def test_extracts_canonical_product_urls(monkeypatch):
    scraper = _make_scraper()
    urls = await _extract_urls(scraper, monkeypatch)

    # Canonical no-collection URL form, matching the site's product sitemap.
    assert all(u.startswith("https://kafinacoffee.fr") and "/products/" in u for u in urls)
    assert not any("/collections/" in u for u in urls)

    # The drip-bag product is excluded.
    assert "https://kafinacoffee.fr/products/fermentation-project-by-james-hoffmann" in urls
    assert "https://kafinacoffee.fr/products/perou-pichanaki-silvania" in urls


async def test_postprocess_pins_currency():
    from kissaten.schemas import CoffeeBean

    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://kafinacoffee.fr/products/test-bean/",
        roaster="Kafina",
        origins=[],
        price_options=[],
        currency="GBP",  # wrong on purpose; postprocess must overwrite
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out is not None
    assert out.currency == "EUR"


async def test_excludes_non_coffee_products(monkeypatch):
    scraper = _make_scraper()
    urls = await _extract_urls(scraper, monkeypatch)

    assert not any("capsulas-para-casa" in u for u in urls)
