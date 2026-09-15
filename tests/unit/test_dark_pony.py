"""Unit tests for the Dark Pony scraper (fixture-based, no network).

The fixture is a trimmed copy of the store's real products.json payload.
"""

import json
from pathlib import Path

from kissaten.scrapers.dark_pony import DarkPonyScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://darkponycoffee.com/collections/coffee/products.json"
EXPECTED_STORE_URLS = ["https://darkponycoffee.com/collections/coffee/products.json"]


def _make_scraper() -> DarkPonyScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return DarkPonyScraper(api_key="test-api-key")


def _fixture_products() -> list[dict]:
    data = json.loads((FIXTURES / "dark_pony_products.json").read_text())
    return data["products"]


async def _extract_urls(scraper, monkeypatch):
    products = _fixture_products()

    async def fake_fetch(products_json_url):
        return products

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    return await scraper._extract_product_urls_from_store(STORE_URL)


def test_registry_entry():
    info = get_registry().get_scraper_info("dark-pony")
    assert info is not None
    assert info.name == "dark-pony"
    assert info.roaster_name == "Dark Pony"
    assert info.display_name == "Dark Pony"
    assert info.currency == "GBP"
    assert info.country == "United Kingdom"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Dark Pony"
    info = get_registry().get_scraper_info("dark-pony")
    assert info is not None
    assert scraper.roaster_name == info.roaster_name


def test_store_currency_pinned():
    scraper = _make_scraper()
    assert scraper.store_currency == "GBP"
    assert scraper._currency_detected is True


async def test_store_urls():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == EXPECTED_STORE_URLS


async def test_extracts_canonical_product_urls(monkeypatch):
    scraper = _make_scraper()
    urls = await _extract_urls(scraper, monkeypatch)

    # Canonical no-collection URL form, matching the site's product sitemap.
    assert all(u.startswith("https://darkponycoffee.com") and "/products/" in u for u in urls)
    assert not any("/collections/" in u for u in urls)

    # All curated-coffee products (incl. the kit) are extracted.
    assert "https://darkponycoffee.com/products/the-fermentation-project-kit" in urls
    assert "https://darkponycoffee.com/products/hambella-natural" in urls


async def test_postprocess_pins_currency():
    from kissaten.schemas import CoffeeBean

    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://darkponycoffee.com/products/test-bean/",
        roaster="Dark Pony",
        origins=[],
        price_options=[],
        currency="GBP",  # wrong on purpose; postprocess must overwrite
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out is not None
    assert out.currency == "GBP"


def test_preprocess_product_soup_prunes_to_product_info():
    from bs4 import BeautifulSoup

    scraper = _make_scraper()
    soup = BeautifulSoup(
        """
        <html><body>
          <header>Giant nav header</header>
          <div class="product__info-wrapper">
            <h1>Hambella Natural</h1>
            <p>Mango, Dried Strawberry, Coconut Milk</p>
            <accordion-block>
              <div class="accordion__panel">
                <p>Origin // Ethiopia</p><p>Elevation // 1,900 - 2,200 M.A.S.L</p>
              </div>
            </accordion-block>
          </div>
          <footer>Footer with lots of unrelated text</footer>
        </body></html>
        """,
        "lxml",
    )
    pruned = scraper.preprocess_product_soup(soup)
    text = pruned.get_text(" ", strip=True)
    assert "Hambella Natural" in text
    assert "Origin // Ethiopia" in text
    assert "Giant nav header" not in text
    assert "Footer with lots of unrelated text" not in text
