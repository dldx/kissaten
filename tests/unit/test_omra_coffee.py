"""Unit tests for the Ómra Coffee scraper (fixture-based, no network).

The fixture mirrors the live ``collections/coffee`` products.json (7 products,
all coffee incl. the James Hoffmann Fermentation Project tasting set).

Covered per-scraper behaviour:
- GBP currency pinned with ``_currency_detected=True`` (Shopify Markets
  geo-converts datacenter requests to EUR without the country=GB param).
- country=GB appended to every listing request.
- Product URLs canonicalized to ``/products/<handle>``.
"""

import json
from pathlib import Path

from kissaten.scrapers.omra_coffee import OmraCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

PRODUCTS_JSON_URL = "https://omra.coffee/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads((FIXTURES / "omra_coffee_products.json").read_text())["products"]


def _make_scraper() -> OmraCoffeeScraper:
    return OmraCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("omra-coffee")
    assert info is not None
    assert info.roaster_name == "Ómra Coffee"
    assert info.display_name == "Ómra Coffee"
    assert info.currency == "GBP"
    assert info.country == "United Kingdom"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    info = get_registry().get_scraper_info("omra-coffee")
    assert scraper.roaster_name == info.roaster_name


async def test_store_urls():
    scraper = _make_scraper()
    assert await scraper.get_store_urls() == [PRODUCTS_JSON_URL]


async def test_extracts_all_coffee_products(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return _fixture_products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # The curated collection is all-coffee: nothing is dropped.
    assert len(urls) == 7
    assert "https://omra.coffee/products/james-hoffmann-fermentation-project-coffee-tasting-set" in urls
    assert "https://omra.coffee/products/los-alpes" in urls


async def test_gbp_pinned_and_detected():
    scraper = _make_scraper()
    assert scraper.store_currency == "GBP"
    assert scraper._currency_detected is True


def test_postprocess_forces_gbp():
    from kissaten.schemas import CoffeeBean

    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Los Alpes",
        roaster="Ómra Coffee",
        url="https://omra.coffee/products/los-alpes",
        origins=[],
        price_options=[],
        currency="EUR",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out is not None
    assert out.currency == "GBP"


async def test_listing_requests_pin_gb_market(mocker):
    scraper = _make_scraper()
    recorded_urls = []

    async def fake_escalation(url: str):
        recorded_urls.append(url)
        return {"products": []}, False

    mocker.patch.object(scraper, "_fetch_page_with_escalation", side_effect=fake_escalation)

    await scraper._fetch_all_shopify_products(PRODUCTS_JSON_URL)

    assert recorded_urls == [f"{PRODUCTS_JSON_URL}?country=GB&limit=250&page=1"]


async def test_canonicalizes_to_no_collection_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return [_fixture_products()[1]]

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert urls == ["https://omra.coffee/products/los-alpes"]
