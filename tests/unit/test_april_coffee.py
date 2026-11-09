"""Unit tests for the April Coffee scraper.

April moved to a custom Next.js storefront backed by the Shopify Storefront
API: every ``/collections/<handle>/products.json`` URL returns 404 and product
data comes from ``/api/collections/products?collection=<handle>`` instead.
These tests run against a captured fixture of that API (see
``tests/fixtures/april_coffee_products.json``) and verify the normalization
into the classic Shopify ``products.json`` shape, the legacy-URL identity
scheme, the roast-profile mapping and the exclude-slug behavior.
"""

import json
from pathlib import Path

import pytest

from kissaten.schemas import CoffeeBean, PriceOption
from kissaten.schemas.coffee_bean import Bean
from kissaten.scrapers.april_coffee import COLLECTIONS, STOREFRONT_API_URL, AprilCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "april_coffee_products.json"
LEGACY_BASE = "https://www.aprilcoffeeroasters.com/collections"


def _make_scraper() -> AprilCoffeeScraper:
    # No api_key: no network, no AI extractor needed for these tests.
    return AprilCoffeeScraper()


def _fixture_products() -> list[dict]:
    data = json.loads(FIXTURE.read_text())
    return data["products"]


def _make_bean(url: str) -> CoffeeBean:
    return CoffeeBean(
        name="Test Bean",
        roaster="April Coffee",
        url=url,
        origins=[Bean(country="Denmark")],
        price_options=[PriceOption(weight=250, price=168.0, currency="DKK")],
        currency="DKK",
    )


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    """Minimal stand-in for httpx.AsyncClient returning queued API pages."""

    def __init__(self, pages: list[dict] | Exception):
        self.pages = list(pages) if isinstance(pages, list) else pages
        self.requested_urls: list[str] = []

    async def get(self, url: str, **kwargs):
        self.requested_urls.append(url)
        if isinstance(self.pages, Exception):
            raise self.pages
        return _FakeResponse(self.pages.pop(0))


def test_registered_in_registry():
    registry = get_registry()
    assert registry.is_registered("april-coffee")
    info = registry.get_scraper_info("april-coffee")
    assert info is not None
    assert info.scraper_class is AprilCoffeeScraper
    assert info.currency == "DKK"
    assert info.country == "Denmark"
    assert info.status == "available"


def test_products_json_urls_cover_all_collections():
    scraper = _make_scraper()
    assert scraper.products_json_urls == [
        f"{LEGACY_BASE}/filter-beans/products.json",
        f"{LEGACY_BASE}/espresso-beans/products.json",
    ]
    assert set(scraper._api_handles_by_legacy_segment) == set(COLLECTIONS)
    all_handles = {h for handles in COLLECTIONS.values() for h in handles}
    assert (
        set(scraper._api_handles_by_legacy_segment["filter-beans"])
        | set(scraper._api_handles_by_legacy_segment["espresso-beans"])
        == all_handles
    )
    # Core roast collections must be present.
    assert {"filter-coffee", "espresso-coffee"} <= all_handles
    assert STOREFRONT_API_URL == "https://www.aprilcoffeeroasters.com/api/collections/products"


def test_storefront_api_handle_for_legacy_url():
    scraper = _make_scraper()
    assert "filter-coffee" in scraper._api_handles_by_legacy_segment["filter-beans"]
    assert "espresso-coffee" in scraper._api_handles_by_legacy_segment["espresso-beans"]


def test_normalize_storefront_product_from_fixture():
    scraper = _make_scraper()
    raw = _fixture_products()[0]
    assert raw["handle"] == "volcan-azul-costa-rica-washed-sl28"

    normalized = scraper._normalize_storefront_product(raw)

    assert normalized["handle"] == "volcan-azul-costa-rica-washed-sl28"
    assert normalized["title"] == raw["title"]
    assert normalized["body_html"] == raw["descriptionHtml"]
    assert normalized["tags"] == ["Filter Beans"]
    # Synthesized variant carries the min price and availability.
    assert normalized["variants"] == [
        {"title": "Default", "price": raw["priceRange"]["minVariantPrice"]["amount"], "available": True}
    ]
    assert normalized["available"] is True
    assert normalized["images"][0]["src"] == raw["featuredImage"]["url"]
    assert normalized["supplier_information"] == raw["supplierInformation"]


def test_normalize_out_of_stock_product():
    scraper = _make_scraper()
    raw = dict(_fixture_products()[0])
    raw["availableForSale"] = False

    normalized = scraper._normalize_storefront_product(raw)

    assert normalized["available"] is False
    assert normalized["variants"][0]["available"] is False


async def test_fetch_all_shopify_products_paginates_and_normalizes():
    scraper = _make_scraper()
    fixture_page = json.loads(FIXTURE.read_text())
    page1 = {"products": fixture_page["products"][:2], "pageInfo": {"hasNextPage": True, "endCursor": "CURSOR1"}}
    page2 = {"products": fixture_page["products"][2:], "pageInfo": {"hasNextPage": False}}
    empty = {"products": [], "pageInfo": {"hasNextPage": False}}
    # filter-beans group = filter-coffee, samplebox, organic-coffee, filter-drip-packs
    scraper.client = _FakeClient([page1, page2, empty, empty, empty])

    url = f"{LEGACY_BASE}/filter-beans/products.json"
    products = await scraper._fetch_all_shopify_products(url)

    # filter-beans maps to filter-coffee first; pages 1-2 are its pagination,
    # the remaining pages are the (empty) first pages of the other collections
    # in the group.
    assert len(products) == len(fixture_page["products"])
    assert all("variants" in p and p["handle"] for p in products)
    # First page without cursor, second page with the cursor param.
    assert scraper.client.requested_urls[0] == f"{STOREFRONT_API_URL}?collection=filter-coffee"
    assert scraper.client.requested_urls[1] == f"{STOREFRONT_API_URL}?collection=filter-coffee&cursor=CURSOR1"
    assert scraper.client.requested_urls[2] == f"{STOREFRONT_API_URL}?collection=samplebox"
    # Success must not mark the listing as failed.
    assert url not in scraper._failed_listing_urls


async def test_fetch_failure_records_failed_listing_url():
    scraper = _make_scraper()
    scraper.client = _FakeClient(RuntimeError("connection reset"))

    url = f"{LEGACY_BASE}/espresso-beans/products.json"
    products = await scraper._fetch_all_shopify_products(url)

    assert products == []
    assert url in scraper._failed_listing_urls


async def test_extract_product_urls_uses_legacy_identity_scheme():
    scraper = _make_scraper()
    fixture_products = [scraper._normalize_storefront_product(p) for p in _fixture_products()]
    # Add a subscription product that must be filtered out by exclude_slugs.
    fixture_products.append(
        scraper._normalize_storefront_product(
            {
                "id": "gid://shopify/Product/1",
                "handle": "organic-subscription",
                "title": "Organic Subscription",
                "description": "",
                "tags": [],
                "priceRange": {"minVariantPrice": {"amount": "199.0"}},
                "availableForSale": True,
            }
        )
    )

    async def fake_fetch(store_url):
        return fixture_products

    scraper._fetch_all_shopify_products = fake_fetch  # type: ignore[method-assign]

    urls = await scraper._extract_product_urls_from_store(f"{LEGACY_BASE}/filter-beans/products.json")

    assert len(urls) == len(_fixture_products())
    for url in urls:
        assert url.startswith(f"{LEGACY_BASE}/filter-beans/products/")
    assert f"{LEGACY_BASE}/filter-beans/products/volcan-azul-costa-rica-washed-sl28" in urls
    # Excluded slug never becomes a product URL.
    assert not any("subscription" in url for url in urls)
    # Product JSON and stock status recorded per URL for later enrichment.
    sample = f"{LEGACY_BASE}/filter-beans/products/volcan-azul-costa-rica-washed-sl28"
    assert scraper._shopify_product_data[sample]["handle"] == "volcan-azul-costa-rica-washed-sl28"
    assert scraper._shopify_stock_status[sample] is True


async def test_extract_failure_leaves_urls_empty():
    scraper = _make_scraper()

    async def failing_fetch(store_url):
        return []

    scraper._fetch_all_shopify_products = failing_fetch  # type: ignore[method-assign]

    urls = await scraper._extract_product_urls_from_store(f"{LEGACY_BASE}/filter-beans/products.json")

    assert urls == []


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (f"{LEGACY_BASE}/filter-beans/products/volcan-azul-costa-rica-washed-sl28", "Filter"),
        (f"{LEGACY_BASE}/espresso-beans/products/volcan-azul-costa-rica-washed-sl28-1", "Espresso"),
        # New storefront handles are accepted too (future URL scheme).
        (
            "https://www.aprilcoffeeroasters.com/product/tadesse-ethiopia-washed-krume-74158?collection=filter-coffee",
            "Filter",
        ),
        (
            "https://www.aprilcoffeeroasters.com/product/tadesse-ethiopia-washed-krume-74159?collection=espresso-coffee",
            "Espresso",
        ),
    ],
)
def test_roast_profile_mapping(url: str, expected: str):
    scraper = _make_scraper()
    bean = _make_bean(url)
    assert bean.roast_profile is None

    result = scraper.postprocess_extracted_bean(bean)

    assert result is not None
    assert result.roast_profile == expected
    assert result.currency == "DKK"


def test_roast_profile_unchanged_for_other_urls():
    scraper = _make_scraper()
    bean = _make_bean("https://www.aprilcoffeeroasters.com/product/some-other-bean")

    result = scraper.postprocess_extracted_bean(bean)

    assert result is not None
    assert result.roast_profile is None
