"""Unit tests for the Onoma Kaffee scraper (fixture-based, no network).

The fixture mirrors the live ``collections/kaffee`` products.json: 5 bean
products (incl. the Fermentation Project set and the probierpaket sampler) plus
gift card / Aeropress / barista course items from ``all`` that must be excluded.
"""

import json
from pathlib import Path

from kissaten.scrapers.onoma_kaffee import OnomaKaffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

PRODUCTS_JSON_URL = "https://onoma.coffee/collections/kaffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads((FIXTURES / "onoma_kaffee_products.json").read_text())["products"]


def _make_scraper() -> OnomaKaffeeScraper:
    return OnomaKaffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("onoma-kaffee")
    assert info is not None
    assert info.roaster_name == "Onoma Kaffee"
    assert info.display_name == "Onoma Kaffee"
    assert info.currency == "EUR"
    assert info.country == "Germany"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    info = get_registry().get_scraper_info("onoma-kaffee")
    assert scraper.roaster_name == info.roaster_name


async def test_store_urls():
    scraper = _make_scraper()
    assert await scraper.get_store_urls() == [PRODUCTS_JSON_URL]


async def test_extracts_beans_keeps_sampler_and_excludes_non_coffee(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return _fixture_products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # 5 kept: beans + the Fermentation Project set + the probierpaket sampler
    # (samplers are flagged downstream, never dropped); gift card, Aeropress
    # and barista course dropped.
    assert len(urls) == 5
    assert "https://onoma.coffee/products/fermentation-project-set-4-kaffees-je-50g" in urls
    assert "https://onoma.coffee/products/probierpaket" in urls
    assert "https://onoma.coffee/products/holm" in urls
    assert not any("gift-card" in u for u in urls)
    assert not any("aeropress" in u for u in urls)
    assert not any("kurs" in u for u in urls)


async def test_canonicalizes_to_no_collection_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return [_fixture_products()[1]]

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert urls == ["https://onoma.coffee/products/holm"]
