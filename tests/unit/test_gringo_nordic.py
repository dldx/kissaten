"""Unit tests for the Gringo Nordic scraper (fixture-based, no network).

Gringo Nordic (gringonordic.se) runs a WooCommerce storefront with JetWooBuilder
archive cards; the fixture is a trimmed copy of the real
``/product-category/kaffe/`` listing page.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.gringo_nordic import GringoNordicScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://www.gringonordic.se/product-category/kaffe/"


def _make_scraper() -> GringoNordicScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return GringoNordicScraper(api_key="test-api-key")


def _listing_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "gringo_nordic_kaffe.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("gringo-nordic")
    assert info is not None
    assert info.roaster_name == "Gringo Nordic"
    assert info.currency == "SEK"
    assert info.country == "Sweden"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Gringo Nordic"


async def test_store_url_is_kaffe_category():
    scraper = _make_scraper()
    assert await scraper.get_store_urls() == [STORE_URL]


async def test_extracts_product_urls_from_listing_fixture(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)
    assert "https://www.gringonordic.se/product/colombia-las-moras/" in urls
    assert "https://www.gringonordic.se/product/mocca-blend/" in urls
    # Every extracted URL uses the WooCommerce /product/ permalink format.
    assert all("/product/" in u for u in urls)


async def test_sold_out_card_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)
    assert "https://www.gringonordic.se/product/burundi-nemba-kayanza/" not in urls


async def test_subscription_card_is_excluded_even_with_coffee_slug(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)
    # The variable-subscription product uses the slug /product/single-origin/ —
    # only the card-level product-type-*-subscription class can catch it.
    assert "https://www.gringonordic.se/product/single-origin/" not in urls


async def test_sold_out_text_detection_without_class(monkeypatch):
    scraper = _make_scraper()
    soup = BeautifulSoup(
        '<html><body><ul class="products">'
        '<li class="product type-product"><a href="https://www.gringonordic.se/product/oos-bean/">OOS Bean</a>'
        "<p>Slut i lager</p></li>"
        "</ul></body></html>",
        "lxml",
    )
    urls = scraper._extract_product_urls_from_listing_soup(soup)
    assert urls == ["https://www.gringonordic.se/product/oos-bean/"]


async def test_pagination_stops_when_fetch_fails(monkeypatch):
    scraper = _make_scraper()
    fetched = []

    async def fake_fetch(url, **kwargs):
        fetched.append(url)
        if "page/2" in url:
            return None  # 404 past the last page
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)
    assert "https://www.gringonordic.se/product/colombia-las-moras/" in urls
    assert fetched[0] == STORE_URL
    assert fetched[1] == f"{STORE_URL}page/2/"
    assert len(fetched) == 2  # stopped after the failed page-2 fetch


async def test_failed_first_page_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)
    assert urls == []


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://www.gringonordic.se/product/mocca-blend/",
        roaster="Gringo Nordic",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "SEK"
