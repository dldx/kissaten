"""Unit tests for the Merit Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from kissaten.scrapers.merit_coffee import MeritCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "merit_coffee_products.json"
PRODUCTS_JSON_URL = "https://meritcoffee.com/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return MeritCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("merit-coffee")
    assert info is not None
    assert info.roaster_name == "Merit"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Merit"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://meritcoffee.com/products/") for u in urls)
    assert "https://meritcoffee.com/products/ojo-de-agua-3" in urls
    assert "https://meritcoffee.com/products/camino-de-oro-cielo-andino" in urls


@pytest.mark.asyncio
async def test_subscriptions_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("subscription" in u for u in urls)


def test_page_extraction_enabled(scraper):
    assert scraper.scrape_product_pages is True
    assert scraper.use_optimized_mode is False


def test_preprocess_product_soup_keeps_specs_accordions():
    soup = BeautifulSoup(
        """
        <html><body>
          <nav>big site chrome</nav>
          <rte-formatter><p>Ganache • Maple Syrup • Dates</p></rte-formatter>
          <accordion-custom>
            <details><summary>Coffee Specs</summary>
              <div class="details-content"><p><strong>Process</strong><br/>Washed &amp; Natural</p></div>
            </details>
          </accordion-custom>
        </body></html>
        """,
        "html.parser",
    )
    pruned = MeritCoffeeScraper().preprocess_product_soup(soup)

    text = pruned.get_text()
    assert "Ganache" in text
    assert "Washed" in text
    assert "big site chrome" not in text
    # A valid body must remain so the Shopify JSON context can be injected.
    assert pruned.body is not None


def test_preprocess_product_soup_passthrough_when_no_keepers():
    soup = BeautifulSoup("<html><body><p>plain page</p></body></html>", "html.parser")
    assert MeritCoffeeScraper().preprocess_product_soup(soup) is soup


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
