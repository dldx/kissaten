"""Unit tests for the Kings Arms Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.kings_arms_coffee import KingsArmsCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "kings_arms_coffee_products.json"
PRODUCTS_JSON_URL = "https://kingsarmscoffee.com/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return KingsArmsCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("kings-arms-coffee")
    assert info is not None
    assert info.roaster_name == "Kings Arms Coffee"
    assert info.display_name == "Kings Arms Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    # Brand styles itself "Kings Arms" (no apostrophe).
    assert scraper.roaster_name == "Kings Arms Coffee"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Collection segment must be stripped: the site links to /products/<handle>.
    assert all(u.startswith("https://kingsarmscoffee.com/products/") for u in urls)
    assert "https://kingsarmscoffee.com/products/colombia-jairo-arcila-strawberry-co-fermentation" in urls
    assert "https://kingsarmscoffee.com/products/bayshore-blend" in urls


@pytest.mark.asyncio
async def test_gift_card_is_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("gift-card" in u for u in urls)


@pytest.mark.asyncio
async def test_coferments_and_decaf_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://kingsarmscoffee.com/products/colombia-sebastian-ramirez-red-fruit-co-fermentation" in urls
    assert "https://kingsarmscoffee.com/products/colombia-ea-decaf" in urls


@pytest.mark.asyncio
async def test_stock_status_parsed(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert scraper._shopify_stock_status["https://kingsarmscoffee.com/products/bayshore-blend"] is True


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True


@pytest.mark.asyncio
async def test_us_market_param_appended(scraper, mocker):
    # Markets filtering by egress geography hides limited lots; the override
    # must pin the US home market on every page fetch.
    fetch = mocker.patch.object(
        scraper,
        "_fetch_page_with_escalation",
        side_effect=[({"products": []}, False)],
    )

    products = await scraper._fetch_all_shopify_products(PRODUCTS_JSON_URL)

    assert products == []
    called_url = fetch.call_args.args[0]
    assert called_url == f"{PRODUCTS_JSON_URL}?country=US&limit=250&page=1"
