"""Unit tests for the Ceto scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.ceto import CetoScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "ceto_products.json"
PRODUCTS_JSON_URL = "https://ceto.coffee/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return CetoScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("ceto")
    assert info is not None
    assert info.roaster_name == "Ceto"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Ceto"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://ceto.coffee/products/") for u in urls)
    assert "https://ceto.coffee/products/luz-helena-gesha-dark-roast" in urls
    assert "https://ceto.coffee/products/el-salvador-divina-natural" in urls


@pytest.mark.asyncio
async def test_mystery_coffee_league_one_off_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # One-off Mystery Coffee League releases are real coffees, not subscriptions.
    assert "https://ceto.coffee/products/mystery-coffee-league-1" in urls


@pytest.mark.asyncio
async def test_subscriptions_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("subscription" in u for u in urls)


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
