"""Unit tests for the SOLO Brewing scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.solo_brewing import SoloBrewingScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "solo_brewing_products.json"
PRODUCTS_JSON_URL = "https://solobrewing.pt/collections/all/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return SoloBrewingScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("solo-brewing")
    assert info is not None
    assert info.roaster_name == "Solo Brewing"
    assert info.currency == "EUR"
    assert info.country == "Portugal"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Solo Brewing"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://solobrewing.pt/products/") for u in urls)
    assert "https://solobrewing.pt/products/cherry-bomb" in urls
    assert "https://solobrewing.pt/products/caramuru-red-catuai-natural-brazil" in urls
    # Beans missing from the curated our-beans collection must be captured
    # via collections/all.
    assert "https://solobrewing.pt/products/balaycho-yirgacheff-ethiopia" in urls
    assert "https://solobrewing.pt/products/geisha-zeo-colombia-diego-bermudez" in urls
    assert "https://solobrewing.pt/products/oreti-tropical-sunrise-kenya-sl28" in urls


@pytest.mark.asyncio
async def test_fermentation_project_kit_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://solobrewing.pt/products/the-fermentation-project" in urls
    assert "https://solobrewing.pt/products/the-fermentation-project-bundle" in urls


@pytest.mark.asyncio
async def test_subscriptions_and_brew_gear_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("subscription" in u for u in urls)
    # Untyped brew gear and the gift card are filtered by exclude_slugs.
    for excluded in (
        "acaia-coaster",
        "evo-espresso-machine-cleaner",
        "cafetto-gc2",
        "kalita",
        "server-solo",
        "sibarist",
        "solo-gift-card",
        "aeropress-xl",
    ):
        assert f"https://solobrewing.pt/products/{excluded}" not in urls


@pytest.mark.asyncio
async def test_stock_status_keyed_by_canonical_url(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    url = "https://solobrewing.pt/products/the-fermentation-project"
    assert url in scraper._shopify_stock_status
    assert url in scraper._shopify_product_data


def test_home_currency_pinned(scraper):
    # EUR is SOLO Brewing's home market and the storefront does not convert
    # prices for the scraper's default headers, so detection stays dynamic.
    assert scraper.store_currency == "EUR"
    assert scraper._currency_detected is True
