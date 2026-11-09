"""Fixture-based tests for the Wanderlust Espresso scraper.

The Wix listing at ``/coffee-beans`` is JS-rendered, so the listing fetch is
routed through Playwright. The current storefront renders each product as a
``[data-hook="product-widget"]`` card; the stock signal is the card's
``product-widget-OutOfStock`` badge and/or the ``action-button`` text/state
(the hidden quick-view ``product-item-root`` templates contain "Out of Stock"
text for every product, so whole-card text sniffing must not be used). These
tests exercise ``_extract_product_urls_from_store`` against a realistic
fixture of the listing page, verifying:
  * in-stock product URLs (``/product-page/...``) are found on widget cards,
  * sold-out cards (OutOfStock badge) are skipped,
  * the legacy ``product-item-root`` fallback uses the add-to-cart button
    state, not whole-card text.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from bs4 import BeautifulSoup

from kissaten.scrapers.wanderlust import WanderlustEspressoScraper

FIXTURE = Path(__file__).parent.parent / "fixtures" / "wanderlust_coffee_beans.html"


def _load_fixture_soup() -> BeautifulSoup:
    return BeautifulSoup(FIXTURE.read_text(encoding="utf-8"), "lxml")


@pytest.fixture
def scraper() -> WanderlustEspressoScraper:
    return WanderlustEspressoScraper(api_key="test-fake-key")


def test_store_urls_point_at_coffee_beans_listing(scraper):
    """get_store_urls returns the coffee-beans Wix listing page."""
    urls = asyncio.run(scraper.get_store_urls())
    assert urls == ["https://www.wanderlust-espresso.com/coffee-beans"]


def test_extract_product_urls_from_wix_listing(scraper):
    """In-stock widget cards are found; badge-carrying sold-out cards skipped."""
    soup = _load_fixture_soup()
    scraper.fetch_page = AsyncMock(return_value=soup)

    urls = asyncio.run(scraper._extract_product_urls_from_store("https://www.wanderlust-espresso.com/coffee-beans"))

    # In-stock product present
    assert "https://www.wanderlust-espresso.com/product-page/house-blend" in urls
    # Sold-out product skipped (OutOfStock badge on the card)
    assert "https://www.wanderlust-espresso.com/product-page/cosmic-blend" not in urls
    # Only the in-stock product remains (quick-view templates are not counted)
    assert urls == ["https://www.wanderlust-espresso.com/product-page/house-blend"]


def test_legacy_product_item_root_uses_button_state(scraper):
    """Legacy product-item-root fallback keys on the add-to-cart button state,
    not the card text (which contains hidden quick-view 'Out of Stock' copy)."""
    soup = BeautifulSoup(
        """
        <div data-hook="product-item-root">
          <a href="https://www.wanderlust-espresso.com/product-page/house-blend"></a>
          <button data-hook="product-item-add-to-cart-button">Add to Cart</button>
          <span>Quick View House Blend Price £8.00 Out of Stock</span>
        </div>
        <div data-hook="product-item-root">
          <a href="https://www.wanderlust-espresso.com/product-page/cosmic-blend"></a>
          <button data-hook="product-item-add-to-cart-button" disabled="">Out of Stock</button>
        </div>
        """,
        "lxml",
    )
    scraper.fetch_page = AsyncMock(return_value=soup)

    urls = asyncio.run(scraper._extract_product_urls_from_store("https://www.wanderlust-espresso.com/coffee-beans"))

    assert urls == ["https://www.wanderlust-espresso.com/product-page/house-blend"]


def test_extract_product_urls_uses_playwright_for_listing(scraper):
    """The listing fetch is routed through Playwright (JS-rendered Wix page)."""
    captured_kwargs = {}
    soup = _load_fixture_soup()

    async def fake_fetch(url, **kwargs):
        captured_kwargs.update(kwargs)
        return soup

    scraper.fetch_page = fake_fetch
    asyncio.run(scraper._extract_product_urls_from_store("https://www.wanderlust-espresso.com/coffee-beans"))
    assert captured_kwargs.get("use_playwright") is True


def test_extract_product_urls_handles_fetch_failure(scraper):
    """A None fetch result yields no URLs without raising."""
    scraper.fetch_page = AsyncMock(return_value=None)
    urls = asyncio.run(scraper._extract_product_urls_from_store("https://www.wanderlust-espresso.com/coffee-beans"))
    assert urls == []
