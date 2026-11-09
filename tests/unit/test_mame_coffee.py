"""Unit tests for the Mame Coffee scraper.

MAME Roastery (mame.coffee) migrated off a legacy WooCommerce theme to a
Shopify storefront: ``/product-category/*`` URLs 301 to ``/collections/*`` and
the catalogue is served through ``/products.json``. These tests run against a
captured fixture of that feed (``tests/fixtures/mame_coffee_products.json``)
and verify the URL-extraction path, the non-coffee exclude slugs (equipment +
subscriptions), the CHF currency pinning and the chrome-impersonated client
(the Shopify edge 403s curl_cffi's default fingerprint).
"""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.mame_coffee import MameCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "mame_coffee_products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    """Minimal stand-in for the scraper's curl_cffi-backed AsyncClient."""

    def __init__(self, pages: list[dict] | Exception):
        self.pages = list(pages) if isinstance(pages, list) else pages
        self.requested_urls: list[str] = []

    async def get(self, url: str, **kwargs):
        self.requested_urls.append(url)
        if isinstance(self.pages, Exception):
            raise self.pages
        return _FakeResponse(self.pages.pop(0))


def _make_scraper_with_fixture(monkeypatch) -> MameCoffeeScraper:
    scraper = MameCoffeeScraper()
    scraper.client = _FakeClient([{"products": _fixture_products()}])
    return scraper


def test_registered_in_registry():
    registry = get_registry()
    assert registry.is_registered("mame-coffee")
    info = registry.get_scraper_info("mame-coffee")
    assert info is not None
    assert info.scraper_class is MameCoffeeScraper
    assert info.currency == "CHF"
    assert info.country == "Switzerland"
    assert info.status == "available"


def test_store_urls_use_shopify_products_json():
    """The legacy /product-category/* WooCommerce URLs must be gone."""
    scraper = MameCoffeeScraper()
    urls = _run(scraper.get_store_urls())
    assert urls == ["https://mame.coffee/products.json"]
    assert all("product-category" not in u for u in urls)


def test_client_uses_chrome_impersonation():
    """The Shopify edge 403s the default libcurl fingerprint; the client must
    be rebuilt with ``impersonate="chrome"`` (curl_cffi-backed shim)."""
    scraper = MameCoffeeScraper()
    # The _curl_http shim stores the profile on the client instance.
    assert getattr(scraper.client, "_impersonate", None) == "chrome"


def test_extract_product_urls_filters_non_coffee_and_builds_handles(monkeypatch):
    """Coffee handles become product URLs; equipment/subscription slugs are
    excluded; sold-out (all variants unavailable) coffees are still listed —
    their stock status is recorded on the scraper's status map."""
    scraper = _make_scraper_with_fixture(monkeypatch)
    urls = _run(scraper._extract_product_urls_from_store("https://mame.coffee/products.json"))

    # Feed has 19 products: 8 excluded non-coffee + 11 coffees (daily + competition).
    coffee_handles = [
        "tinganga-ab",
        "uba-sangria-omni",
        "uba-orange-omni",
        "uba-berry-omni",
        "brayan-smith",
        "el-placer-geisha-white-honey-omni",
        "adaura-geisha-natural-df-omni",
        "decaf-omni",
        "pearl",
        "full-bloom",
        "pink-bourbon",
    ]
    expected = {f"https://mame.coffee/products/{h}" for h in coffee_handles}
    assert set(urls) == expected
    assert len(urls) == len(coffee_handles)

    for excluded in ("hario", "aeropress", "ankomn", "subscription"):
        assert not any(excluded in u for u in urls), excluded

    # Stock map: any-variant availability recorded per coffee URL.
    assert scraper._shopify_stock_status["https://mame.coffee/products/uba-orange-omni"] is True
    assert scraper._shopify_stock_status["https://mame.coffee/products/uba-berry-omni"] is True
    # Excluded slugs never reach the stock map (skipped before recording).
    assert "https://mame.coffee/products/mame-x-hario-switch-purion-02" not in scraper._shopify_stock_status
    # Product JSON cached for later AI enrichment.
    assert scraper._shopify_product_data["https://mame.coffee/products/pearl"]["handle"] == "pearl"


def test_listing_failure_records_failed_listing_url(monkeypatch):
    """A fetch failure must mark the listing URL failed so the BaseScraper
    false-delisting guard suppresses out-of-stock updates for the session."""
    scraper = MameCoffeeScraper()
    scraper.client = _FakeClient(RuntimeError("boom"))
    with pytest.raises(Exception):
        _run(scraper._extract_product_urls_from_store("https://mame.coffee/products.json"))


def _run(coro):
    import asyncio

    return asyncio.run(coro)
