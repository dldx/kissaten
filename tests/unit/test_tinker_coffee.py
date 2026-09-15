"""Unit tests for the Tinker Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.tinker_coffee import TinkerCoffeeScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "tinker_coffee_products.json"
PRODUCTS_JSON_URL = "https://www.tinkercoffee.com/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return TinkerCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("tinker-coffee")
    assert info is not None
    assert info.roaster_name == "Tinker Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Tinker Coffee"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://www.tinkercoffee.com/products/") for u in urls)
    assert "https://www.tinkercoffee.com/products/zing-blend" in urls
    assert "https://www.tinkercoffee.com/products/arc-blend" in urls


@pytest.mark.asyncio
async def test_subscriptions_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # coffee-subscription and coffee-subscription-secret-menu both match.
    assert not any("subscription" in u for u in urls)


@pytest.mark.asyncio
async def test_sample_packs_are_kept_for_review_flagging(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://www.tinkercoffee.com/products/adventurous-sample-pack" in urls


@pytest.mark.asyncio
async def test_layered_ferment_coffee_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://www.tinkercoffee.com/products/ethiopia-demeka-becha-layered-ferment" in urls


def test_base_class_advent_url_filter_is_overridden(scraper):
    # The base filter drops any URL containing "advent" (advent calendars);
    # Tinker's 'adventurous' line must pass through it regardless.
    assert scraper.is_coffee_product_url("https://www.tinkercoffee.com/products/adventurous-sample-pack") is True


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
