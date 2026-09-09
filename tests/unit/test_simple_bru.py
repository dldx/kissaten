"""Unit tests for the Simple Bru Coffee Co scraper (fixture-based, no network).

The fixtures are trimmed copies of the real WooCommerce listing/product pages
(WordPress with default ``?product=`` permalinks and an Elementor product
grid on the Shop page).
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.simple_bru import SimpleBruScraper

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> SimpleBruScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return SimpleBruScraper(api_key="test-api-key")


def _shop_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "simple_bru_shop.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("simple-bru")
    assert info is not None
    assert info.roaster_name == "Simple Bru Coffee Co"
    assert info.currency == "ZAR"
    assert info.country == "South Africa"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Simple Bru Coffee Co"


async def test_store_urls_use_page_id_shop():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == ["https://simplebrucoffee.co.za/?page_id=1400"]


async def test_extracts_product_urls_from_shop_fixture(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://simplebrucoffee.co.za/?page_id=1400")
    assert "https://simplebrucoffee.co.za/?product=alternative-blend-250g" in urls
    # Every extracted URL uses the ?product= permalink format.
    assert all("?product=" in u for u in urls)


async def test_sold_out_card_is_excluded(monkeypatch):
    scraper = _make_scraper()
    sold_out_soup = BeautifulSoup(
        '<html><body><ul class="products">'
        '<li class="product outofstock"><a class="woocommerce-LoopProduct-link" '
        'href="https://simplebrucoffee.co.za/?product=sold-out-bean">Sold Out Bean</a>'
        "<p>Out of stock</p></li>"
        '<li class="product"><a class="woocommerce-LoopProduct-link" '
        'href="https://simplebrucoffee.co.za/?product=fresh-bean">Fresh Bean</a>'
        "<p>R250.00</p></li>"
        "</ul></body></html>",
        "lxml",
    )

    async def fake_fetch(url, **kwargs):
        return sold_out_soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://simplebrucoffee.co.za/?page_id=1400")
    assert urls == ["https://simplebrucoffee.co.za/?product=fresh-bean"]


async def test_sold_out_text_detection_without_class(monkeypatch):
    scraper = _make_scraper()
    soup = BeautifulSoup(
        '<html><body><ul class="products">'
        '<li class="product"><a class="woocommerce-LoopProduct-link" '
        'href="https://simplebrucoffee.co.za/?product=oos-bean">OOS Bean</a>'
        "<p>Out of stock</p></li>"
        "</ul></body></html>",
        "lxml",
    )

    async def fake_fetch(url, **kwargs):
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://simplebrucoffee.co.za/?page_id=1400")
    assert urls == []


async def test_non_product_and_excluded_urls_are_filtered(monkeypatch):
    scraper = _make_scraper()
    soup = BeautifulSoup(
        '<html><body><ul class="products">'
        '<li class="product"><a class="woocommerce-LoopProduct-link" '
        'href="https://simplebrucoffee.co.za/?product=coffee-subscription">Subscription</a></li>'
        '<li class="product"><a class="woocommerce-LoopProduct-link" '
        'href="https://simplebrucoffee.co.za/?product=gift-card">Gift card</a></li>'
        '<li class="product"><a class="woocommerce-LoopProduct-link" '
        'href="https://simplebrucoffee.co.za/?add-to-cart=123">Add to cart</a></li>'
        "</ul></body></html>",
        "lxml",
    )

    async def fake_fetch(url, **kwargs):
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://simplebrucoffee.co.za/?page_id=1400")
    assert urls == []


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://simplebrucoffee.co.za/?page_id=1400")
    assert urls == []


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://simplebrucoffee.co.za/?product=test-bean",
        roaster="Simple Bru Coffee Co",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "ZAR"
