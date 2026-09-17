"""Unit tests for the Coffee with Dongze scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.coffee_with_dongze import CoffeeWithDongzeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "coffee_with_dongze_products.json"
PRODUCTS_JSON_URL = "https://coffee-with-dongze.myshopify.com/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return CoffeeWithDongzeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("coffee-with-dongze")
    assert info is not None
    assert info.roaster_name == "Coffee with Dongze"
    assert info.display_name == "Coffee with Dongze"
    assert info.website == "https://coffee-with-dongze.myshopify.com"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Coffee with Dongze"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Canonical form on the myshopify domain is /products/<handle> (no
    # collection segment), which is what the base class builds from the root
    # products.json URL.
    assert all(u.startswith("https://coffee-with-dongze.myshopify.com/products/") for u in urls)
    assert "https://coffee-with-dongze.myshopify.com/products/blackmoon-chiroso-anaerobic-natural-lot-0206" in urls
    assert "https://coffee-with-dongze.myshopify.com/products/symbiosis-project-x-bambito-estate-gesha-washed" in urls


@pytest.mark.asyncio
async def test_sold_out_drops_are_discovered(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Most drop products are sold out — they must still be discovered and
    # tracked via the stock-status map.
    assert "https://coffee-with-dongze.myshopify.com/products/blackmoon-chiroso-anaerobic-natural-lot-0206" in urls
    assert scraper._shopify_stock_status[
        "https://coffee-with-dongze.myshopify.com/products/blackmoon-chiroso-anaerobic-natural-lot-0206"
    ] is False


@pytest.mark.asyncio
async def test_tasting_sets_are_kept_for_review_flagging(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Curated tasting sets are coffee; they are flagged as tasting kits
    # downstream instead of excluded.
    assert "https://coffee-with-dongze.myshopify.com/products/peru-incahuasi-sl-09-tasting-set" in urls
    assert "https://coffee-with-dongze.myshopify.com/products/2026-finca-sophia-auction-tasting-set" in urls


@pytest.mark.asyncio
async def test_gift_cards_are_excluded(scraper, mocker):
    products = _fixture_products()
    products.append({"handle": "gift-card", "title": "Gift Card", "variants": [{"available": True}]})
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=products)

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("gift-card" in u for u in urls)


@pytest.mark.asyncio
async def test_premium_boxes_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # The annual premium coffee box is coffee, not merch.
    assert "https://coffee-with-dongze.myshopify.com/products/year-of-the-horse-premium-coffee-boxes" in urls


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
