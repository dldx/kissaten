"""Unit tests for the Quaffee scraper (fixture-based, no network).

The fixtures are trimmed copies of the real WooCommerce
``/product-category/coffee/`` archive pages 1 and 2 (Astra theme; product
pages under ``/offerings/<slug>/``).
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.quaffee import QuaffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

CATEGORY_URL = "https://quaffee.co.za/product-category/coffee/"


def _make_scraper() -> QuaffeeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return QuaffeeScraper(api_key="test-api-key")


def _page1_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "quaffee_category_coffee.html").read_text(), "lxml")


def _page2_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "quaffee_category_coffee_page2.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("quaffee")
    assert info is not None
    assert info.roaster_name == "Quaffee"
    assert info.currency == "ZAR"
    assert info.country == "South Africa"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Quaffee"


async def test_store_urls_cover_roasted_and_green_coffee():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert "https://quaffee.co.za/product-category/coffee/" in urls
    assert "https://quaffee.co.za/product-category/green-coffee/" in urls


async def test_extracts_all_products_across_pagination(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        if url.endswith("/page/2/"):
            return _page2_soup()
        if url.endswith("/page/3/"):
            # Page 3 does not exist: a 404 archive with no product loop.
            return BeautifulSoup("<html><body><p>404</p></body></html>", "lxml")
        return _page1_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(CATEGORY_URL)

    # 12 products on page 1 + 5 on page 2, minus the coffee-beans
    # subscription which is filtered out — all under /offerings/.
    assert len(urls) == 16
    assert all("/offerings/" in u for u in urls)
    assert "https://quaffee.co.za/offerings/old-school/" in urls
    assert "https://quaffee.co.za/offerings/colombian-atunkaa-decaf/" in urls


async def test_subscription_and_services_are_filtered(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        if url.endswith("/page/2/"):
            return _page2_soup()
        if url.endswith("/page/3/"):
            return BeautifulSoup("<html><body><p>404</p></body></html>", "lxml")
        return _page1_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(CATEGORY_URL)

    # The coffee-beans subscription product appears in the real loop and must
    # be filtered out; services like the coffee tasting experience must never
    # leak in either.
    assert not any("subscription" in u for u in urls)
    assert not any("tasting-experience" in u for u in urls)


async def test_sold_out_card_is_excluded(monkeypatch):
    scraper = _make_scraper()
    soup = BeautifulSoup(
        '<html><body><ul class="products">'
        '<li class="product type-product outofstock"><a class="woocommerce-LoopProduct-link" '
        'href="https://quaffee.co.za/offerings/oos-bean/">OOS Bean</a>'
        "<p>Out of stock</p></li>"
        '<li class="product type-product"><a class="woocommerce-LoopProduct-link" '
        'href="https://quaffee.co.za/offerings/fresh-bean/">Fresh Bean</a>'
        "<p>R115.00</p></li>"
        "</ul></body></html>",
        "lxml",
    )

    async def fake_fetch(url, **kwargs):
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(CATEGORY_URL)
    assert urls == ["https://quaffee.co.za/offerings/fresh-bean/"]


async def test_navigation_widget_links_do_not_leak(monkeypatch):
    scraper = _make_scraper()
    soup = BeautifulSoup(
        '<html><body>'
        # Navigation/widget links carrying /offerings/ but no loop-link class:
        '<a href="https://quaffee.co.za/offerings/cart/">Cart</a>'
        '<a href="https://quaffee.co.za/offerings/my-account/">My account</a>'
        '<a href="https://quaffee.co.za/offerings/timemore-product-line/">Timemore</a>'
        '<a href="https://quaffee.co.za/offerings/coffee-tasting-experience/">Tasting</a>'
        # The only real product link:
        '<li class="product type-product"><a class="woocommerce-LoopProduct-link" '
        'href="https://quaffee.co.za/offerings/bunna-blend/">Bunna</a></li>'
        "</body></html>",
        "lxml",
    )

    async def fake_fetch(url, **kwargs):
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(CATEGORY_URL)
    assert urls == ["https://quaffee.co.za/offerings/bunna-blend/"]


async def test_empty_first_page_marks_listing_failed(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return BeautifulSoup("<html><body><p>empty archive</p></body></html>", "lxml")

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    # discover_all_product_urls() (the scrape() entry point) applies the
    # failed-listing guard so out-of-stock updates are skipped rather than
    # poisoning the history when a listing yields nothing.
    urls = await scraper.discover_all_product_urls()
    assert urls == []
    assert CATEGORY_URL in scraper._failed_listing_urls


async def test_failed_fetch_returns_empty_and_marks_listing_failed(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper.discover_all_product_urls()
    assert urls == []
    assert CATEGORY_URL in scraper._failed_listing_urls


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://quaffee.co.za/offerings/test-bean/",
        roaster="Quaffee",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "ZAR"
