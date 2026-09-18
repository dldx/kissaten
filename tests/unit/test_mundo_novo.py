"""Unit tests for the Mundo Novo Coffee scraper (fixture-based, no network).

The fixture is a trimmed copy of the live ``collections/cafe`` products.json
(4 bean products incl. the Fermentation Project pack + the subscription).
"""

import json
from pathlib import Path

from kissaten.scrapers.mundo_novo import MundoNovoScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

PRODUCTS_JSON_URL = "https://mundonovocoffee.com/collections/cafe/products.json"


def _fixture_products() -> list[dict]:
    return json.loads((FIXTURES / "mundo_novo_products.json").read_text())["products"]


def _make_scraper() -> MundoNovoScraper:
    return MundoNovoScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("mundo-novo")
    assert info is not None
    assert info.roaster_name == "Mundo Novo Coffee"
    assert info.display_name == "Mundo Novo Coffee"
    assert info.currency == "EUR"
    assert info.country == "Spain"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    info = get_registry().get_scraper_info("mundo-novo")
    assert scraper.roaster_name == info.roaster_name


async def test_store_urls():
    scraper = _make_scraper()
    assert await scraper.get_store_urls() == [PRODUCTS_JSON_URL]


async def test_extracts_beans_and_excludes_subscription(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return _fixture_products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # 4 beans kept (incl. the Fermentation Project pack), subscription dropped.
    assert len(urls) == 4
    assert "https://mundonovocoffee.com/products/the-fermentation-profect-pack" in urls
    assert "https://mundonovocoffee.com/products/bolivia-asocafe" in urls
    assert not any("suscripcion" in u for u in urls)


async def test_canonicalizes_to_no_collection_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return [_fixture_products()[0]]

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert urls == ["https://mundonovocoffee.com/products/the-fermentation-profect-pack"]
