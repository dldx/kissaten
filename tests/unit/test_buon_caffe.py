"""Unit tests for the Buon Caffe scraper (fixture-based, no network).

The fixtures mirror the real WooCommerce Store API listing JSON and a trimmed
product detail page of buoncaffe.com.tw (zh-TW WordPress/WooCommerce site).
"""

import json
from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.buon_caffe import API_PRODUCTS_URL, BuonCaffeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> BuonCaffeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return BuonCaffeScraper(api_key="test-api-key")


def _api_soup() -> BeautifulSoup:
    data = json.loads((FIXTURES / "buon_caffe_api_page1.json").read_text())
    return BeautifulSoup(json.dumps(data), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("buon-caffe")
    assert info is not None
    assert info.roaster_name == "Buon Caffe"
    assert info.currency == "TWD"
    assert info.country == "Taiwan"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Buon Caffe"


async def test_store_urls_use_store_api():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [f"{API_PRODUCTS_URL}?per_page=100&page=1"]


async def test_extracts_in_stock_product_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _api_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(f"{API_PRODUCTS_URL}?per_page=100&page=1")
    # In-stock products only: the fermentation kit + the washed Ethiopia
    assert sorted(urls) == [
        "https://buoncaffe.com.tw/products/203180/",
        "https://buoncaffe.com.tw/products/ethiopia-banko-chelchele-washed-g1/",
    ]


async def test_sold_out_products_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _api_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(f"{API_PRODUCTS_URL}?per_page=100&page=1")
    assert "https://buoncaffe.com.tw/products/costa-rica-finca-las-lajas-caturra-catuai-black-honey/" not in urls


async def test_fermentation_project_kit_is_kept(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _api_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(f"{API_PRODUCTS_URL}?per_page=100&page=1")
    assert "https://buoncaffe.com.tw/products/203180/" in urls


async def test_excluded_urls_are_filtered(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _api_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(f"{API_PRODUCTS_URL}?per_page=100&page=1")
    slugs = {u.rstrip("/").rsplit("/", 1)[-1] for u in urls}
    # green beans, drip bags and gift boxes never leak through
    assert not any("greenbeans" in s or "green-beans" in s for s in slugs)
    assert not any("drip" in s for s in slugs)
    assert not any("giftbox" in s for s in slugs)


async def test_stops_paginating_on_empty_page(monkeypatch):
    scraper = _make_scraper()
    calls: list[str] = []

    async def fake_fetch(url, **kwargs):
        calls.append(url)
        if url.endswith("page=1"):
            return _api_soup()
        return BeautifulSoup("[]", "lxml")

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(f"{API_PRODUCTS_URL}?per_page=100&page=1")
    assert len(calls) == 2  # page 1 + empty page 2, then stop
    assert urls


async def test_failed_first_page_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(f"{API_PRODUCTS_URL}?per_page=100&page=1")
    assert urls == []


async def test_fetch_page_narrows_product_pages(monkeypatch):
    scraper = _make_scraper()
    product_html = (FIXTURES / "buon_caffe_product.html").read_text()
    full_soup = BeautifulSoup(product_html, "lxml")

    async def fake_super_fetch(self, url, **kwargs):
        return full_soup

    monkeypatch.setattr(type(scraper).__mro__[1], "fetch_page", fake_super_fetch)
    narrowed = await scraper.fetch_page("https://buoncaffe.com.tw/products/203180/")
    assert narrowed is not None
    assert "Fermentation" in narrowed.get_text()

    # The narrowed node IS the WooCommerce div.product container
    assert narrowed.name == "div"
    assert "product" in (narrowed.get("class") or [])

    # Listing / API URLs are not narrowed
    api_soup = await scraper.fetch_page(f"{API_PRODUCTS_URL}?per_page=100&page=1")
    assert api_soup is full_soup


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://buoncaffe.com.tw/products/test-bean/",
        roaster="Buon Caffe",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "TWD"
