"""Unit tests for the Curious Coffee scraper (fixture-based, no network).

The fixture is a trimmed copy of the real Wix "all-products" category listing
(server-rendered ``div[data-hook="product-item-root"]`` cards).
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.curious_coffee import CuriousCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> CuriousCoffeeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return CuriousCoffeeScraper(api_key="test-api-key")


def _category_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "curious_coffee_category.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("curious-coffee")
    assert info is not None
    assert info.roaster_name == "Curious Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Curious Coffee"


async def test_store_urls_use_wix_category():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == ["https://www.curious-coffee.com/category/all-products"]


async def test_extracts_product_urls_from_category_fixture(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _category_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.curious-coffee.com/category/all-products")
    assert "https://www.curious-coffee.com/product-page/jairo-arcila-natural-chiroso" in urls
    # The Fermentation Project tasting kit must not be excluded.
    assert "https://www.curious-coffee.com/product-page/the-fermentation-project" in urls
    # Every extracted URL uses the Wix /product-page/ path format.
    assert all("/product-page/" in u for u in urls)
    assert len(urls) == 2


async def test_sold_out_card_is_excluded(monkeypatch):
    # The fixture's second card carries "Out of stock" / "Unavailable" markers.
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _category_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.curious-coffee.com/category/all-products")
    assert "https://www.curious-coffee.com/product-page/marlon-bolaños-geisha-natural" not in urls


async def test_non_coffee_products_are_excluded(monkeypatch):
    scraper = _make_scraper()
    soup = BeautifulSoup(
        """
        <div data-hook="product-item-root">
          <a href="https://www.curious-coffee.com/product-page/monthly-coffee-subscription">Subscription</a>
        </div>
        <div data-hook="product-item-root">
          <a href="https://www.curious-coffee.com/product-page/curious-t-shirts">T-shirts</a>
        </div>
        <div data-hook="product-item-root">
          <a href="https://www.curious-coffee.com/product-page/mypressi-twist">Mypressi Twist</a>
        </div>
        <div data-hook="product-item-root">
          <a href="https://www.curious-coffee.com/product-page/fellow-aiden-precision-coffee-maker">Aiden</a>
        </div>
        """,
        "lxml",
    )

    async def fake_fetch(url, **kwargs):
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.curious-coffee.com/category/all-products")
    assert urls == []


async def test_pagination_stops_when_no_new_cards(monkeypatch):
    scraper = _make_scraper()
    calls = []

    async def fake_fetch(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            return _category_soup()
        # Page 2+ repeats the same soup (already-seen cards) then fails.
        if len(calls) == 2:
            return _category_soup()
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.curious-coffee.com/category/all-products")
    # Page 2 yields no *new* cards, so pagination stops and page 3 is never fetched.
    assert len(calls) == 2
    assert len(urls) == 2


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
        "https://www.curious-coffee.com/product-page/jairo-arcila-natural-chiroso",
        use_playwright=False,
    )
    assert narrowed is not None
    assert "Some Coffee" in narrowed.get_text()
    assert "menu" not in narrowed.get_text()

    # Listing pages are left untouched.
    listing = await scraper.fetch_page("https://www.curious-coffee.com/category/all-products", use_playwright=False)
    assert "menu" in listing.get_text()


async def test_fetch_page_returns_none_on_failure(monkeypatch):
    scraper = _make_scraper()

    async def fake_base_fetch(self, url, **kwargs):
        return None

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_base_fetch)
    result = await scraper.fetch_page("https://www.curious-coffee.com/product-page/x", use_playwright=False)
    assert result is None


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.curious-coffee.com/category/all-products")
    assert urls == []


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://www.curious-coffee.com/product-page/test-bean",
        roaster="Curious Coffee",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "USD"
