"""Unit tests for the Regalia Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.regalia_coffee import RegaliaCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "regalia_coffee_products.json"
PRODUCTS_JSON_URL = "https://regaliacoffee.com/collections/all/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return RegaliaCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("regalia-coffee")
    assert info is not None
    assert info.roaster_name == "Regalia"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Regalia"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://regaliacoffee.com/products/") for u in urls)
    assert "https://regaliacoffee.com/products/goro-site" in urls
    assert "https://regaliacoffee.com/products/chiroso-lot-6" in urls


@pytest.mark.asyncio
async def test_non_coffee_product_types_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Grinders (the-eg-1, the-hg-2, the-key, the-bird-1, moonraker-1), brew
    # gear, books, apparel and gift cards are filtered by product_type.
    for excluded in (
        "the-eg-1",
        "the-hg-2",
        "the-key",
        "the-bird-1",
        "moonraker-1",
        "gift-cards",
        "kids-staple-tee",
        "the-physics-of-espresso",
        "cometeer-regalia-capsules",
    ):
        assert f"https://regaliacoffee.com/products/{excluded}" not in urls
    assert not any("subscription" in u for u in urls)


@pytest.mark.asyncio
async def test_stock_status_keyed_by_canonical_url(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    url = "https://regaliacoffee.com/products/goro-site"
    assert url in scraper._shopify_stock_status
    assert url in scraper._shopify_product_data


def test_home_currency_pinned(scraper):
    # Regalia's storefront converts prices to EUR for clients sending an
    # Accept-Language header; the US market is pinned via country=US.
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True


@pytest.mark.asyncio
async def test_market_param_appended_to_listing_requests(scraper, mocker):
    captured: list[str] = []

    async def fake_fetch(url):
        captured.append(url)
        return {"products": _fixture_products()}, False

    mocker.patch.object(scraper, "_fetch_page_with_escalation", side_effect=fake_fetch)

    await scraper._fetch_all_shopify_products(PRODUCTS_JSON_URL)

    assert captured == [f"{PRODUCTS_JSON_URL}?country=US&limit=250&page=1"]
