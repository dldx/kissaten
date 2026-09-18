"""Unit tests for the Gost Coffee Roasters scraper (fixture-based, no network).

Fixtures are trimmed copies of the real Wix store-products sitemap and product
detail pages (JSON-LD availability probe + ``div[data-hook="product-page"]``).
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.gost_coffee import GostCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

SITEMAP_URL = "https://www.gostcoffee.com/store-products-sitemap.xml"


def _make_scraper() -> GostCoffeeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return GostCoffeeScraper(api_key="test-api-key")


def _sitemap_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "gost_sitemap.xml").read_text(), "lxml")


def _product_soup(name: str) -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / f"gost_product_{name}.html").read_text(), "lxml")


def _probe_fetch(url, **kwargs):
    """Map candidate product URLs to their trimmed detail-page fixtures."""

    async def _inner():
        if "honduras-orlando-arita" in url or "burundi-kayanza" in url:
            return _product_soup("in_stock")
        if "colombia-orange-washed" in url or "pre-order-james-hoffmann-lucias-solis-fermentation-project" in url:
            return _product_soup("sold_out")
        return None

    return _inner()


async def test_registry_entry():
    info = get_registry().get_scraper_info("gost-coffee")
    assert info is not None
    assert info.roaster_name == "Gost Coffee Roasters"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Gost Coffee Roasters"


async def test_store_urls_use_store_products_sitemap():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == ["https://www.gostcoffee.com/store-products-sitemap.xml"]


async def test_extracts_coffee_urls_from_sitemap(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        if url == SITEMAP_URL:
            return _sitemap_soup()
        return await _probe_fetch(url, **kwargs)

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(SITEMAP_URL)
    assert "https://www.gostcoffee.com/product-page/honduras-orlando-arita" in urls
    assert "https://www.gostcoffee.com/product-page/burundi-kayanza" in urls
    # Every extracted URL uses the Wix /product-page/ path format.
    assert all("/product-page/" in u for u in urls)


async def test_non_coffee_slugs_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        if url == SITEMAP_URL:
            return _sitemap_soup()
        return await _probe_fetch(url, **kwargs)

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(SITEMAP_URL)
    # Tea, equipment, drinkware, ready-to-drink and instant sticks.
    for excluded in (
        "organic-assam-breakfast",
        "chemex-8-cup-glass-handle",
        "adventure-tumbler-red-rock",
        "cold-brew-coffee",
        "espresso-profile-12-sticks",
    ):
        assert excluded not in " ".join(urls)


async def test_sold_out_products_are_probed_and_skipped(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        if url == SITEMAP_URL:
            return _sitemap_soup()
        return await _probe_fetch(url, **kwargs)

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(SITEMAP_URL)
    # JSON-LD availability = OutOfStock on the detail page.
    assert "https://www.gostcoffee.com/product-page/colombia-orange-washed" not in urls
    assert (
        "https://www.gostcoffee.com/product-page/pre-order-james-hoffmann-lucias-solis-fermentation-project" not in urls
    )
    # In-stock products survive the probe.
    assert "https://www.gostcoffee.com/product-page/honduras-orlando-arita" in urls


async def test_probe_failure_treats_product_as_in_stock(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        if url == SITEMAP_URL:
            return _sitemap_soup()
        return None  # probe fetch fails

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    assert await scraper._product_is_in_stock("https://www.gostcoffee.com/product-page/honduras-orlando-arita")
    # And the URL survives extraction.
    urls = await scraper._extract_product_urls_from_store(SITEMAP_URL)
    assert "https://www.gostcoffee.com/product-page/honduras-orlando-arita" in urls


async def test_failed_sitemap_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(SITEMAP_URL)
    assert urls == []


async def test_fetch_page_narrows_product_pages(monkeypatch):
    scraper = _make_scraper()
    product_soup = BeautifulSoup(
        """
        <html><body>
          <nav>menu</nav>
          <div data-hook="product-page"><h1>Some Coffee</h1><p>Tasting notes</p></div>
          <footer>footer</footer>
        </body></html>
        """,
        "lxml",
    )

    async def fake_base_fetch(self, url, **kwargs):
        return product_soup

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_base_fetch)

    narrowed = await scraper.fetch_page(
        "https://www.gostcoffee.com/product-page/honduras-orlando-arita", use_playwright=False
    )
    assert narrowed is not None
    assert "Some Coffee" in narrowed.get_text()
    assert "menu" not in narrowed.get_text()

    # Sitemap pages are left untouched.
    sitemap = await scraper.fetch_page(SITEMAP_URL, use_playwright=False)
    assert "menu" in sitemap.get_text()


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://www.gostcoffee.com/product-page/test-bean",
        roaster="Gost Coffee Roasters",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "USD"
