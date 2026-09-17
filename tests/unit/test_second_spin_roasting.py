"""Unit tests for the Second Spin Roasting Co. scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.second_spin_roasting import SecondSpinRoastingScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "second_spin_roasting_products.json"
PRODUCTS_JSON_URL = "https://secondspinroasting.com/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return SecondSpinRoastingScraper()


def test_registry_entry(scraper):
    info = get_registry().get_scraper_info("second-spin-roasting")
    assert info is not None
    assert info.roaster_name == "Second Spin"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Second Spin"


async def test_store_urls_cover_all_three_collections(scraper):
    urls = await scraper.get_store_urls()
    assert urls == [
        "https://secondspinroasting.com/collections/coffee/products.json",
        "https://secondspinroasting.com/collections/limited-66-gallery/products.json",
        "https://secondspinroasting.com/collections/wholesale/products.json",
    ]


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Product URLs are canonicalized to the no-collection /products/<handle> form.
    assert all(u.startswith("https://secondspinroasting.com/products/") for u in urls)
    assert "https://secondspinroasting.com/products/ethiopia-testi-specialty-aricha-adorsi-yirgacheffe" in urls
    assert "https://secondspinroasting.com/products/kodachrome-signature-espresso-blend" in urls
    assert len(urls) == 6


@pytest.mark.asyncio
async def test_limited_66_micro_lot_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert (
        "https://secondspinroasting.com/products/"
        "limited-66-colombia-finca-la-riviera-julio-madrid-julio-quiceno-sudan-rume-44-hour-anaerobic-bioprocess"
        in urls
    )


@pytest.mark.asyncio
async def test_subscriptions_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("subscription" in u for u in urls)


@pytest.mark.asyncio
async def test_preprocess_product_url_strips_collection_segment(scraper):
    url = "https://secondspinroasting.com/collections/limited-66-gallery/products/ethiopia-testi"
    assert scraper.preprocess_product_url(url) == "https://secondspinroasting.com/products/ethiopia-testi"
    # Non-products.json-derived URLs pass through unchanged.
    assert scraper.preprocess_product_url("https://secondspinroasting.com/pages/about") == (
        "https://secondspinroasting.com/pages/about"
    )


@pytest.mark.asyncio
async def test_sold_out_products_are_still_listed(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Sold-out status is tracked per-URL for stock updates, but the product
    # stays in the catalog list (the Ethiopia Gori Gesha lot is unavailable).
    assert "https://secondspinroasting.com/products/ethiopia-testi-specialty-aricha-adorsi-yirgacheffe" in urls


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
