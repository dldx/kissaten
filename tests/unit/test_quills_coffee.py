"""Unit tests for the Quills Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.quills_coffee import QuillsCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "quills_coffee_products.json"
PRODUCTS_JSON_URL = "https://quillscoffee.com/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return QuillsCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("quills-coffee")
    assert info is not None
    assert info.roaster_name == "Quills Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Quills Coffee"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Quills' canonical URLs are on the apex domain (no www), no collection.
    assert all(u.startswith("https://quillscoffee.com/products/") for u in urls)
    assert "https://quillscoffee.com/products/inkwell-house-blend" in urls
    assert "https://quillscoffee.com/products/ethiopia-bombe" in urls


@pytest.mark.asyncio
async def test_fermentation_project_tasting_set_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://quillscoffee.com/products/james-hoffmann-fermentation-project-tasting-set" in urls


@pytest.mark.asyncio
async def test_cold_brew_blend_beans_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Southern Gothic is a cold brew *blend* sold as beans — not an RTD product.
    assert "https://quillscoffee.com/products/southern-gothic-12oz" in urls


@pytest.mark.asyncio
async def test_stock_status_keyed_by_canonical_url(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    url = "https://quillscoffee.com/products/james-hoffmann-fermentation-project-tasting-set"
    assert url in scraper._shopify_stock_status
    assert url in scraper._shopify_product_data


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
