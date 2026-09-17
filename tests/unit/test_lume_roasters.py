"""Unit tests for the Lume Roasters scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.lume_roasters import LumeRoastersScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "lume_roasters_products.json"
PRODUCTS_JSON_URL = "https://lumeroasters.coffee/collections/frontpage/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return LumeRoastersScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("lume-roasters")
    assert info is not None
    assert info.roaster_name == "Lume Roasters"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Lume Roasters"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://lumeroasters.coffee/products/") for u in urls)
    assert "https://lumeroasters.coffee/products/chelchele" in urls
    assert "https://lumeroasters.coffee/products/pepe-jijon-100g" in urls
    # No collection segment in the canonical product URLs
    assert not any("/collections/" in u for u in urls)


@pytest.mark.asyncio
async def test_sold_out_beans_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Sold-out archive beans must still be scraped (they can come back in stock)
    assert "https://lumeroasters.coffee/products/gatugi-factory-100g" in urls
    assert "https://lumeroasters.coffee/products/aida-battle-100g" in urls


@pytest.mark.asyncio
async def test_reddit_sample_is_kept_for_review_flagging(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # The 60g Reddit sampler is coffee; flagged as a tasting kit downstream
    # instead of excluded.
    assert "https://lumeroasters.coffee/products/reddit-sample" in urls
    assert scraper.is_tasting_kit_url("https://lumeroasters.coffee/products/reddit-sample")


@pytest.mark.asyncio
async def test_stock_status_reflects_variant_availability(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert scraper._shopify_stock_status["https://lumeroasters.coffee/products/chelchele"] is True
    assert scraper._shopify_stock_status["https://lumeroasters.coffee/products/pepe-jijon-100g"] is False


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True


def test_preprocess_product_url_strips_collection_segment(scraper):
    url = "https://lumeroasters.coffee/collections/frontpage/products/chelchele"
    assert scraper.preprocess_product_url(url) == "https://lumeroasters.coffee/products/chelchele"
