"""Unit tests for the One Line Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.one_line_coffee import OneLineCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "one_line_coffee_products.json"
PRODUCTS_JSON_URL = "https://www.onelinecoffee.com/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return OneLineCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("one-line-coffee")
    assert info is not None
    assert info.roaster_name == "One Line Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "One Line Coffee"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Collection segment must be stripped: the site links to /products/<handle>.
    assert all(u.startswith("https://www.onelinecoffee.com/products/") for u in urls)
    assert "https://www.onelinecoffee.com/products/method-blend-espresso" in urls
    assert "https://www.onelinecoffee.com/products/ethiopia-musa-abalulesa-honey" in urls


@pytest.mark.asyncio
async def test_subscriptions_and_gift_bundles_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("subscription" in u for u in urls)
    assert not any("gift-bundle" in u for u in urls)


@pytest.mark.asyncio
async def test_decaf_and_house_roast_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://www.onelinecoffee.com/products/colombia-fortune-decaf" in urls
    # The live catalogue no longer lists the bottled "cold-brew" product;
    # the base Colombia El Nevado house roast remains and must be kept.
    assert "https://www.onelinecoffee.com/products/colombia-el-nevado-house-roast" in urls


@pytest.mark.asyncio
async def test_stock_status_parsed(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert scraper._shopify_stock_status["https://www.onelinecoffee.com/products/burundi-hafi"] is True


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True


@pytest.mark.asyncio
async def test_us_market_param_appended(scraper, mocker):
    # Markets filtering by egress geography can empty the collection and
    # convert prices to GBP; the override must pin the US home market.
    fetch = mocker.patch.object(
        scraper,
        "_fetch_page_with_escalation",
        side_effect=[({"products": []}, False)],
    )

    products = await scraper._fetch_all_shopify_products(PRODUCTS_JSON_URL)

    assert products == []
    called_url = fetch.call_args.args[0]
    assert called_url == f"{PRODUCTS_JSON_URL}?country=US&limit=250&page=1"
