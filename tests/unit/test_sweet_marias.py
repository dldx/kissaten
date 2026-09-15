"""Unit tests for the Sweet Maria's scraper (fixture-based, no network).

Kissaten does not track green (unroasted) beans, so the scraper intentionally
targets only Sweet Maria's ``roasted-coffee`` collection. The fixture is a
trimmed copy of that collection's real ``products.json`` payload.
"""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.sweet_marias import SweetMariasScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "sweet_marias_products.json"
ROASTED_COFFEE_URL = "https://www.sweetmarias.com/collections/roasted-coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return SweetMariasScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("sweet-marias")
    assert info is not None
    assert info.roaster_name == "Sweet Maria's"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Sweet Maria's"


async def test_store_urls_target_roasted_coffee_only(scraper):
    urls = await scraper.get_store_urls()
    assert urls == [ROASTED_COFFEE_URL]
    # The green-coffee catalogue and the green blends must not be scraped.
    assert not any("green-coffee" in u for u in urls)
    assert not any("blends" in u for u in urls)


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(ROASTED_COFFEE_URL)

    assert all(u.startswith("https://www.sweetmarias.com/products/") for u in urls)
    assert "https://www.sweetmarias.com/products/roasted-coffee-ethiopia-organic-buture-cooperative-8704" in urls


@pytest.mark.asyncio
async def test_no_green_beans_in_fixture_scope(scraper, mocker):
    # The roasted-coffee collection carries product_type "Roasted Coffee";
    # nothing green may leak into the URL set.
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(ROASTED_COFFEE_URL)

    assert not any("green" in u for u in urls)


@pytest.mark.asyncio
async def test_roasted_subscription_is_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(ROASTED_COFFEE_URL)

    assert not any("rstd-subs" in u for u in urls)


@pytest.mark.asyncio
async def test_overlapping_collections_dedup(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    combined = await scraper.discover_all_product_urls()

    assert len(combined) == len(set(combined))
    # 5 fixture products minus the excluded rstd-subs subscription.
    assert len(combined) == 4


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
