"""Unit tests for the Aero Coffee Roasters scraper (fixture-based, no network).

The fixture is a trimmed copy of the real Wix shop listing
(``/shop``) with the ``[data-hook="product-item-root"]`` cards and
"Out of Stock" markers the live site renders.
"""

from pathlib import Path

from bs4 import BeautifulSoup, Tag

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.aero_coffee import AeroCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> AeroCoffeeScraper:
    return AeroCoffeeScraper(api_key="test-api-key")


def _shop_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "aero_coffee_shop.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("aero-coffee")
    assert info is not None
    assert info.roaster_name == "Aero Coffee Roasters"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Aero Coffee Roasters"


async def test_store_urls_use_wix_shop():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == ["https://www.aerocoffeeroasters.com/shop"]


async def test_extracts_product_urls_from_shop_fixture(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.aerocoffeeroasters.com/shop")
    # Every extracted URL uses the Wix /product-page/ permalink format.
    assert all("/product-page/" in u for u in urls)
    assert "https://www.aerocoffeeroasters.com/product-page/kenya-tegu-aa" in urls
    assert "https://www.aerocoffeeroasters.com/product-page/the-fermentation-project-set" in urls


async def test_sold_out_card_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.aerocoffeeroasters.com/shop")
    assert "https://www.aerocoffeeroasters.com/product-page/finca-la-maria-light-roast" not in urls


async def test_non_coffee_urls_are_filtered(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.aerocoffeeroasters.com/shop")
    assert urls == [
        "https://www.aerocoffeeroasters.com/product-page/kenya-tegu-aa",
        "https://www.aerocoffeeroasters.com/product-page/the-fermentation-project-set",
    ]


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.aerocoffeeroasters.com/shop")
    assert urls == []


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://www.aerocoffeeroasters.com/product-page/test-bean",
        roaster="Aero Coffee Roasters",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "USD"


async def test_fetch_page_narrows_wix_product_container(monkeypatch):
    scraper = _make_scraper()

    product_html = (
        "<html><head></head><body><nav>menu</nav>"
        "<div data-hook='product-page'><h1>Kenya Tegu AA</h1><p>Notes</p></div>"
        "<footer>footer</footer></body></html>"
    )
    captured: dict = {}

    async def fake_base_fetch(self, url, *args, **kwargs):
        captured["url"] = url
        return BeautifulSoup(product_html, "lxml")

    # Patch the base implementation so only the narrowing logic is exercised.
    monkeypatch.setattr("kissaten.scrapers.base.BaseScraper.fetch_page", fake_base_fetch)

    soup = await scraper.fetch_page(
        "https://www.aerocoffeeroasters.com/product-page/kenya-tegu-aa", use_playwright=False
    )
    assert isinstance(soup, Tag)
    assert soup.select_one("div[data-hook='product-page']") is None  # narrowed, not the wrapper
    assert "Kenya Tegu AA" in soup.get_text()
    assert "footer" not in soup.get_text()
    assert captured["url"] == "https://www.aerocoffeeroasters.com/product-page/kenya-tegu-aa"
