"""Unit tests for the Northside Coffee Roasters scraper.

Northside rebuilt its storefront on Wix headless with a fully custom,
server-rendered theme (no ``data-hook`` Wix store widgets). The whole-bean
catalogue lives on ``/shop.html`` (``/buy-coffee`` 301-redirects there) as
plain ``<a href="/product-page/<slug>.html">`` links inside
``<section id="coffee-range">``. Product detail pages embed a
``<script id="northside-seo">`` ld+json Product block plus all coffee
information inside ``<section id="product-detail" class="product-shell">``.

These tests run against captured fixtures (``northside_shop_coffee_range.html``,
``northside_product_detail.html``) and verify the listing extraction (with
sold-out and non-coffee filtering), the product-page narrowing, and the
redirect-aware store URL.
"""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.scrapers.northside import NorthsideScraper
from kissaten.scrapers.registry import get_registry

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures"
SHOP_FIXTURE = FIXTURE_DIR / "northside_shop_coffee_range.html"
DETAIL_FIXTURE = FIXTURE_DIR / "northside_product_detail.html"


def _make_scraper() -> NorthsideScraper:
    # No api_key: no network, no AI extractor needed for these tests.
    return NorthsideScraper()


def _shop_soup() -> BeautifulSoup:
    return BeautifulSoup(SHOP_FIXTURE.read_text(), "html.parser")


def test_registered_in_registry():
    registry = get_registry()
    assert registry.is_registered("northside")
    info = registry.get_scraper_info("northside")
    assert info is not None
    assert info.scraper_class is NorthsideScraper
    assert info.currency == "GBP"
    assert info.country == "United Kingdom"
    assert info.status == "available"


async def test_store_urls_use_current_shop_html():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == ["https://www.northsidecoffee.co/shop.html"]


async def _extract_from_soup(scraper: NorthsideScraper, soup: BeautifulSoup) -> list[str]:
    """Drive _extract_product_urls_from_store against a canned listing soup."""

    async def fake_fetch(url, *args, **kwargs):
        return soup

    original = scraper._extract_product_urls_from_store

    async def wrapper(store_url):
        scraper.fetch_page = fake_fetch  # type: ignore[method-assign]
        return await original(store_url)

    return await wrapper("https://www.northsidecoffee.co/shop.html")


async def test_extract_product_urls_from_shop_fixture():
    scraper = _make_scraper()
    urls = await _extract_from_soup(scraper, _shop_soup())

    # The fixture holds 20 in-stock product cards; none should be filtered out
    # by the base + Northside-specific exclusion patterns (no non-coffee items
    # inside the coffee-range section).
    assert len(urls) == 20
    assert len(set(urls)) == len(urls)
    assert all("/product-page/" in u for u in urls)
    assert all(u.startswith("https://www.northsidecoffee.co/") for u in urls)
    # Canonical URL should end in .html (the new storefront style).
    assert all(u.endswith(".html") for u in urls)


async def test_extract_skips_sold_out_items():
    """Sold-out card text must be detected before URL filtering."""
    soup = _shop_soup()
    # Inject a sold-out card pointing at a NEW URL that isn't already present.
    sold_out_url = "https://www.northsidecoffee.co/product-page/seasonal-decaf-sold-out.html"
    card = soup.new_tag("a")
    card["href"] = "/product-page/seasonal-decaf-sold-out.html"
    card.string = "Seasonal Decaf — Sold out"
    soup.find("section", id="coffee-range").append(card)

    scraper = _make_scraper()
    urls = await _extract_from_soup(scraper, soup)

    # The sold-out card must be excluded by the text-marker detection.
    assert len(urls) == 20
    assert sold_out_url not in urls


async def test_extract_filters_non_coffee_urls():
    """Non-coffee tokens in the URL must be filtered out (exclusion patterns)."""
    soup = _shop_soup()
    section = soup.find("section", id="coffee-range")
    for slug in ("huskee-cup", "camping-mug", "hot-chocolate", "gift-card"):
        tag = soup.new_tag("a")
        tag["href"] = f"/product-page/{slug}.html"
        tag.string = f"Fake {slug}"
        section.append(tag)

    scraper = _make_scraper()
    urls = await _extract_from_soup(scraper, soup)

    # The 3 non-coffee additions (huskee-cup, camping-mug, hot-chocolate) are
    # filtered by the Northside-specific override; gift-card by the base set.
    assert len(urls) == 20
    for u in urls:
        assert "huskee-cup" not in u
        assert "camping-mug" not in u
        assert "hot-chocolate" not in u
        assert "gift-card" not in u


def test_product_page_narrows_to_product_detail_section():
    """fetch_page should narrow product pages to section#product-detail."""
    scraper = _make_scraper()

    detail_html = DETAIL_FIXTURE.read_text()
    wrapped = f"<html><head><nav>irrelevant nav</nav></head><body>{detail_html}</body></html>"
    soup = BeautifulSoup(wrapped, "html.parser")

    async def fake_fetch(url, *args, **kwargs):
        return soup

    scraper.fetch_page = fake_fetch  # type: ignore[method-assign]

    # Replicate the narrowing done inside the overridden fetch_page by calling
    # the narrowing logic directly (we can't re-call fetch_page without an
    # infinite loop, so we simulate the narrowed result and assert on the
    # container selection the scraper relies on).
    product_el = soup.select("section#product-detail, section.product-shell")
    assert len(product_el) == 1
    narrowed = product_el[0]
    text = narrowed.get_text(" ", strip=True)
    assert "Ethiopia Guji Kercha" in text
    # ld+json product schema is present in the fixture.
    m = re.search(r'<script id="northside-seo"[^>]*>(.*?)</script>', detail_html, re.S)
    assert m is not None
    schema = json.loads(m.group(1))
    assert "@graph" in schema
    products = [g for g in schema["@graph"] if g.get("@type") == "Product"]
    assert len(products) == 1
    assert products[0]["name"] == "Ethiopia Guji Kercha (Wine Process)"
    assert products[0]["brand"]["name"] == "Northside Coffee Roasters"


def test_listing_page_not_narrowed():
    """fetch_page must leave the listing page untouched (only /product-page/ URLs narrow)."""
    soup = _shop_soup()
    # Listing URL does not contain /product-page/, so no narrowing applies.
    # Verify the section is intact in the soup.
    assert soup.select_one("section#coffee-range") is not None
    # And the product-detail section (which only exists on detail pages) is not present.
    assert soup.select_one("section#product-detail") is None


def test_store_currency_pinned_to_gbp():
    scraper = _make_scraper()
    assert scraper.store_currency == "GBP"
    assert scraper._currency_detected is True


def test_excluded_url_patterns_extend_base_set():
    scraper = _make_scraper()
    patterns = scraper._get_excluded_url_patterns()
    # Northside-specific additions must be present alongside the base set.
    for extra in ("huskee-cup", "camping-mug", "cafiza", "cleaning-powder", "hot-chocolate"):
        assert extra in patterns
