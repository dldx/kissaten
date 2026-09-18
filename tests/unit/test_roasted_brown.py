"""Unit tests for the Roasted Brown scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.roasted_brown import RoastedBrownScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "roasted_brown_products.json"
PRODUCTS_JSON_URL = "https://www.roastedbrown.com/collections/all-coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return RoastedBrownScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("roasted-brown")
    assert info is not None
    assert info.roaster_name == "Roasted Brown"
    assert info.currency == "EUR"
    assert info.country == "Republic of Ireland"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Roasted Brown"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://www.roastedbrown.com/products/") for u in urls)
    assert "https://www.roastedbrown.com/products/huila" in urls
    assert "https://www.roastedbrown.com/products/the-lucky-sip" in urls


@pytest.mark.asyncio
async def test_fermentation_project_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # The Fermentation Project handle itself contains "cupping" — the exclude
    # slugs must be specific enough not to drop it.
    assert "https://www.roastedbrown.com/products/guatemala-the-fermentation-project-for-cupping-filter-brewing" in urls


@pytest.mark.asyncio
async def test_cupping_accessories_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("cupping-spoon" in u for u in urls)
    assert not any("cupping-bowl" in u for u in urls)


def test_base_class_cupping_url_filter_is_overridden(scraper):
    # The base filter drops any URL containing "cupping"; the Fermentation
    # Project coffee must pass through it regardless.
    ferment = "https://www.roastedbrown.com/products/guatemala-the-fermentation-project-for-cupping-filter-brewing"
    assert scraper.is_coffee_product_url(ferment) is True
    # Accessories still fall through to the base filter.
    assert scraper.is_coffee_product_url("https://www.roastedbrown.com/products/roasted-brown-cupping-spoon") is False


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "EUR"
    assert scraper._currency_detected is True
