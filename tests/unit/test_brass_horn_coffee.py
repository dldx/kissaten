"""Unit tests for the Brass Horn Coffee Roasters scraper (fixture-based, no network).

The fixture is a trimmed copy of the Square Online "Coffee" category listing with
``product-card`` containers, an "Out of Stock" card and merch/equipment cards.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.brass_horn_coffee import BrassHornCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> BrassHornCoffeeScraper:
    return BrassHornCoffeeScraper(api_key="test-api-key")


def _listing_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "brass_horn_coffee_shop.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("brass-horn-coffee")
    assert info is not None
    assert info.roaster_name == "Brass Horn Coffee Roasters"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Brass Horn Coffee Roasters"


async def test_store_urls_use_coffee_category():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == ["https://www.brasshorncoffee.com/shop/coffee/2"]


async def test_extracts_product_urls_from_listing_fixture(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.brasshorncoffee.com/shop/coffee/2")
    # Every extracted URL uses the /product/<slug>/<id>/ format.
    assert all("/product/" in u for u in urls)
    assert "https://www.brasshorncoffee.com/product/moon-walker/284" in urls


async def test_sold_out_card_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.brasshorncoffee.com/shop/coffee/2")
    assert "https://www.brasshorncoffee.com/product/el-eden-8oz/3YDGNQOBF2CVDXSITVQNLHV6" not in urls


async def test_merch_and_equipment_are_filtered(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.brasshorncoffee.com/shop/coffee/2")
    # The roasters-choice sample box must be kept (tasting-kit flagging is downstream).
    assert "https://www.brasshorncoffee.com/product/sample-box-roasters-choice/81" in urls
    assert not any("grinder" in u for u in urls)
    assert not any("tees" in u for u in urls)
    assert urls == [
        "https://www.brasshorncoffee.com/product/moon-walker/284",
        "https://www.brasshorncoffee.com/product/sample-box-roasters-choice/81",
    ]


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.brasshorncoffee.com/shop/coffee/2")
    assert urls == []


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://www.brasshorncoffee.com/product/test-bean/123",
        roaster="Brass Horn Coffee Roasters",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "USD"
