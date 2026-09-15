"""Unit tests for the Mundos Roasting scraper (fixture-based, no network).

Mundos is a Squarespace storefront: the /coffee collection page embeds the
catalog as escaped Squarespace JSON (``fullUrl``/``urlSlug``/``qtyInStock``),
and product detail pages carry the standard ``og:*/product:*`` meta tags plus
the ``Static.SQUARESPACE_CONTEXT`` variants blob (the Pala pattern).
"""

import json
from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.mundos_roasting import MundosRoastingScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

LISTING_URL = "https://www.mundosroastingco.com/coffee"
PRODUCT_URL = "https://www.mundosroastingco.com/coffee/p/burundi-jarama"


def _make_scraper() -> MundosRoastingScraper:
    return MundosRoastingScraper(api_key="test-api-key")


def _listing_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "mundos_coffee.html").read_text(), "html.parser")


def test_registry_entry():
    info = get_registry().get_scraper_info("mundos-roasting")
    assert info is not None
    assert info.roaster_name == "Mundos Roasting"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Mundos Roasting"


async def test_store_urls_use_coffee_collection():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [LISTING_URL]


async def test_extracts_in_stock_coffee_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    assert "https://www.mundosroastingco.com/coffee/p/colombia-argelia" in urls
    assert "https://www.mundosroastingco.com/coffee/p/kenya-kathakwa" in urls
    # The Fermentation Project kit must NOT be excluded
    assert "https://www.mundosroastingco.com/coffee/p/fermentation-box-set" in urls
    assert all("/coffee/p/" in u for u in urls)


async def test_sold_out_products_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    # burundi-jarama has qtyInStock 0 in the collection JSON (detail page shows oos)
    assert "https://www.mundosroastingco.com/coffee/p/burundi-jarama" not in urls


async def test_merch_and_non_coffee_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    joined = " ".join(urls)
    assert "white-chocolate" not in joined
    assert "coffee-plant-mug" not in joined
    assert "test-t-shirt" not in joined


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(LISTING_URL)
    assert urls == []


async def test_fetch_page_product_page_returns_meta_only_soup_with_variants(monkeypatch):
    scraper = _make_scraper()
    full_soup = BeautifulSoup((FIXTURES / "mundos_product.html").read_text(), "html.parser")

    async def fake_base_fetch_page(self, url: str, **kwargs) -> BeautifulSoup:
        return full_soup

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_base_fetch_page)

    compact = await scraper.fetch_page(PRODUCT_URL)

    html = str(compact)
    # Kept: product meta tags + variants block
    assert 'property="og:title"' in html
    assert 'property="product:price:amount"' in html
    assert 'property="product:availability"' in html
    assert "Variants:" in compact.get_text()
    variants_text = compact.find("div").get_text()
    assert "- Size: 12oz. | Price: 20.00 USD | Stock: unknown" in variants_text
    assert "- Size: 5lb. | Price: 56.00 USD | Stock: instock" in variants_text
    # Dropped: body noise
    assert "NAV NOISE" not in html
    assert "FOOTER NOISE" not in html


async def test_fetch_page_listing_url_returns_unmodified_soup(monkeypatch):
    scraper = _make_scraper()
    listing_soup = _listing_soup()

    async def fake_base_fetch_page(self, url: str, **kwargs) -> BeautifulSoup:
        return listing_soup

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_base_fetch_page)

    compact = await scraper.fetch_page(LISTING_URL)
    assert compact is listing_soup


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url=PRODUCT_URL,
        roaster="Mundos Roasting",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "USD"


def test_static_context_fixture_variants_are_valid_json():
    """The fixture's variants blob must parse so _extract_variants exercises the real path."""
    html = (FIXTURES / "mundos_product.html").read_text()
    assert "Static.SQUARESPACE_CONTEXT" in html
    data = json.loads(html.split("Static.SQUARESPACE_CONTEXT = ")[1].split(";</script>")[0])
    assert len(data["product"]["variants"]) == 2
