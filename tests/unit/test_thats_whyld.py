"""Unit tests for the That's Whyld scraper (fixture-based, no network).

That's Whyld (thatswhyld.com.au) is a Squarespace storefront; the fixtures are
trimmed copies of the real ``/shop`` listing page (newer
``div.product-list-item`` markup) and a ``/shop/p/`` product page (meta tags +
``Static.SQUARESPACE_CONTEXT`` variants).
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.thats_whyld import ThatsWhyldScraper

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://www.thatswhyld.com.au/shop"


def _make_scraper() -> ThatsWhyldScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return ThatsWhyldScraper(api_key="test-api-key")


def _shop_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "thats_whyld_shop.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("thats-whyld")
    assert info is not None
    assert info.roaster_name == "That's Whyld Coffee Roasters"
    assert info.currency == "AUD"
    assert info.country == "Australia"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "That's Whyld Coffee Roasters"


async def test_store_url_is_shop_listing():
    scraper = _make_scraper()
    assert await scraper.get_store_urls() == [STORE_URL]


async def test_extracts_product_urls_from_shop_fixture(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)
    assert "https://www.thatswhyld.com.au/shop/p/solstice-blend" in urls
    assert "https://www.thatswhyld.com.au/shop/p/solstice-blend-espresso" in urls
    assert "https://www.thatswhyld.com.au/shop/p/swiss-water-process-organic-decaf" in urls
    # Every extracted URL uses the Squarespace /shop/p/ permalink format.
    assert all("/shop/p/" in u for u in urls)


async def test_sold_out_card_is_excluded_but_kit_kept(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)
    # Regular sold-out product is excluded...
    assert "https://www.thatswhyld.com.au/shop/p/nocturnal-dark-blend" not in urls
    # ...while the sold-out Fermentation Project kit is kept for extraction.
    assert "https://www.thatswhyld.com.au/shop/p/hoffmanproject" in urls


async def test_merch_products_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)
    assert not any("kev-mug" in u for u in urls)
    assert not any("kev-tees" in u for u in urls)


async def test_fermentation_project_kit_is_kept_even_when_sold_out(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    kit_url = "https://www.thatswhyld.com.au/shop/p/hoffmanproject"
    urls = await scraper._extract_product_urls_from_store(STORE_URL)
    assert kit_url in urls


async def test_fermentation_kit_dropped_once_scraped_historically(monkeypatch):
    scraper = _make_scraper()
    kit_url = "https://www.thatswhyld.com.au/shop/p/hoffmanproject"

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)
    assert kit_url in urls

    scraper._mark_bean_as_scraped(kit_url)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)
    assert kit_url not in urls


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)
    assert urls == []


def test_compact_product_soup_keeps_meta_and_variants():
    scraper = _make_scraper()
    soup = BeautifulSoup((FIXTURES / "thats_whyld_product.html").read_text(), "lxml")
    compact = scraper._compact_product_soup(soup)

    assert compact.find("meta", property="og:title") is not None
    assert compact.find("meta", property="product:price:currency")["content"] == "AUD"
    assert compact.find("meta", property="product:price:amount")["content"] == "20.00"
    body_text = compact.body.get_text(" ", strip=True)
    assert "Variants:" in body_text
    assert "250g" in body_text
    assert "Whole Bean" in body_text
    # Page body copy must not leak into the compacted soup
    assert "Lorem ipsum" not in str(compact)
    assert "boilerplate" not in str(compact)


def test_compact_product_soup_handles_missing_variants():
    scraper = _make_scraper()
    soup = BeautifulSoup("<html><head></head><body><p>x</p></body></html>", "lxml")
    compact = scraper._compact_product_soup(soup)
    assert compact is not None


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://www.thatswhyld.com.au/shop/p/solstice-blend",
        roaster="That's Whyld Coffee Roasters",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "AUD"


def test_tasting_kit_url_patterns_cover_hoffmanproject():
    scraper = _make_scraper()
    assert scraper.is_tasting_kit_url("https://www.thatswhyld.com.au/shop/p/hoffmanproject")
    assert not scraper.is_tasting_kit_url("https://www.thatswhyld.com.au/shop/p/solstice-blend")
