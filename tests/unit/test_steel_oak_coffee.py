"""Unit tests for the Steel Oak Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.steel_oak_coffee import SteelOakCoffeeScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "steel_oak_coffee_products.json"
PRODUCTS_JSON_URL = "https://steeloakcoffee.com/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return SteelOakCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("steel-oak-coffee")
    assert info is not None
    assert info.roaster_name == "Steel Oak Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Steel Oak Coffee"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://steeloakcoffee.com/products/") for u in urls)
    assert "https://steeloakcoffee.com/products/galeras" in urls
    assert "https://steeloakcoffee.com/products/colombia-cadefihuila" in urls


@pytest.mark.asyncio
async def test_fermentation_project_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://steeloakcoffee.com/products/james-hoffmann-fermentation-project" in urls


@pytest.mark.asyncio
async def test_subscriptions_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("subscription" in u for u in urls)


@pytest.mark.asyncio
async def test_stock_status_keyed_by_canonical_url(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    url = "https://steeloakcoffee.com/products/james-hoffmann-fermentation-project"
    assert url in scraper._shopify_stock_status
    assert url in scraper._shopify_product_data


def test_home_currency_pinned(scraper):
    # Steel Oak's storefront converts prices to EUR for clients sending an
    # Accept-Language header; the US market is pinned via country=US.
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True


@pytest.mark.asyncio
async def test_market_param_appended_to_listing_requests(scraper, mocker):
    captured: list[str] = []

    async def fake_fetch(url):
        captured.append(url)
        return {"products": _fixture_products()}, False

    mocker.patch.object(scraper, "_fetch_page_with_escalation", side_effect=fake_fetch)

    await scraper._fetch_all_shopify_products(PRODUCTS_JSON_URL)

    assert captured == [f"{PRODUCTS_JSON_URL}?country=US&limit=250&page=1"]
