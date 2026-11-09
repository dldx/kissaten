"""Unit tests for the Pala Kaffebrenneri scraper.

Pala Kaffebrenneri (pala.no) migrated off Squarespace to a custom Next.js
storefront on Vercel: ``/butikk`` returns a Next.js error page and the coffee
catalogue lives at ``/products/coffee``, embedded as a ``schema.org/ItemList``
JSON-LD block. Product pages keep the Squarespace-style ``og:*`` and
``product:price:*`` meta tags plus a ``schema.org/Product`` JSON-LD whose
``offers`` array carries per-variant prices.

These tests run against captured fixtures
(``pala_kaffebrenneri_listing.html`` / ``pala_kaffebrenneri_product.html``)
and verify ItemList-driven URL extraction, the meta-tag/variant compaction on
product pages and the NOK currency pinning.
"""

import asyncio
from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.scrapers.pala_kaffebrenneri import STORE_URL, PalaKaffebrenneriScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
LISTING = FIXTURES / "pala_kaffebrenneri_listing.html"
PRODUCT = FIXTURES / "pala_kaffebrenneri_product.html"


def test_registered_in_registry():
    registry = get_registry()
    assert registry.is_registered("pala-kaffebrenneri")
    info = registry.get_scraper_info("pala-kaffebrenneri")
    assert info is not None
    assert info.scraper_class is PalaKaffebrenneriScraper
    assert info.currency == "NOK"
    assert info.country == "Norway"
    assert info.status == "available"


def test_store_url_points_at_nextjs_listing():
    """The legacy Squarespace /butikk URL must be gone; the store URL is the
    Next.js coffee listing page."""
    scraper = PalaKaffebrenneriScraper()
    urls = asyncio.run(scraper.get_store_urls())
    assert urls == [STORE_URL]
    assert urls == ["https://pala.no/products/coffee"]
    assert not any(u.endswith("/butikk") for u in urls)


def test_extract_urls_from_itemlist_jsonld(monkeypatch):
    """The primary extraction source is the schema.org/ItemList JSON-LD block."""
    scraper = PalaKaffebrenneriScraper()
    soup = BeautifulSoup(LISTING.read_text(), "lxml")
    monkeypatch.setattr(scraper, "fetch_page", _async_return(soup))

    urls = asyncio.run(scraper._extract_product_urls_from_store(STORE_URL))

    # The captured listing carries exactly 9 coffees in the ItemList.
    assert len(urls) == 9
    assert all(u.startswith("https://pala.no/products/") for u in urls)
    # Deduplicated and query/fragment-free
    assert len(set(urls)) == len(urls)
    assert all("?" not in u and "#" not in u for u in urls)
    # Known coffees from the live store
    names = [u.rsplit("/", 1)[-1] for u in urls]
    assert "la-virgen" in names
    assert "karumandi-aa" in names
    assert "05a2655c-ed08-4b93-ae20-c66cc7b08690" in names
    # The listing page itself never leaks in
    assert not any(u.rstrip("/") == STORE_URL.rstrip("/") for u in urls)


def test_extract_urls_falls_back_to_anchor_links(monkeypatch):
    """Without the ItemList block, /products/ anchors drive extraction; the
    listing page's own "Butikk" anchor is excluded."""
    scraper = PalaKaffebrenneriScraper()
    soup = BeautifulSoup(LISTING.read_text(), "lxml")
    for script in soup.find_all("script", type="application/ld+json"):
        script.decompose()
    monkeypatch.setattr(scraper, "fetch_page", _async_return(soup))

    urls = asyncio.run(scraper._extract_product_urls_from_store(STORE_URL))

    # 9 coffees × 2 anchor links (image + title) minus the /products/coffee
    # nav link = 18 anchors, deduplicated to 9 product URLs.
    assert len(urls) == 9
    assert all(u.startswith("https://pala.no/products/") for u in urls)
    assert not any(u.rstrip("/") == STORE_URL.rstrip("/") for u in urls)


def test_fetch_page_compacts_product_page_to_meta_and_variants(monkeypatch):
    """Product pages are narrowed to og:*/product:* meta tags + the variant
    offers parsed from the schema.org/Product JSON-LD."""
    scraper = PalaKaffebrenneriScraper()
    soup = BeautifulSoup(PRODUCT.read_text(), "lxml")

    async def _fake_super_fetch(*args, **kwargs):
        return soup

    monkeypatch.setattr("kissaten.scrapers.base.BaseScraper.fetch_page", _fake_super_fetch)
    compact = asyncio.run(scraper.fetch_page(url="https://pala.no/products/05a2655c-ed08-4b93-ae20-c66cc7b08690"))

    assert compact is not None
    # product:* metas use name=, og:* metas use property=; collect both.
    meta_keys = {(m.get("property") or m.get("name")) for m in compact.find_all("meta")}
    assert "og:title" in meta_keys
    assert "og:description" in meta_keys
    assert "product:price:amount" in meta_keys
    assert "product:price:currency" in meta_keys
    assert "product:availability" in meta_keys
    assert "og:image" in meta_keys
    # Meta price matches the live page (Frinsa Manis 250g, NOK).
    price = compact.find("meta", attrs={"name": "product:price:amount"})
    assert price and float(price["content"]) == 248.00
    currency = compact.find("meta", attrs={"name": "product:price:currency"})
    assert currency and currency["content"] == "NOK"

    variants_div = compact.body.find("div")
    assert variants_div is not None and variants_div.string
    assert variants_div.string.startswith("Variants:")
    assert "248.00 NOK" in variants_div.string
    assert "instock" in variants_div.string


def test_listing_pages_pass_through_unpruned(monkeypatch):
    """Listing pages are not narrowed to meta tags."""
    scraper = PalaKaffebrenneriScraper()
    soup = BeautifulSoup(LISTING.read_text(), "lxml")

    async def _fake_super_fetch(*args, **kwargs):
        return soup

    monkeypatch.setattr("kissaten.scrapers.base.BaseScraper.fetch_page", _fake_super_fetch)
    passthrough = asyncio.run(scraper.fetch_page(url=STORE_URL))
    assert passthrough is not None
    assert len(passthrough.find_all("script")) == len(soup.find_all("script"))


def test_postprocess_pins_nok():
    """The site sells exclusively in NOK; the bean currency is pinned."""

    class _Bean:
        currency = "SEK"

    scraper = PalaKaffebrenneriScraper()
    bean = scraper.postprocess_extracted_bean(_Bean())
    assert bean.currency == "NOK"


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner
