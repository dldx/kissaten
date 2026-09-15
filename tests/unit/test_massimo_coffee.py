"""Unit tests for the Massimo Coffee scraper (fixture-based, no network).

Massimo Coffee runs an Ecwid Instant Site storefront with server-rendered
``.grid-product`` cards and a ``div.static-product-browser`` product container.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.massimo_coffee import MassimoCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> MassimoCoffeeScraper:
    return MassimoCoffeeScraper(api_key="test-api-key")


def _listing_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "massimo_coffee_listing.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("massimo-coffee")
    assert info is not None
    assert info.roaster_name == "Massimo Coffee"
    assert info.currency == "KZT"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    assert _make_scraper().roaster_name == "Massimo Coffee"


async def test_store_urls():
    scraper = _make_scraper()
    assert await scraper.get_store_urls() == ["https://icoffee.store/products/"]


async def test_extracts_only_in_stock_coffee_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://icoffee.store/products/")

    assert "https://icoffee.store/products/kenya-gatina-aa" in urls
    assert "https://icoffee.store/products/ethiopia-daannisa-natural-847783762" in urls
    # Sold-out card text ("Нет в наличии") excludes the product.
    assert "https://icoffee.store/products/peru-monteverde-washed-espresso" not in urls
    # Russian grinder slug is excluded as equipment.
    assert "https://icoffee.store/products/kofemolka-c40-nitro-blade-sunset" not in urls


async def test_category_pages_are_excluded(monkeypatch):
    scraper = _make_scraper()
    soup = BeautifulSoup(
        "<html><body><div class='grid'>"
        "<div class='grid-product'><a href='https://icoffee.store/products/kofe'>КОФЕ</a></div>"
        "<div class='grid-product'><a href='https://icoffee.store/products/merch'>Мерч</a></div>"
        "</div></body></html>",
        "lxml",
    )

    async def fake_fetch(url, **kwargs):
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    assert await scraper._extract_product_urls_from_store("https://icoffee.store/products/") == []


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    assert await scraper._extract_product_urls_from_store("https://icoffee.store/products/") == []


async def test_fetch_page_narrows_product_detail(monkeypatch):
    scraper = _make_scraper()
    product = BeautifulSoup((FIXTURES / "massimo_coffee_product.html").read_text(), "lxml")

    async def fake_super_fetch(self, url, *args, **kwargs):
        return product

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_super_fetch)
    result = await scraper.fetch_page("https://icoffee.store/products/kenya-gatina-aa")

    assert result is not None
    text = result.get_text(" ", strip=True)
    assert "Kenya Gatina AA" in text
    assert "KZT 9 350" in text
    # Narrowed to div.static-product-browser: theme chrome is gone.
    assert "unrelated marketing copy" not in text


async def test_listing_page_is_not_narrowed(monkeypatch):
    scraper = _make_scraper()
    listing = _listing_soup()

    async def fake_super_fetch(self, url, *args, **kwargs):
        return listing

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_super_fetch)
    result = await scraper.fetch_page("https://icoffee.store/products/")
    assert result is not None
    assert len(result.select(".grid-product")) == 4


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://icoffee.store/products/test-bean",
        roaster="Massimo Coffee",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    assert scraper.postprocess_extracted_bean(bean).currency == "KZT"
