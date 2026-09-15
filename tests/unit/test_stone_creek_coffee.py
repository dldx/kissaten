"""Unit tests for the Stone Creek Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.stone_creek_coffee import StoneCreekCoffeeScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "stone_creek_coffee_products.json"
PRODUCTS_JSON_URL = "https://www.stonecreekcoffee.com/collections/shop-all-coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return StoneCreekCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("stone-creek-coffee")
    assert info is not None
    assert info.roaster_name == "Stone Creek Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Stone Creek Coffee"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://www.stonecreekcoffee.com/products/") for u in urls)
    assert "https://www.stonecreekcoffee.com/products/boneshaker-colombia" in urls
    assert "https://www.stonecreekcoffee.com/products/cream-city" in urls


@pytest.mark.asyncio
async def test_fermentation_project_presale_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://www.stonecreekcoffee.com/products/the-fermentation-project" in urls


@pytest.mark.asyncio
async def test_pods_and_cold_brew_filter_packs_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("escape-pods" in u for u in urls)
    assert not any("filter-packs" in u for u in urls)


@pytest.mark.asyncio
async def test_calibration_kits_are_kept_for_review_flagging(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Multi-bag caffeine-calibration kits are coffee; flagged as tasting kits
    # downstream instead of excluded.
    assert "https://www.stonecreekcoffee.com/products/freak-finder-kit" in urls


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
