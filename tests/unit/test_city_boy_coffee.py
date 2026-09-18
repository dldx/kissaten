"""Unit tests for the City Boy Coffee scraper (fixture-based, no network).

The fixture mirrors the real WooCommerce Store API listing JSON of
cityboycoffee.com (coffee beans, cafe drinks, subscription, gift card).
"""

import json
from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.city_boy_coffee import API_PRODUCTS_URL, CityBoyCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> CityBoyCoffeeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return CityBoyCoffeeScraper(api_key="test-api-key")


def _api_soup() -> BeautifulSoup:
    data = json.loads((FIXTURES / "city_boy_coffee_api.json").read_text())
    return BeautifulSoup(json.dumps(data), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("city-boy-coffee")
    assert info is not None
    assert info.roaster_name == "City Boy Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "City Boy Coffee"


async def test_store_urls_use_store_api():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [f"{API_PRODUCTS_URL}?per_page=100&page=1"]


async def test_extracts_in_stock_coffee_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        if url.endswith("page=1"):
            return _api_soup()
        return BeautifulSoup("[]", "lxml")

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(f"{API_PRODUCTS_URL}?per_page=100&page=1")
    assert sorted(urls) == [
        "https://cityboycoffee.com/product/el-salvador-coffee-finca-miravalles-pacamara/",
        "https://cityboycoffee.com/product/liberica-l2-anaerobic-natural/",
    ]


async def test_sold_out_products_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _api_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(f"{API_PRODUCTS_URL}?per_page=100&page=1")
    assert "https://cityboycoffee.com/product/colombia-coffee-la-terraza/" not in urls


async def test_drinks_and_merch_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _api_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(f"{API_PRODUCTS_URL}?per_page=100&page=1")
    slugs = {u.rstrip("/").rsplit("/", 1)[-1] for u in urls}
    for slug in (
        "americano",
        "flat-white",
        "cortado",
        "cappuccino",
        "latte",
        "macchiato",
        "espresso",
        "extra-shot",
        "cascara-tea",
        "coffee-scale",
        "city-boy-gift-card",
        "sphere-coffee-club",
    ):
        assert slug not in slugs


async def test_failed_first_page_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(f"{API_PRODUCTS_URL}?per_page=100&page=1")
    assert urls == []


async def test_stops_paginating_on_empty_page(monkeypatch):
    scraper = _make_scraper()
    calls: list[str] = []

    async def fake_fetch(url, **kwargs):
        calls.append(url)
        if url.endswith("page=1"):
            return _api_soup()
        return BeautifulSoup("[]", "lxml")

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    await scraper._extract_product_urls_from_store(f"{API_PRODUCTS_URL}?per_page=100&page=1")
    assert len(calls) == 2  # page 1 + empty page 2, then stop


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://cityboycoffee.com/product/test-bean/",
        roaster="City Boy Coffee",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "USD"
