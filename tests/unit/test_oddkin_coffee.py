"""Unit tests for the Oddkin Coffee scraper (fixture-based, no network).

The fixture is a trimmed merge of the three collections the scraper fetches
(``speciality-coffee``, ``decaf`` and ``hoffman`` — the Fermentation Project
bundles live only in the latter).
"""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.oddkin_coffee import OddkinCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "oddkin_coffee_products.json"
SPECIALITY_URL = "https://www.oddkincoffee.com/collections/speciality-coffee/products.json"
DECAF_URL = "https://www.oddkincoffee.com/collections/decaf/products.json"
HOFFMAN_URL = "https://www.oddkincoffee.com/collections/hoffman/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return OddkinCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("oddkin-coffee")
    assert info is not None
    assert info.roaster_name == "Oddkin Coffee"
    assert info.currency == "GBP"
    assert info.country == "United Kingdom"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Oddkin Coffee"


async def test_store_urls_cover_all_three_collections(scraper):
    urls = await scraper.get_store_urls()
    assert SPECIALITY_URL in urls
    assert DECAF_URL in urls
    assert HOFFMAN_URL in urls


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(SPECIALITY_URL)

    assert all(u.startswith("https://www.oddkincoffee.com/products/") for u in urls)
    assert "https://www.oddkincoffee.com/products/popayan-colombia" in urls
    assert "https://www.oddkincoffee.com/products/jazzhouse-blend" in urls


@pytest.mark.asyncio
async def test_fermentation_project_bundles_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(HOFFMAN_URL)

    assert "https://www.oddkincoffee.com/products/the-fermentation-project-basic-bundle" in urls
    assert "https://www.oddkincoffee.com/products/the-fermentation-project-cuppers-bundle" in urls
    assert "https://www.oddkincoffee.com/products/the-fermentation-project-jazzy-bundle" in urls
    assert "https://www.oddkincoffee.com/products/the-fermentation-project-i-heart-fermentation-bundle" in urls


@pytest.mark.asyncio
async def test_taster_and_sample_packs_are_kept_for_review_flagging(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(SPECIALITY_URL)

    assert "https://www.oddkincoffee.com/products/coffee-taster-pack" in urls
    assert "https://www.oddkincoffee.com/products/house-bundle" in urls


@pytest.mark.asyncio
async def test_overlapping_collections_dedup(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    combined = await scraper.discover_all_product_urls()

    # The decaf collection overlaps speciality-coffee; canonical /products/
    # URLs collapse the duplicates so the union is unique.
    assert len(combined) == len(set(combined))
    assert len(combined) == 10


def test_home_currency_not_pinned(scraper):
    assert scraper.store_currency == "GBP"
    assert scraper._currency_detected is False
