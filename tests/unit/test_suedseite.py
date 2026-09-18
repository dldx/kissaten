"""Unit tests for the Suedseite scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.suedseite import SuedseiteScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "suedseite_products.json"
PRODUCTS_JSON_URL = "https://suedseite.coffee/collections/alle-bohnen/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return SuedseiteScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("suedseite")
    assert info is not None
    assert info.roaster_name == "Suedseite"
    assert info.currency == "EUR"
    assert info.country == "Germany"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Suedseite"


@pytest.mark.asyncio
async def test_extracts_collection_prefixed_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Suedseite's own collection pages link with the collection segment.
    assert all(u.startswith("https://suedseite.coffee/collections/alle-bohnen/products/") for u in urls)
    assert "https://suedseite.coffee/collections/alle-bohnen/products/kibirigwi-kenya" in urls
    assert "https://suedseite.coffee/collections/alle-bohnen/products/goro-badesa-ethiopia-washed" in urls


@pytest.mark.asyncio
async def test_fermentation_project_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert (
        "https://suedseite.coffee/collections/alle-bohnen/products/"
        "the-fermentation-project-james-hoffmann-lucia-solis-guatemala" in urls
    )


@pytest.mark.asyncio
async def test_subscription_abo_is_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # best-of-sudseite-abo is the "Best of Suedseite" coffee subscription.
    assert not any("abo" in u for u in urls)


@pytest.mark.asyncio
async def test_stock_status_keyed_by_collection_url(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    url = (
        "https://suedseite.coffee/collections/alle-bohnen/products/"
        "the-fermentation-project-james-hoffmann-lucia-solis-guatemala"
    )
    assert url in scraper._shopify_stock_status
    assert url in scraper._shopify_product_data


def test_home_currency_not_pinned(scraper):
    # EUR is Suedseite's home market and the storefront does not convert
    # prices for the scraper's default headers, so detection stays dynamic.
    assert scraper.store_currency == "EUR"
    assert scraper._currency_detected is False
