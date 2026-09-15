"""Unit tests for the Higher Grounds scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.higher_grounds import HigherGroundsScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "higher_grounds_products.json"
PRODUCTS_JSON_URL = "https://www.highergroundstrading.com/collections/all-coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return HigherGroundsScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("higher-grounds")
    assert info is not None
    assert info.roaster_name == "Higher Grounds"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Higher Grounds"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://www.highergroundstrading.com/products/") for u in urls)
    assert "https://www.highergroundstrading.com/products/justice" in urls
    assert "https://www.highergroundstrading.com/products/funky-mamacita" in urls


@pytest.mark.asyncio
async def test_fermentation_project_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://www.highergroundstrading.com/products/fermentation-project" in urls


@pytest.mark.asyncio
async def test_subscriptions_and_donations_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("subscription" in u for u in urls)
    assert not any("donate-a-bag" in u for u in urls)


@pytest.mark.asyncio
async def test_sampler_is_kept_for_review_flagging(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://www.highergroundstrading.com/products/coffee-trio-sampler-gift-sets" in urls


@pytest.mark.asyncio
async def test_stock_status_keyed_by_canonical_url(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    url = "https://www.highergroundstrading.com/products/fermentation-project"
    assert url in scraper._shopify_stock_status
    assert url in scraper._shopify_product_data


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
