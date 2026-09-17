"""Unit tests for the Movement Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from kissaten.scrapers.movement_coffee import MovementCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "movement_coffee_products.json"
PRODUCTS_JSON_URL = "https://movementcoffee.com/collections/buy-coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return MovementCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("movement-coffee")
    assert info is not None
    assert info.roaster_name == "Movement Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Movement Coffee"


def test_page_extraction_enabled(scraper):
    # The Coffee Info accordion (variety/farm/altitude) only exists on the page.
    assert scraper.scrape_product_pages is True
    assert scraper.use_optimized_mode is False


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://movementcoffee.com/products/") for u in urls)
    assert "https://movementcoffee.com/products/esmeralda-1" in urls
    assert "https://movementcoffee.com/products/house-blend-coffee" in urls


@pytest.mark.asyncio
async def test_sold_out_products_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Limited-stock sold-out lots (Esmeralda) remain listed and are kept.
    esmeralda = next(p for p in _fixture_products() if p["handle"] == "esmeralda-1")
    assert not any(v.get("available") for v in esmeralda["variants"])
    assert "https://movementcoffee.com/products/esmeralda-1" in urls


@pytest.mark.asyncio
async def test_rtd_and_gift_cards_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("cold-brew" in u for u in urls)
    assert not any("gift-card" in u for u in urls)


def test_preprocess_product_soup_keeps_description_and_accordions():
    soup = BeautifulSoup(
        """
        <html><body>
          <header>big site chrome</header>
          <div class="product__description rte"><p>Tasting Notes: Peach, Mandarin, Jasmine</p></div>
          <div class="product__accordion accordion">
            <details><summary>Coffee Info</summary>
              <div class="accordion__content rte">Variety: Geisha<br/>Farm: Hacienda Esmeralda, Panama</div>
            </details>
          </div>
          <footer>more chrome</footer>
        </body></html>
        """,
        "html.parser",
    )
    pruned = MovementCoffeeScraper().preprocess_product_soup(soup)

    text = pruned.get_text()
    assert "Peach, Mandarin" in text
    assert "Hacienda Esmeralda" in text
    assert "big site chrome" not in text
    assert "more chrome" not in text
    # A valid body must remain so the Shopify JSON context can be injected.
    assert pruned.body is not None


def test_preprocess_product_soup_passthrough_when_no_keepers():
    soup = BeautifulSoup("<html><body><p>plain page</p></body></html>", "html.parser")
    assert MovementCoffeeScraper().preprocess_product_soup(soup) is soup


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
