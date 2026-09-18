"""Unit tests for the Base Coat Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.base_coat_coffee import BaseCoatCoffeeScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "base_coat_coffee_products.json"
PRODUCTS_JSON_URLS = [
    "https://basecoatcoffee.com/collections/coffee/products.json",
    "https://basecoatcoffee.com/collections/archives/products.json",
]


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return BaseCoatCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("base-coat-coffee")
    assert info is not None
    assert info.display_name == "Base Coat"
    assert info.roaster_name == "Base Coat"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Base Coat"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = []
    for store_url in PRODUCTS_JSON_URLS:
        urls.extend(await scraper._extract_product_urls_from_store(store_url))

    assert all(u.startswith("https://basecoatcoffee.com/products/") for u in urls)
    assert "https://basecoatcoffee.com/products/paya-washed-caturra-pache-verde" in urls
    assert "https://basecoatcoffee.com/products/mikiyas-bogales-gerse-washed-landrace" in urls


@pytest.mark.asyncio
async def test_urls_dedupe_across_collections(scraper, mocker):
    mocker.patch.object(scraper, "get_store_urls", return_value=PRODUCTS_JSON_URLS)
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    # Production dedupes across collections in discover_all_product_urls.
    urls = await scraper.discover_all_product_urls()

    # Collection-prefixed URLs are normalized to /products/<handle>, so the
    # same product found in both collections deduplicates to one URL.
    assert len(urls) == len(set(urls))
    assert len(urls) == 7


@pytest.mark.asyncio
async def test_comparison_sets_and_archive_pages_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URLS[0])

    # A/B comparison sets and $0.00 drop-archive pages are coffee; kept and
    # left for the tasting-kit heuristics to flag rather than excluded.
    assert "https://basecoatcoffee.com/products/vinka-sidra-mosto-comparison-set" in urls
    assert "https://basecoatcoffee.com/products/drop-1" in urls


@pytest.mark.asyncio
async def test_clearance_lots_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URLS[0])

    assert "https://basecoatcoffee.com/products/garage-sale-50-off-past-releases" in urls


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True


def test_soup_prune_keeps_specs_and_accordions():
    html = """
    <html><body>
      <div class="product-details"><p>Varietal: <strong>Caturra</strong></p></div>
      <div class="accordion"><details><summary>Farm and Producer</summary>
        <div class="details-content"><p>Santos Pablo Ramirez</p></div></details></div>
      <nav class="header-drawer">Menu</nav>
      <div class="product-recommendations">Other beans</div>
    </body></html>
    """
    scraper = BaseCoatCoffeeScraper()
    minimal = scraper.preprocess_product_soup(BeautifulSoup(html, "lxml"))
    text = minimal.get_text(" ", strip=True)
    assert "Varietal:" in text
    assert "Farm and Producer" in text
    assert "Santos Pablo Ramirez" in text
    assert "Other beans" not in text
    assert "Menu" not in text
    # A valid body must survive so the Shopify JSON context can be injected.
    assert minimal.body is not None
