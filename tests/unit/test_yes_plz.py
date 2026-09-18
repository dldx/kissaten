"""Unit tests for the YES PLZ scraper (fixture-based, no network).

YES PLZ is a small custom Next.js storefront: the /shop listing links a fixed
set of server-rendered product pages, and stock state only appears on the
detail page as a visible "SOLD OUT" banner.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.yes_plz import YesPlzScraper

FIXTURES = Path(__file__).parent.parent / "fixtures"

SHOP_URL = "https://www.yesplz.coffee/shop"
MIX_URL = "https://www.yesplz.coffee/product/beans"
FERMENTATION_URL = "https://www.yesplz.coffee/product/fermentation-project"


def _make_scraper() -> YesPlzScraper:
    return YesPlzScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("yes-plz")
    assert info is not None
    assert info.roaster_name == "YES PLZ"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "YES PLZ"


async def test_store_urls_use_shop_page():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [SHOP_URL]


async def test_extracts_product_urls_and_skips_sold_out(monkeypatch):
    """Detail-page sold-out check: /shop links both, but the sold-out detail page is skipped."""
    scraper = _make_scraper()
    shop_soup = BeautifulSoup((FIXTURES / "yesplz_shop.html").read_text(), "lxml")
    mix_soup = BeautifulSoup((FIXTURES / "yesplz_product.html").read_text(), "lxml")
    fermentation_soup = BeautifulSoup((FIXTURES / "yesplz_product_soldout.html").read_text(), "lxml")

    async def fake_fetch(url, **kwargs):
        if url == SHOP_URL:
            return shop_soup
        if "fermentation-project" in url:
            return fermentation_soup
        return mix_soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(SHOP_URL)

    assert MIX_URL in urls
    assert FERMENTATION_URL not in urls  # visible "PRE-SALE SOLD OUT" banner
    assert all("/product/" in u for u in urls)
    assert all("/merch" not in u for u in urls)


async def test_in_stock_products_are_kept_when_detail_fetch_fails(monkeypatch):
    """A failed detail fetch must not silently drop the product."""
    scraper = _make_scraper()
    shop_soup = BeautifulSoup((FIXTURES / "yesplz_shop.html").read_text(), "lxml")

    async def fake_fetch(url, **kwargs):
        if url == SHOP_URL:
            return shop_soup
        return None  # detail fetch fails

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(SHOP_URL)

    assert MIX_URL in urls
    assert FERMENTATION_URL in urls


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(SHOP_URL)
    assert urls == []


async def test_merch_link_is_excluded(monkeypatch):
    scraper = _make_scraper()
    soup = BeautifulSoup(
        '<html><body><a href="/merch">Merch</a><a href="/product/beans">The Mix</a></body></html>',
        "lxml",
    )

    async def fake_fetch(url, **kwargs):
        if url == SHOP_URL:
            return soup
        return BeautifulSoup((FIXTURES / "yesplz_product.html").read_text(), "lxml")

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(SHOP_URL)
    assert urls == [MIX_URL]


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="The Mix",
        url=MIX_URL,
        roaster="YES PLZ",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "USD"
