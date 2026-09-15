"""Unit tests for the Ief & Ido scraper (fixture-based, no network).

Ief & Ido runs WooCommerce; the fixtures mirror the ``li.product`` category
cards and the theme's ``div.product`` detail container.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.ief_ido import IefIdoScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> IefIdoScraper:
    return IefIdoScraper(api_key="test-api-key")


def _category_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "ief_ido_category.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("ief-ido")
    assert info is not None
    assert info.roaster_name == "Ief & Ido"
    assert info.currency == "EUR"
    assert info.country == "Netherlands"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    assert _make_scraper().roaster_name == "Ief & Ido"


async def test_store_urls():
    scraper = _make_scraper()
    assert await scraper.get_store_urls() == ["https://iefido.nl/product-categorie/coffee/"]


async def test_extracts_in_stock_coffee_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _category_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://iefido.nl/product-categorie/coffee/")

    assert "https://iefido.nl/product/brazil-do-lobo/" in urls
    # Tasting package is kept (tasting-kit flagging happens downstream).
    assert "https://iefido.nl/product/iefido-proefpakketje/" in urls
    # Out-of-stock products are excluded (class and text detection).
    assert "https://iefido.nl/product/colombia-bubblegum/" not in urls
    assert "https://iefido.nl/product/the-fermentation-project/" not in urls
    # Workshop products are excluded as non-coffee.
    assert "https://iefido.nl/product/workshop-espresso-basics/" not in urls


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    assert await scraper._extract_product_urls_from_store("https://iefido.nl/product-categorie/coffee/") == []


async def test_fetch_page_narrows_product_detail(monkeypatch):
    scraper = _make_scraper()
    soup = BeautifulSoup((FIXTURES / "ief_ido_category.html").read_text(), "lxml")
    product = BeautifulSoup(
        "<html><body><header>chrome</header>"
        "<div class='product product-layout-1 type-product'>"
        "<h1 class='product_title'>Brazil do Lobo</h1><div class='summary'>€ 10.50</div>"
        "</div><footer>more chrome</footer></body></html>",
        "lxml",
    )

    async def fake_super_fetch(self, url, *args, **kwargs):
        if "/product-categorie/" in url:
            return soup
        return product

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_super_fetch)
    result = await scraper.fetch_page("https://iefido.nl/product/brazil-do-lobo/")
    assert result is not None
    assert "Brazil do Lobo" in result.get_text()
    # Narrowed to the product container: page chrome is gone.
    assert "chrome" not in result.get_text()


def test_review_flags_for_tasting_packages():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Ief&Ido tasting package",
        url="https://iefido.nl/product/iefido-proefpakketje/",
        roaster="Ief & Ido",
        origins=[],
        price_options=[],
        currency="EUR",
    )
    scraper.postprocess_review_flags(bean, str(bean.url))
    assert bean.is_tasting_kit is True


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://iefido.nl/product/test-bean/",
        roaster="Ief & Ido",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    assert scraper.postprocess_extracted_bean(bean).currency == "EUR"
