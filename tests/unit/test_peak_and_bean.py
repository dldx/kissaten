"""Unit tests for the Peak and Bean scraper (fixture-based, no network).

Peak and Bean sells via an Odoo eCommerce shop (odoo.peakandbeans.com); the
fixtures are trimmed copies of the real ``/en/shop`` listing page
(``div.oe_product`` cards) and a product detail page (``.o_wsale_product_page``).
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.peak_and_bean import PeakAndBeanScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://odoo.peakandbeans.com/en/shop"


def _make_scraper() -> PeakAndBeanScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return PeakAndBeanScraper(api_key="test-api-key")


def _shop_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "peak_and_bean_shop.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("peak-and-bean")
    assert info is not None
    assert info.roaster_name == "Peak and Bean"
    assert info.currency == "GTQ"
    assert info.country == "Guatemala"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Peak and Bean"


async def test_store_url_is_odoo_shop():
    scraper = _make_scraper()
    assert await scraper.get_store_urls() == [STORE_URL]


async def test_extracts_coffee_product_urls_from_listing_fixture(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)
    assert "https://odoo.peakandbeans.com/en/shop/blend-h-2129" in urls
    assert "https://odoo.peakandbeans.com/en/shop/bourbon-h-lavado-2123" in urls
    # Every extracted URL uses the Odoo /shop/<slug>-<id> format.
    assert all("/shop/" in u for u in urls)


async def test_sold_out_card_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)
    # Gesha card carries the "Agotado" ribbon in the fixture.
    assert "https://odoo.peakandbeans.com/en/shop/gesha-natural-atitlan-panorama-2143" not in urls


async def test_equipment_products_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)
    # Fellow Ode grinder and V60 dripper must not leak through.
    assert not any("ode-gen" in u for u in urls)
    assert not any("dripper" in u for u in urls)


async def test_sold_out_text_detection_without_ribbon_class(monkeypatch):
    scraper = _make_scraper()
    soup = BeautifulSoup(
        "<html><body>"
        '<div class="oe_product"><a class="oe_product_image_link" '
        'href="/en/shop/bourbon-h-natural-2122"><span>Bourbon H Natural</span></a>'
        "<p>Out of stock</p></div>"
        "</body></html>",
        "lxml",
    )
    urls = scraper._extract_product_urls_from_listing_soup(soup)
    assert urls == []


async def test_pagination_stops_when_fetch_fails(monkeypatch):
    scraper = _make_scraper()
    fetched = []

    async def fake_fetch(url, **kwargs):
        fetched.append(url)
        if "page/2" in url:
            return None  # 404 past the last page
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)
    assert "https://odoo.peakandbeans.com/en/shop/blend-h-2129" in urls
    assert fetched[0] == STORE_URL
    assert fetched[1] == f"{STORE_URL}/page/2"
    assert len(fetched) == 2  # stopped after the failed page-2 fetch


async def test_failed_first_page_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)
    assert urls == []


def test_narrow_product_soup_returns_odoo_container():
    scraper = _make_scraper()
    soup = BeautifulSoup((FIXTURES / "peak_and_bean_product.html").read_text(), "lxml")
    narrowed = scraper._narrow_product_soup(soup)

    assert narrowed.select_one("#product_details") is not None
    assert "Blend H" in narrowed.get_text(" ", strip=True)
    assert "panela" in narrowed.get_text(" ", strip=True)
    # Nav/footer content outside the product container must be stripped.
    assert "money-back guarantee" not in narrowed.get_text(" ", strip=True)
    assert "must be stripped" not in narrowed.get_text(" ", strip=True)


def test_narrow_product_soup_falls_back_to_full_page():
    scraper = _make_scraper()
    soup = BeautifulSoup("<html><body><p>no container</p></body></html>", "lxml")
    narrowed = scraper._narrow_product_soup(soup)
    assert narrowed is not None
    assert "no container" in narrowed.get_text()


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://odoo.peakandbeans.com/en/shop/blend-h-2129",
        roaster="Peak and Bean",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "GTQ"
