"""Unit tests for the Patch Coffee scraper (fixture-based, no network).

The live storefront (patchcoffee.shop) was unreachable at authoring time —
the Shopify edge refuses TLS for the custom domain and the store reports
"Store unavailable", so a live products.json could not be captured. The
fixture is a structural stub in the exact Shopify products.json schema
(4 coffees + a gift card + a subscription) used to validate URL extraction
and exclusion logic until the store comes back online.
"""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.patch_coffee import PatchCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "patch_coffee_products.json"
PRODUCTS_JSON_URL = "https://patchcoffee.shop/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return PatchCoffeeScraper()


def test_registry_entry(scraper):
    info = get_registry().get_scraper_info("patch-coffee")
    assert info is not None
    assert info.roaster_name == "Patch"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"
    assert info.website == "https://patchcoffee.shop"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Patch"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://patchcoffee.shop/products/") for u in urls)
    assert "https://patchcoffee.shop/products/patch-house-blend" in urls
    assert "https://patchcoffee.shop/products/ethiopia-guji-natural" in urls


@pytest.mark.asyncio
async def test_decaf_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://patchcoffee.shop/products/patch-decaf-sugarcane" in urls


@pytest.mark.asyncio
async def test_gift_card_and_subscription_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("gift-card" in u for u in urls)
    assert not any("subscription" in u for u in urls)


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
