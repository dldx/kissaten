"""Unit tests for the Muttley & Jack's scraper (fixture-based, no network).

The fixture mirrors the live ``collections/all`` products.json: beans, the
James Hoffmann Fermentation Project box, tasting kits (smaklåda, seasonal
tasting box), plus gift memberships, coffee-experience subscription boxes,
gift cards, shipping, food and equipment items that must be excluded.
"""

import json
from pathlib import Path

from kissaten.scrapers.muttley_jacks import MuttleyJacksScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

PRODUCTS_JSON_URL = "https://muttleyandjacks.se/collections/all/products.json"


def _fixture_products() -> list[dict]:
    return json.loads((FIXTURES / "muttley_jacks_products.json").read_text())["products"]


def _make_scraper() -> MuttleyJacksScraper:
    return MuttleyJacksScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("muttley-jacks")
    assert info is not None
    assert info.roaster_name == "Muttley & Jack's Coffee Roasters"
    assert info.display_name == "Muttley & Jack's Coffee Roasters"
    assert info.currency == "SEK"
    assert info.country == "Sweden"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    info = get_registry().get_scraper_info("muttley-jacks")
    assert scraper.roaster_name == info.roaster_name


async def test_store_urls():
    scraper = _make_scraper()
    assert await scraper.get_store_urls() == [PRODUCTS_JSON_URL]


async def test_extracts_beans_keeps_tasting_kits_and_excludes_boxes(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return _fixture_products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # 6 kept: 4 beans + the Fermentation Project box + the smaklåda/seasonal
    # tasting kits (tasting kits are flagged downstream, never dropped);
    # memberships, boxes, gift cards, shipping, food and equipment dropped.
    assert len(urls) == 6
    assert "https://muttleyandjacks.se/products/the-fermentation-project-with-james-hoffmann-and-lucia-solis" in urls
    assert "https://muttleyandjacks.se/products/smaklada" in urls
    assert "https://muttleyandjacks.se/products/seasonal-tasting-box" in urls
    assert "https://muttleyandjacks.se/products/kenya-mitondo-aa" in urls
    assert not any("gavomedlemskap" in u for u in urls)
    assert not any("adventure" in u for u in urls)
    assert not any("gift-card" in u or "500-kr" in u for u in urls)
    assert not any("sverige-frakt" in u for u in urls)
    assert not any("hario" in u for u in urls)
    assert not any("sallader" in u for u in urls)
    assert not any("passport" in u or "voyage" in u for u in urls)


async def test_canonicalizes_to_no_collection_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return [_fixture_products()[1]]

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert urls == ["https://muttleyandjacks.se/products/kenya-mitondo-aa"]
