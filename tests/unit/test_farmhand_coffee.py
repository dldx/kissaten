"""Unit tests for the Farmhand Coffee scraper (fixture-based, no network).

The fixture is a trimmed merge of the two curated collections the scraper
fetches (``filter-coffee-beans`` and ``esspresso-coffee-beans-ground``).
"""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.farmhand_coffee import FarmhandCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "farmhand_coffee_products.json"
FILTER_URL = "https://www.farmhandcoffee.ie/collections/filter-coffee-beans/products.json"
ESPRESSO_URL = "https://www.farmhandcoffee.ie/collections/esspresso-coffee-beans-ground/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return FarmhandCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("farmhand-coffee")
    assert info is not None
    assert info.roaster_name == "Farmhand Coffee"
    assert info.currency == "EUR"
    assert info.country == "Republic of Ireland"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Farmhand Coffee"


async def test_store_urls_cover_both_collections(scraper):
    urls = await scraper.get_store_urls()
    assert FILTER_URL in urls
    assert ESPRESSO_URL in urls


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(FILTER_URL)

    assert all(u.startswith("https://www.farmhandcoffee.ie/products/") for u in urls)
    assert "https://www.farmhandcoffee.ie/products/filter-kenya-karimikui" in urls
    assert "https://www.farmhandcoffee.ie/products/signature-espresso-blend-colombia-brazil" in urls


@pytest.mark.asyncio
async def test_fermentation_project_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(FILTER_URL)

    assert "https://www.farmhandcoffee.ie/products/the-fermentation-project-with-james-hoffmann-lucia-solis" in urls


@pytest.mark.asyncio
async def test_cold_brew_bags_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(FILTER_URL)

    assert not any("cold-brew-bags" in u for u in urls)


@pytest.mark.asyncio
async def test_overlapping_collections_dedup(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    combined = await scraper.discover_all_product_urls()

    # Both collection fetches return the same canonical /products/<handle>
    # URLs, so the union is unique and no URL appears twice.
    assert len(combined) == len(set(combined))
    assert len(combined) == 5


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "EUR"
    assert scraper._currency_detected is True
