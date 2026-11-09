"""Unit tests for the Coffee Architects scraper.

Coffee Architects (coffee-architects.com) migrated from a Squarespace
single-page site (beans rendered as images inside an "Angebot" section,
scraped via pseudo-URL image extraction) to a standard Shopify store. The
catalogue is only 6 coffee products, exposed through
``/collections/all/products.json``. These tests run against a captured
fixture (``coffee_architects_products.json``) and verify the Shopify JSON
listing flow, the canonical URL building, and slug exclusion behavior.
"""

import json
from pathlib import Path

from kissaten.scrapers._curl_http import RequestError
from kissaten.scrapers.coffee_architects import CoffeeArchitectsScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "coffee_architects_products.json"


def _make_scraper() -> CoffeeArchitectsScraper:
    # No api_key: no network, no AI extractor needed for these tests.
    return CoffeeArchitectsScraper()


def _fixture_products() -> list[dict]:
    data = json.loads(FIXTURE.read_text())
    return data["products"]


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    """Minimal stand-in for httpx.AsyncClient returning the fixture page."""

    def __init__(self, payload: dict):
        self.payload = payload
        self.requested_urls: list[str] = []

    async def get(self, url: str, **kwargs):
        self.requested_urls.append(url)
        return _FakeResponse(self.payload)


def test_registered_in_registry():
    registry = get_registry()
    assert registry.is_registered("coffee-architects")
    info = registry.get_scraper_info("coffee-architects")
    assert info is not None
    assert info.scraper_class is CoffeeArchitectsScraper
    assert info.currency == "CHF"
    assert info.country == "Switzerland"
    assert info.status == "available"


def test_products_json_urls_target_shopify_endpoints():
    scraper = _make_scraper()
    assert scraper.products_json_urls == [
        "https://www.coffee-architects.com/collections/all/products.json",
        "https://www.coffee-architects.com/products.json",
    ]


def test_preprocess_product_url_strips_collection_segment():
    scraper = _make_scraper()
    url = "https://www.coffee-architects.com/collections/all/products/keza"
    assert scraper.preprocess_product_url(url) == "https://www.coffee-architects.com/products/keza"


async def test_extract_product_urls_from_shopify_fixture():
    scraper = _make_scraper()
    scraper.client = _FakeClient({"products": _fixture_products()})

    urls = await scraper._extract_product_urls_from_store(
        "https://www.coffee-architects.com/collections/all/products.json"
    )

    # The fixture has 6 genuine coffee products (Filter / Espresso product types).
    assert len(urls) == 6
    expected_handles = {"keza", "tamu", "ligero-decaf", "fusao", "alero", "amizade"}
    actual_handles = {u.rsplit("/", 1)[-1] for u in urls}
    assert actual_handles == expected_handles
    # URLs are canonical (collection segment stripped).
    for u in urls:
        assert u.startswith("https://www.coffee-architects.com/products/")
        assert "/collections/" not in u
    # Stock status recorded per URL; all fixture products are available.
    for u in urls:
        assert scraper._shopify_stock_status[u] is True
        assert u in scraper._shopify_product_data
    # Success must not mark the listing as failed.
    assert "https://www.coffee-architects.com/collections/all/products.json" not in scraper._failed_listing_urls


async def test_extract_filters_excluded_slugs():
    scraper = _make_scraper()
    products = _fixture_products()
    # Add a gift card product that must be filtered out by exclude_slugs.
    products.append({"handle": "gift-card", "title": "Gift Card", "variants": [{"available": True}]})
    products.append({"handle": "coffee-subscription", "title": "Subscription", "variants": [{"available": True}]})
    scraper.client = _FakeClient({"products": products})

    urls = await scraper._extract_product_urls_from_store(
        "https://www.coffee-architects.com/collections/all/products.json"
    )

    assert len(urls) == 6
    for u in urls:
        assert "gift-card" not in u
        assert "subscription" not in u


async def test_fetch_failure_records_failed_listing_url():
    """Failed listing fetch must be recorded so OOS updates are suppressed.

    The base ``_fetch_page_with_escalation`` ladder upgrades httpx failures to
    Playwright, so both transports must fail before the listing is recorded as
    failed. max_retries is 0 so no backoff sleeps run in the test.
    """
    scraper = _make_scraper()
    scraper.max_retries = 0

    class _FailingClient:
        async def get(self, url: str, **kwargs):
            raise RequestError("network down")

    scraper.client = _FailingClient()

    async def failing_playwright(url: str):
        raise RuntimeError("playwright unavailable")

    scraper._fetch_with_playwright = failing_playwright  # type: ignore[method-assign]

    urls = await scraper._extract_product_urls_from_store(
        "https://www.coffee-architects.com/collections/all/products.json"
    )

    assert urls == []
    assert "https://www.coffee-architects.com/collections/all/products.json" in scraper._failed_listing_urls


def test_no_shopify_products_lost_to_url_narrowing():
    """The Shopify flow must not inherit the old Squarespace pseudo-URL scheme."""
    scraper = _make_scraper()
    # The old image-based extractor used #{slug} pseudo URLs; those must be gone.
    assert not hasattr(scraper, "_pseudo_to_image_map")
    assert not hasattr(scraper, "_get_slug_from_image_url")
