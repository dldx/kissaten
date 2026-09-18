"""Unit tests for the Moongoat scraper (fixture-based, no network).

The fixture mirrors the live ``collections/all`` products.json: the James
Hoffmann Fermentation Project set (``fermentationproject`` tag, empty
product_type), Coffee-typed beans, a roasting error (hojicha classified as
"Coffee"), ready-to-drink cold brew, and matcha/gift/subscription/Aeropress
items that carry an empty product_type.

Covered per-scraper behaviour:
- product_type=="Coffee" OR "fermentationproject" tag keeps only beans + kit.
- Shopify Markets geo-conversion defence: country=US pinned on every listing
  request, USD forced with ``_currency_detected=True``.
"""

import json
from pathlib import Path

from kissaten.scrapers.moongoat import MoongoatScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

PRODUCTS_JSON_URL = "https://moongoat.com/collections/all/products.json"


def _fixture_products() -> list[dict]:
    return json.loads((FIXTURES / "moongoat_products.json").read_text())["products"]


def _make_scraper() -> MoongoatScraper:
    return MoongoatScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("moongoat")
    assert info is not None
    assert info.roaster_name == "Moongoat"
    assert info.display_name == "Moongoat"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    info = get_registry().get_scraper_info("moongoat")
    assert scraper.roaster_name == info.roaster_name


async def test_store_urls():
    scraper = _make_scraper()
    assert await scraper.get_store_urls() == [PRODUCTS_JSON_URL]


async def test_type_and_tag_filter_keeps_beans_and_kit(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return _fixture_products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # 4 kept: 3 Coffee-typed beans + the fermentation kit via its
    # "fermentationproject" tag; hojicha/rotating cold brew excluded by slug,
    # everything else by empty product_type.
    assert len(urls) == 4
    assert "https://moongoat.com/products/james-hoffmann-fermentation-project-set-moongoat-coffee" in urls
    assert "https://moongoat.com/products/dark-side-of-the-moongoat" in urls
    assert "https://moongoat.com/products/pillow-pack-decaf" in urls
    assert not any("hojicha" in u for u in urls)
    assert not any("rotating-cold-brew" in u for u in urls)
    assert not any("matcha" in u for u in urls)
    assert not any("gift-card" in u for u in urls)
    assert not any("subscription" in u for u in urls)
    assert not any("aeropress" in u for u in urls)


async def test_usd_pinned_and_detected():
    scraper = _make_scraper()
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True


def test_postprocess_forces_usd():
    from kissaten.schemas import CoffeeBean

    scraper = _make_scraper()
    bean = CoffeeBean(
        name="DarkSide of the MoonGoat",
        roaster="Moongoat",
        url="https://moongoat.com/products/dark-side-of-the-moongoat",
        origins=[],
        price_options=[],
        currency="EUR",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out is not None
    assert out.currency == "USD"


async def test_listing_requests_pin_us_market(mocker):
    scraper = _make_scraper()
    recorded_urls = []

    async def fake_escalation(url: str):
        recorded_urls.append(url)
        return {"products": []}, False

    mocker.patch.object(scraper, "_fetch_page_with_escalation", side_effect=fake_escalation)

    await scraper._fetch_all_shopify_products(PRODUCTS_JSON_URL)

    assert recorded_urls == [f"{PRODUCTS_JSON_URL}?country=US&limit=250&page=1"]


async def test_canonicalizes_to_no_collection_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return [_fixture_products()[1]]

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert urls == ["https://moongoat.com/products/dark-side-of-the-moongoat"]
