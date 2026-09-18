"""Unit tests for the Brandywine scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.brandywine_coffee_roasters import BrandywineCoffeeRoastersScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "brandywine_coffee_roasters_products.json"
PRODUCTS_JSON_URL = "https://www.brandywinecoffeeroasters.com/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return BrandywineCoffeeRoastersScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("brandywine-coffee-roasters")
    assert info is not None
    assert info.roaster_name == "Brandywine"
    assert info.display_name == "Brandywine"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Brandywine"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Collection segment must be stripped: the site's canonical product pages
    # are /products/<handle>.
    assert all(u.startswith("https://www.brandywinecoffeeroasters.com/products/") for u in urls)
    assert "https://www.brandywinecoffeeroasters.com/products/kenya-kiangoi-aa" in urls
    assert "https://www.brandywinecoffeeroasters.com/products/galactic-standard-espresso-blend-16-00" in urls


@pytest.mark.asyncio
async def test_merch_is_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("crewneck" in u for u in urls)


@pytest.mark.asyncio
async def test_tagged_tea_is_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Cosmic Hibiscus Berry is a rooibos/herbal tea tagged "Tea".
    assert not any("cosmic-hibiscus-berry" in u for u in urls)
    assert not any(
        "cosmic-hibiscus-berry" in u for u in scraper._shopify_product_data
    )


@pytest.mark.asyncio
async def test_quirky_coffees_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Novel but genuine coffee products stay in.
    assert "https://www.brandywinecoffeeroasters.com/products/dolly-parton-tribute" in urls
    assert "https://www.brandywinecoffeeroasters.com/products/big-league-coffee-bubblegum-co-ferment-fun" in urls
    assert "https://www.brandywinecoffeeroasters.com/products/ethiopia-decaf-evvw-natural" in urls


@pytest.mark.asyncio
async def test_sample_box_and_spooky_club_are_kept_for_review(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Sample box and the one-off TGIS coffee club are curated coffee bundles:
    # kept and flagged is_tasting_kit/requires_review downstream, not excluded.
    assert "https://www.brandywinecoffeeroasters.com/products/coffee-magic-sample-bog" in urls
    assert "https://www.brandywinecoffeeroasters.com/products/spooky-coffee-club-2026-t-g-i-s" in urls
    assert scraper.is_tasting_kit_url(
        "https://www.brandywinecoffeeroasters.com/products/spooky-coffee-club-2026-t-g-i-s"
    )
    assert scraper.is_tasting_kit_url(
        "https://www.brandywinecoffeeroasters.com/products/coffee-magic-sample-bog"
    )


@pytest.mark.asyncio
async def test_stock_status_parsed(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert scraper._shopify_stock_status["https://www.brandywinecoffeeroasters.com/products/kenya-kiangoi-aa"] is True
    tea_url = "https://www.brandywinecoffeeroasters.com/products/cosmic-hibiscus-berry"
    assert tea_url not in scraper._shopify_stock_status


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
