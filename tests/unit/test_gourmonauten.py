"""Unit tests for the GourmoNauten scraper (fixture-based, no network).

GourmoNauten is a Shopify storefront that is currently password-protected, so
the fixtures use the Shopify ``products.json`` payload shape and the tests
verify graceful degradation when the catalogue endpoint is unavailable (401).
"""

import json
from pathlib import Path

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.gourmonauten import GourmonautenScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _products() -> list[dict]:
    return json.loads((FIXTURES / "gourmonauten_products.json").read_text())["products"]


def _make_scraper() -> GourmonautenScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return GourmonautenScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("gourmonauten")
    assert info is not None
    assert info.roaster_name == "GourmoNauten"
    assert info.currency == "EUR"
    assert info.country == "Germany"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "GourmoNauten"


async def test_store_urls_target_products_json():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == ["https://gourmonauten.club/products.json?limit=250"]


async def test_extracts_only_in_stock_coffee_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(page: int):
        return _products() if page == 1 else []

    monkeypatch.setattr(scraper, "_fetch_products_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://gourmonauten.club/products.json?limit=250")
    assert "https://gourmonauten.club/products/ethiopia-guji-hambella" in urls
    # Sold-out product is excluded.
    assert "https://gourmonauten.club/products/kenya-karimikui-aa" not in urls
    # Equipment (V60 dripper) is excluded by the coffee URL filter.
    assert "https://gourmonauten.club/products/hario-v60-dripper" not in urls


async def test_failed_catalogue_fetch_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(page: int):
        return None

    monkeypatch.setattr(scraper, "_fetch_products_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://gourmonauten.club/products.json?limit=250")
    assert urls == []


async def test_password_protected_products_json_is_treated_as_failure(monkeypatch):
    """A 401 (the pre-launch password page) must not be parsed as a catalogue."""
    scraper = _make_scraper()

    class _Response:
        status_code = 401

        def json(self):
            return {}

    async def fake_get(url: str):
        return _Response()

    monkeypatch.setattr(scraper.client, "get", fake_get)
    assert await scraper._fetch_products_page(1) is None


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://gourmonauten.club/products/test-bean",
        roaster="GourmoNauten",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "EUR"
