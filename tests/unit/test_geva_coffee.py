"""Unit tests for the Geva Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.geva_coffee import GevaCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "geva_coffee_products.json"
PRODUCTS_JSON_URL = "https://www.gevacoffee.com/collections/all/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return GevaCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("geva-coffee")
    assert info is not None
    assert info.roaster_name == "Geva Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Geva Coffee"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://www.gevacoffee.com/products/") for u in urls)
    assert "https://www.gevacoffee.com/products/brazilian-bold" in urls
    assert "https://www.gevacoffee.com/products/kenya-nguvu-aa" in urls


@pytest.mark.asyncio
async def test_fermentation_project_kit_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://www.gevacoffee.com/products/the-fermentation-project-kit" in urls


@pytest.mark.asyncio
async def test_cold_brew_beverages_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("cold-brew" in u for u in urls)
    assert not any("cubano-cold" in u for u in urls)


@pytest.mark.asyncio
async def test_non_coffee_product_types_are_skipped(scraper, mocker):
    products = _fixture_products() + [
        {"handle": "some-black-tea", "title": "Black Tea", "product_type": "Tea", "variants": []},
        {
            "handle": "some-espresso-machine",
            "title": "Espresso Machine",
            "product_type": "Espresso Machine",
            "variants": [],
        },
        {"handle": "no-type-item", "title": "Mystery Item", "variants": []},
    ]
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("some-black-tea" in u for u in urls)
    assert not any("some-espresso-machine" in u for u in urls)
    assert not any("no-type-item" in u for u in urls)


@pytest.mark.asyncio
async def test_sampler_is_kept_for_review_flagging(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Samplers/taster kits are flagged (is_tasting_kit) downstream, not excluded.
    assert "https://www.gevacoffee.com/products/holiday-sampler" in urls


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
