"""Unit tests for the GWO Coffee scraper (fixture-based, no network)."""

import asyncio
import json
from pathlib import Path

from kissaten.scrapers.gwo_coffee import GwoCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://gwo.coffee/products.json"


def _products():
    return json.loads((FIXTURES / "gwo_coffee_products.json").read_text())["products"]


def _make_scraper() -> GwoCoffeeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return GwoCoffeeScraper(api_key="test-api-key")


def _patch_fetch(monkeypatch, scraper: GwoCoffeeScraper) -> None:
    """Replace the single Shopify fetch entry point — fully mocked."""

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)


def test_registry_entry():
    info = get_registry().get_scraper_info("gwo-coffee")
    assert info is not None
    assert info.roaster_name == "GWO Coffee"
    assert info.currency == "EUR"
    assert info.country == "Netherlands"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "GWO Coffee"


async def test_extracts_coffee_products_with_canonical_urls(monkeypatch):
    scraper = _make_scraper()
    _patch_fetch(monkeypatch, scraper)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert "https://gwo.coffee/products/gikirima" in urls
    assert "https://gwo.coffee/products/kii-aa" in urls
    assert all(u.startswith("https://gwo.coffee/products/") for u in urls)
    assert all("/collections/" not in u for u in urls)


async def test_transition_placeholder_is_excluded(monkeypatch):
    scraper = _make_scraper()
    _patch_fetch(monkeypatch, scraper)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    # The 0.00 EUR L100 -> P3000 announcement is not a bean and must never
    # become a product URL.
    assert not any("p3000-drops-loading" in u for u in urls)
    assert not any("p3000" in u for u in urls)


async def test_tasting_sets_are_not_excluded(monkeypatch):
    scraper = _make_scraper()
    _patch_fetch(monkeypatch, scraper)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    # Coffee for sale: they must reach the downstream is_tasting_kit /
    # requires_review flagging instead of being silently dropped.
    assert "https://gwo.coffee/products/gv-oma-tasting-set" in urls
    assert "https://gwo.coffee/products/that-v3" in urls


def test_stock_status_keyed_by_canonical_url(monkeypatch):
    scraper = _make_scraper()
    _patch_fetch(monkeypatch, scraper)

    asyncio.run(scraper._extract_product_urls_from_store(STORE_URL))

    # Every real coffee is currently sold out (store closed for the roaster
    # transition), so the captured fixture reports available=False throughout;
    # the placeholder is never keyed at all.
    for handle in ("gikirima", "kii-aa", "keramo-washed", "gv-oma-tasting-set", "that-v3"):
        url = f"https://gwo.coffee/products/{handle}"
        assert url in scraper._shopify_stock_status
        assert scraper._shopify_stock_status[url] is False
    assert "https://gwo.coffee/products/p3000-drops-loading" not in scraper._shopify_stock_status


def test_currency_pinned_to_home_market():
    scraper = _make_scraper()
    assert scraper.store_currency == "EUR"
    assert scraper._currency_detected is True


def test_currency_pinned_in_postprocess():
    from kissaten.schemas import CoffeeBean

    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://gwo.coffee/products/test-bean",
        roaster="GWO Coffee",
        origins=[],
        price_options=[],
        currency="USD",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "EUR"
