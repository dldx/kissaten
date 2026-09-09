"""Unit tests for the Pavlov's Coffee scraper (fixture-based, no network).

The fixture is a trimmed copy of the real WooCommerce
``/product-category/coffee/`` archive (OceanWP theme; product pages under
``/shop/<slug>/``).
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.pavlovs import PavlovsScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> PavlovsScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return PavlovsScraper(api_key="test-api-key")


def _category_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "pavlovs_category_coffee.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("pavlovs")
    assert info is not None
    assert info.roaster_name == "Pavlov's Coffee"
    assert info.currency == "ZAR"
    assert info.country == "South Africa"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Pavlov's Coffee"


async def test_store_urls():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert "https://pavlovscoffee.co.za/shop/" in urls
    assert "https://pavlovscoffee.co.za/product-category/coffee/" in urls


async def test_extracts_all_products_from_category_fixture(monkeypatch):
    scraper = _make_scraper()
    seen_urls: list[str] = []

    async def fake_fetch(url, **kwargs):
        seen_urls.append(url)
        return _category_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://pavlovscoffee.co.za/product-category/coffee/")

    # All four real products from the fixture are found, each exactly once.
    assert set(urls) == {
        "https://pavlovscoffee.co.za/shop/burundi-mutambu-hill-shg/",
        "https://pavlovscoffee.co.za/shop/single-origin-organic-honduras-copan/",
        "https://pavlovscoffee.co.za/shop/colombia-supremo-shg-organic/",
        "https://pavlovscoffee.co.za/shop/brazil-santos-bourbon/",
    }
    # The fixture archive has no next-page link, so the walk stops after
    # page 1 without fetching a 404 page 2.
    assert seen_urls == ["https://pavlovscoffee.co.za/product-category/coffee/"]


async def test_pagination_follows_next_page_link(monkeypatch):
    scraper = _make_scraper()
    page1 = BeautifulSoup(
        '<html><body><ul class="products">'
        '<li class="entry product"><a class="woocommerce-LoopProduct-link" '
        'href="https://pavlovscoffee.co.za/shop/page1-bean/">P1</a></li>'
        '</ul>'
        '<a class="next page-numbers" href="https://pavlovscoffee.co.za/shop/page/2/">Next</a>'
        "</body></html>",
        "lxml",
    )
    page2 = BeautifulSoup(
        '<html><body><ul class="products">'
        '<li class="entry product"><a class="woocommerce-LoopProduct-link" '
        'href="https://pavlovscoffee.co.za/shop/page2-bean/">P2</a></li>'
        "</ul></body></html>",
        "lxml",
    )

    async def fake_fetch(url, **kwargs):
        return page2 if "/page/2/" in url else page1

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://pavlovscoffee.co.za/shop/")
    assert set(urls) == {
        "https://pavlovscoffee.co.za/shop/page1-bean/",
        "https://pavlovscoffee.co.za/shop/page2-bean/",
    }


async def test_sold_out_card_is_excluded(monkeypatch):
    scraper = _make_scraper()
    soup = BeautifulSoup(
        '<html><body><ul class="products">'
        '<li class="entry product outofstock"><a class="woocommerce-LoopProduct-link" '
        'href="https://pavlovscoffee.co.za/shop/oos-bean/">OOS Bean</a>'
        "<p>Out of stock</p></li>"
        '<li class="entry product"><a class="woocommerce-LoopProduct-link" '
        'href="https://pavlovscoffee.co.za/shop/fresh-bean/">Fresh Bean</a>'
        "<p>R250.00</p></li>"
        "</ul></body></html>",
        "lxml",
    )

    async def fake_fetch(url, **kwargs):
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://pavlovscoffee.co.za/shop/")
    assert urls == ["https://pavlovscoffee.co.za/shop/fresh-bean/"]


async def test_shop_archive_root_and_feed_links_are_excluded(monkeypatch):
    scraper = _make_scraper()
    soup = BeautifulSoup(
        '<html><body>'
        '<a class="woocommerce-LoopProduct-link" href="https://pavlovscoffee.co.za/shop/">Shop</a>'
        '<a class="woocommerce-LoopProduct-link" href="https://pavlovscoffee.co.za/shop/feed/">RSS</a>'
        '<a class="woocommerce-LoopProduct-link" href="https://pavlovscoffee.co.za/shop/real-bean/">Real</a>'
        "</body></html>",
        "lxml",
    )

    async def fake_fetch(url, **kwargs):
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://pavlovscoffee.co.za/shop/")
    assert urls == ["https://pavlovscoffee.co.za/shop/real-bean/"]


async def test_subscription_urls_are_filtered(monkeypatch):
    scraper = _make_scraper()
    soup = BeautifulSoup(
        '<html><body><ul class="products">'
        '<li class="entry product"><a class="woocommerce-LoopProduct-link" '
        'href="https://pavlovscoffee.co.za/shop/coffee-subscription/">Subscription</a></li>'
        "</ul></body></html>",
        "lxml",
    )

    async def fake_fetch(url, **kwargs):
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://pavlovscoffee.co.za/shop/")
    assert urls == []


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://pavlovscoffee.co.za/shop/")
    assert urls == []


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://pavlovscoffee.co.za/shop/test-bean/",
        roaster="Pavlov's Coffee",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "ZAR"
