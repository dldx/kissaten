"""Unit tests for the Roastopus scraper (fixture-based, no network).

Roastopus is a custom Laravel + Vue storefront with server-rendered JSON-LD and
a Vue price component; the fixtures mirror both category and product pages.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.roastopus import RoastopusScraper

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> RoastopusScraper:
    return RoastopusScraper(api_key="test-api-key")


def _category_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "roastopus_category.html").read_text(), "lxml")


def _product_soup(availability: str = "InStock") -> BeautifulSoup:
    html = (FIXTURES / "roastopus_product.html").read_text().replace("schema.org/InStock", f"schema.org/{availability}")
    return BeautifulSoup(html, "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("roastopus")
    assert info is not None
    assert info.roaster_name == "Roastopus"
    assert info.currency == "HUF"
    assert info.country == "Hungary"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    assert _make_scraper().roaster_name == "Roastopus"


async def test_store_urls():
    scraper = _make_scraper()
    assert await scraper.get_store_urls() == [
        "https://roastopus.com/hu/termekeink/kaveink-espresso",
        "https://roastopus.com/hu/termekeink/kaveink-filter",
    ]


def test_product_url_detection():
    scraper = _make_scraper()
    assert scraper._is_product_url("https://roastopus.com/hu/termekeink/kaveink-espresso/siren-100025")
    assert not scraper._is_product_url("https://roastopus.com/hu/termekeink/kaveink-espresso")
    assert not scraper._is_product_url("https://roastopus.com/hu/termekeink/kaveink-filter")


def test_item_list_extraction():
    urls = RoastopusScraper._extract_item_list_urls(_category_soup())
    assert urls == [
        "https://roastopus.com/hu/termekeink/kaveink-espresso/the-fermentation-project-100115",
        "https://roastopus.com/hu/termekeink/kaveink-espresso/siren-100025",
        "https://roastopus.com/hu/termekeink/kaveink-espresso/black-pearl-100002",
    ]


def test_price_and_availability_extraction():
    soup = _product_soup()
    assert RoastopusScraper._extract_price_lines(soup) == [
        "- Price: 4390 Ft",
        "- Price: 5490 Ft",
        "- Price: 19990 Ft",
    ]
    assert RoastopusScraper._extract_availability(soup) == "InStock"
    assert RoastopusScraper._extract_availability(_product_soup("OutOfStock")) == "OutOfStock"


async def test_extract_product_urls_skips_sold_out(monkeypatch):
    scraper = _make_scraper()

    async def fake_super_fetch(self, url, *args, **kwargs):
        if url.rstrip("/").endswith("kaveink-espresso") and "/siren" not in url:
            return _category_soup()
        if "black-pearl" in url:
            return _product_soup("OutOfStock")
        return _product_soup("InStock")

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_super_fetch)
    urls = await scraper._extract_product_urls_from_store("https://roastopus.com/hu/termekeink/kaveink-espresso")

    assert "https://roastopus.com/hu/termekeink/kaveink-espresso/siren-100025" in urls
    assert "https://roastopus.com/hu/termekeink/kaveink-espresso/the-fermentation-project-100115" in urls
    assert "https://roastopus.com/hu/termekeink/kaveink-espresso/black-pearl-100002" not in urls


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_super_fetch(self, url, *args, **kwargs):
        return None

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_super_fetch)
    assert await scraper._extract_product_urls_from_store("https://roastopus.com/hu/termekeink/kaveink-espresso") == []


async def test_fetch_page_narrows_product_datasheet(monkeypatch):
    scraper = _make_scraper()
    product = _product_soup()

    async def fake_super_fetch(self, url, *args, **kwargs):
        return product

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_super_fetch)
    result = await scraper.fetch_page("https://roastopus.com/hu/termekeink/kaveink-espresso/siren-100025")

    assert result is not None
    text = result.get_text(" ", strip=True)
    assert "SIREN" in text
    assert "Kirinyaga" in text
    # Prices (invisible in the rendered text) and availability are injected.
    assert "4390 Ft" in text
    assert "Availability: InStock" in text
    # Narrowed to section.product-datasheet.
    assert "product-card" not in str(result)


def test_review_flags_for_tasting_products():
    scraper = _make_scraper()
    for url in (
        "https://roastopus.com/hu/termekeink/kaveink-espresso/the-fermentation-project-100115",
        "https://roastopus.com/hu/termekeink/kaveink-filter/filter-minicsomag-100056",
    ):
        bean = CoffeeBean(
            name="Test",
            url=url,
            roaster="Roastopus",
            origins=[],
            price_options=[],
            currency="HUF",
        )
        scraper.postprocess_review_flags(bean, url)
        assert bean.is_tasting_kit is True


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://roastopus.com/hu/termekeink/kaveink-espresso/test-bean-100000",
        roaster="Roastopus",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    assert scraper.postprocess_extracted_bean(bean).currency == "HUF"
