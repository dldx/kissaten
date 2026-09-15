"""Unit tests for the Bean Machine scraper (fixture-based, no network).

The fixture is a trimmed copy of the real JetEngine-filtered WooCommerce
"Kaffe" category grid with the ``div.jet-woo-products__item`` cards,
``outofstock`` classes and "Udsolgt" markers the live site renders.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.bean_machine import BeanMachineScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> BeanMachineScraper:
    return BeanMachineScraper(api_key="test-api-key")


def _listing_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "bean_machine_coffee.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("bean-machine")
    assert info is not None
    assert info.roaster_name == "Bean Machine"
    assert info.currency == "DKK"
    assert info.country == "Denmark"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Bean Machine"


async def test_store_urls_use_kaffe_category_filter():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == ["https://www.beanmachine.dk/shop/?jsf=jet-woo-products-grid&tax=product_cat:17"]


async def test_extracts_product_urls_from_listing_fixture(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(
        "https://www.beanmachine.dk/shop/?jsf=jet-woo-products-grid&tax=product_cat:17"
    )
    # Every extracted URL uses the nyristet-kaffe permalink format.
    assert all("/shop/nyristet-kaffe/" in u for u in urls)
    assert "https://www.beanmachine.dk/shop/nyristet-kaffe/peru/" in urls
    assert "https://www.beanmachine.dk/shop/nyristet-kaffe/brazil/" in urls


async def test_sold_out_card_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(
        "https://www.beanmachine.dk/shop/?jsf=jet-woo-products-grid&tax=product_cat:17"
    )
    assert "https://www.beanmachine.dk/shop/nyristet-kaffe/kenya/" not in urls


async def test_equipment_links_are_filtered(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(
        "https://www.beanmachine.dk/shop/?jsf=jet-woo-products-grid&tax=product_cat:17"
    )
    assert not any("udstyr" in u for u in urls)
    assert urls == [
        "https://www.beanmachine.dk/shop/nyristet-kaffe/peru/",
        "https://www.beanmachine.dk/shop/nyristet-kaffe/brazil/",
    ]


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(
        "https://www.beanmachine.dk/shop/?jsf=jet-woo-products-grid&tax=product_cat:17"
    )
    assert urls == []


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://www.beanmachine.dk/shop/nyristet-kaffe/test-bean/",
        roaster="Bean Machine",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "DKK"
