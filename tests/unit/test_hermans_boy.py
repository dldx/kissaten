"""Unit tests for the Herman's Boy Coffee scraper (fixture-based, no network).

Herman's Boy runs a Square Online storefront whose public store API
(``cdn5.editmysite.com``) supplies the catalogue, per-product detail and SKUs.
"""

import json
from pathlib import Path

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.hermans_boy import (
    STORE_API_BASE,
    HermansBoyScraper,
    _parse_weight_grams,
)
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _make_scraper() -> HermansBoyScraper:
    return HermansBoyScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("hermans-boy")
    assert info is not None
    assert info.roaster_name == "Herman's Boy Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    assert _make_scraper().roaster_name == "Herman's Boy Coffee"


async def test_store_urls_target_coffee_categories():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert len(urls) == 5
    assert all(url.startswith(f"{STORE_API_BASE}/products?") for url in urls)
    assert all("categories[]=" in url for url in urls)


async def test_extracts_only_visible_in_stock_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch_json(url: str):
        return _load("hermans_boy_products.json")

    monkeypatch.setattr(scraper, "_fetch_json", fake_fetch_json)
    urls = await scraper._extract_product_urls_from_store(
        f"{STORE_API_BASE}/products?page=1&per_page=50&categories[]=T7MSYPDOIACMII5LSZI33SOE"
    )

    assert "https://hermans-boy.square.site/product/colombian-supremo/L5F66ZVB42NMUIWR7IVNOG4G" in urls
    # The Fermentation Project kit stays in (tasting-kit flagging is downstream).
    assert (
        "https://hermans-boy.square.site/product/presale-the-fermentation-project-tasting-kit/GOY3QUCTPE764Y7UHZGQIHOY"
        in urls
    )
    # Out-of-stock and hidden products are excluded.
    assert "https://hermans-boy.square.site/product/hazelnut/VHXVGK36N5LELKPTKQ63A23J" not in urls
    assert "https://hermans-boy.square.site/product/hidden-test-blend/OC6QVH3TXFUWOWT4SMKOZ6I3" not in urls


async def test_failed_api_fetch_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch_json(url: str):
        return None

    monkeypatch.setattr(scraper, "_fetch_json", fake_fetch_json)
    assert (
        await scraper._extract_product_urls_from_store(
            f"{STORE_API_BASE}/products?page=1&per_page=50&categories[]=T7MSYPDOIACMII5LSZI33SOE"
        )
        == []
    )


def test_weight_parsing():
    assert _parse_weight_grams("Regular, 1/2 lb bag") == 227
    assert _parse_weight_grams("Regular, 1 lb bag") == 454
    assert _parse_weight_grams("Decaf, 5 lb bag") == 2268
    assert _parse_weight_grams("250 g") == 250
    assert _parse_weight_grams("Default") is None
    # Out-of-schema weights are rejected rather than emitted.
    assert _parse_weight_grams("2 g") is None


async def test_build_product_summary_html(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch_json(url: str):
        if "/skus" in url:
            return _load("hermans_boy_skus.json")
        return _load("hermans_boy_detail.json")

    monkeypatch.setattr(scraper, "_fetch_json", fake_fetch_json)
    html = await scraper._fetch_product_summary_html(
        "https://hermans-boy.square.site/product/colombian-supremo/L5F66ZVB42NMUIWR7IVNOG4G"
    )

    assert html is not None
    assert "Colombian Supremo" in html
    assert "Medium roast" in html
    assert "Caffeine: Regular, Decaf, 50/50" in html
    assert "1/2 lb bag (227 g) | Price: $8.50 USD" in html
    assert "5 lb bag (2268 g) | Price: $64.75 USD" in html


async def test_fetch_page_serves_product_pages_from_api(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch_json(url: str):
        if "/skus" in url:
            return _load("hermans_boy_skus.json")
        return _load("hermans_boy_detail.json")

    monkeypatch.setattr(scraper, "_fetch_json", fake_fetch_json)
    soup = await scraper.fetch_page(
        "https://hermans-boy.square.site/product/colombian-supremo/L5F66ZVB42NMUIWR7IVNOG4G"
    )
    assert soup is not None
    assert "Colombian Supremo" in soup.get_text(" ", strip=True)


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://hermans-boy.square.site/product/test-bean/ABC123",
        roaster="Herman's Boy Coffee",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    assert scraper.postprocess_extracted_bean(bean).currency == "USD"
