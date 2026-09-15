"""Unit tests for The God Shot scraper (fixture-based, no network).

The God Shot runs an Odoo storefront: the coffee-beans category page lists
``article.oe_product_cart`` cards, and product detail pages carry the content
in ``#product_details`` / ``#product_full_description`` / ``#product_specifications``.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.the_god_shot import TheGodShotScraper

FIXTURES = Path(__file__).parent.parent / "fixtures"

CATEGORY_URL = "https://www.thegodshot.be/shop/category/coffee-beans-3"
PRODUCT_URL = "https://www.thegodshot.be/shop/coffee-beans-3/guatemala-the-fermentation-project-1693"


def _make_scraper() -> TheGodShotScraper:
    return TheGodShotScraper(api_key="test-api-key")


def _category_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "godshot_category.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("the-god-shot")
    assert info is not None
    assert info.roaster_name == "The God Shot"
    assert info.currency == "EUR"
    assert info.country == "Belgium"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "The God Shot"


async def test_store_urls_use_coffee_beans_category():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [CATEGORY_URL]


async def test_extracts_in_stock_coffee_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _category_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(CATEGORY_URL)

    assert "https://www.thegodshot.be/shop/coffee-beans-3/brazil-dois-irmaos-1695" in urls
    # The Fermentation Project kit must NOT be excluded
    assert "https://www.thegodshot.be/shop/coffee-beans-3/guatemala-the-fermentation-project-1693" in urls
    # Sample packs are kept (flagged as tasting kits downstream)
    assert "https://www.thegodshot.be/shop/coffee-beans-3/sample-pack-espresso-1313" in urls
    assert all("/shop/coffee-beans-3/" in u for u in urls)


async def test_sold_out_card_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _category_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(CATEGORY_URL)

    assert "https://www.thegodshot.be/shop/coffee-beans-3/rwanda-sold-out-lot-1700" not in urls


async def test_subscriptions_and_equipment_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _category_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(CATEGORY_URL)

    joined = " ".join(urls)
    assert "subscription" not in joined
    assert "fellow-atmos" not in joined


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(CATEGORY_URL)
    assert urls == []


async def test_fetch_page_product_page_narrows_to_odoo_containers(monkeypatch):
    scraper = _make_scraper()
    full_soup = BeautifulSoup((FIXTURES / "godshot_product.html").read_text(), "lxml")

    async def fake_base_fetch_page(self, url: str, **kwargs) -> BeautifulSoup:
        return full_soup

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_base_fetch_page)

    compact = await scraper.fetch_page(PRODUCT_URL)

    html = str(compact)
    # Kept: the Odoo product containers
    assert 'id="product_details"' in html
    assert 'id="product_full_description"' in html
    # Dropped: nav noise outside the containers
    assert "NAV NOISE" not in html
    assert "FOOTER NOISE" not in html


async def test_fetch_page_category_url_returns_unmodified_soup(monkeypatch):
    scraper = _make_scraper()
    category_soup = _category_soup()

    async def fake_base_fetch_page(self, url: str, **kwargs) -> BeautifulSoup:
        return category_soup

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_base_fetch_page)

    compact = await scraper.fetch_page(CATEGORY_URL)
    assert compact is category_soup


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Brazil: Dois Irmãos",
        url=PRODUCT_URL,
        roaster="The God Shot",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "EUR"
