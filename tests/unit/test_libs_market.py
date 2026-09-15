"""Unit tests for the LiB's Market scraper (fixture-based, no network).

LiB's Market is a Square Online (Weebly) storefront: the listing pages are
JS-rendered with no product anchors, so discovery uses the static sitemap.xml
(the same approach as the Artificer Square Online scraper).
"""

from pathlib import Path

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.libs_market import LibsMarketScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

SITEMAP_URL = "https://www.libsmarket.com/sitemap.xml"


def _make_scraper() -> LibsMarketScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return LibsMarketScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("libs-market")
    assert info is not None
    assert info.roaster_name == "LiB's Market"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "LiB's Market"


async def test_store_urls_use_sitemap():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [SITEMAP_URL]


async def test_extracts_bean_urls_from_sitemap(monkeypatch):
    scraper = _make_scraper()
    sitemap_html = (FIXTURES / "libs_market_sitemap.xml").read_text()

    async def fake_fetch(url, **kwargs):
        from bs4 import BeautifulSoup

        return BeautifulSoup(sitemap_html, "lxml")

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(SITEMAP_URL)

    # Bean products survive the cafe-menu filtering
    assert "https://www.libsmarket.com/product/12-oz-lib-s-fresh-premium-coffee/673" in urls
    assert "https://www.libsmarket.com/product/believe-blend/2MHOGH3E44CZI662BRYSKX5G" in urls
    assert "https://www.libsmarket.com/product/decaf-roasted-coffee/855" in urls
    # The Fermentation Project tasting kit must NOT be excluded
    assert "https://www.libsmarket.com/product/the-fermentation-project-pack/HVM6DDJKPSVXBHDZKZ5I2HRG" in urls
    # The specialty coffee sampler pack is kept (flagged as tasting kit downstream)
    assert "https://www.libsmarket.com/product/level-7-specialty-coffee-sampler-pack/DGE3M5WRGZUCXQHK4WJ5EWEQ" in urls
    assert all("/product/" in u for u in urls)


async def test_cafe_menu_and_merch_are_excluded(monkeypatch):
    scraper = _make_scraper()
    sitemap_html = (FIXTURES / "libs_market_sitemap.xml").read_text()

    async def fake_fetch(url, **kwargs):
        from bs4 import BeautifulSoup

        return BeautifulSoup(sitemap_html, "lxml")

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(SITEMAP_URL)

    joined = " ".join(urls)
    # Cafe food/drinks
    assert "avocado-toast" not in joined
    assert "latte-cappuccino" not in joined
    assert "iced-coffee" not in joined
    assert "cold-brew" not in joined
    assert "drip-coffee" not in joined
    # Non-bean coffee-adjacent items
    assert "libs-coffee-compost" not in joined
    assert "10th-anniversary-candle" not in joined
    assert "wholesale-coffee" not in joined
    assert "subscription" not in joined
    # Merch and supporter packs
    assert "full-city-tee" not in joined
    assert "level-9-full-city-roasting-club-pack" not in joined
    # Event ticket
    assert "live-tasting" not in joined


async def test_failed_sitemap_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(SITEMAP_URL)
    assert urls == []


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://www.libsmarket.com/product/test-bean/1",
        roaster="LiB's Market",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "USD"
