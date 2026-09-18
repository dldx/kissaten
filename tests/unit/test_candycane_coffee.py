"""Unit tests for the Candycane Coffee scraper (fixture-based, no network).

The fixture is a trimmed copy of the real Livewire coffee category listing
(``/kategorie/kava``) with the ``a[data-context="product_card"]`` cards and
"Vyprodáno" (sold-out) markers the live site renders.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.candycane_coffee import CandycaneCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> CandycaneCoffeeScraper:
    return CandycaneCoffeeScraper(api_key="test-api-key")


def _listing_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "candycane_coffee_shop.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("candycane-coffee")
    assert info is not None
    assert info.roaster_name == "Candycane Coffee"
    assert info.currency == "CZK"
    assert info.country == "Czechia"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Candycane Coffee"


async def test_store_urls_use_kava_category():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == ["https://www.candycane.coffee/kategorie/kava"]


async def test_extracts_product_urls_and_dedupes_mobile_cards(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.candycane.coffee/kategorie/kava")
    # Every extracted URL uses the /produkty/ permalink format.
    assert all("/produkty/" in u for u in urls)
    # The desktop + mobile duplicate cards collapse into one URL.
    assert urls.count("https://www.candycane.coffee/produkty/chelchele-8-etiopie") == 1
    assert "https://www.candycane.coffee/produkty/fredy-orantes-guatemala" in urls


async def test_sold_out_card_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.candycane.coffee/kategorie/kava")
    assert "https://www.candycane.coffee/produkty/buena-vista-gesha-guatemala" not in urls


async def test_subscriptions_chocolate_and_cascara_are_filtered(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.candycane.coffee/kategorie/kava")
    assert not any("home-office" in u for u in urls)
    assert not any("cokolad" in u for u in urls)
    assert urls == [
        "https://www.candycane.coffee/produkty/chelchele-8-etiopie",
        "https://www.candycane.coffee/produkty/fredy-orantes-guatemala",
    ]


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.candycane.coffee/kategorie/kava")
    assert urls == []


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://www.candycane.coffee/produkty/test-bean",
        roaster="Candycane Coffee",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "CZK"
