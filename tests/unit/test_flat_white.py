"""Tests for the Flat&White scraper (WordPress/TiendaPocket listing page)."""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.scrapers.flat_white import FlatWhiteScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).parent.parent / "fixtures" / "flat_white_argentina_listing.html"


def _load_soup() -> BeautifulSoup:
    return BeautifulSoup(FIXTURE.read_text(encoding="utf-8"), "html.parser")


def test_registry_entry():
    info = get_registry().get_scraper_info("flat-white")
    assert info is not None
    assert info.roaster_name == "Flat&White"
    assert info.website == "https://flatnwhite.com"
    assert info.currency == "ARS"


async def test_extract_uses_tp_product_card_selectors_and_filters(monkeypatch):
    """The 2026 TiendaPocket theme redesign replaced the WooCommerce loop
    markup with ``article.tp-product-card`` blocks whose primary link is
    ``a.tp-product-card__img-link``. URLs now point directly at product
    pages (e.g. /cafe-de-especialidad-colombia/)."""
    scraper = FlatWhiteScraper()
    soup = _load_soup()

    async def fake_fetch_page(url, retries=0, use_playwright=False):
        assert url == "https://flatnwhite.com/cafe-de-especialidad-flatwhite-argentina/"
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch_page)
    urls = await scraper._extract_product_urls_from_store(
        "https://flatnwhite.com/cafe-de-especialidad-flatwhite-argentina/"
    )

    # Coffee products (and the box bundle, which the pipeline flags as a
    # tasting kit via is_tasting_kit) must be found via the new selectors.
    assert "https://flatnwhite.com/cafe-de-especialidad-colombia/" in urls
    assert "https://flatnwhite.com/cafe-especialidad-etiopia/" in urls
    assert "https://flatnwhite.com/cafe-especialidad-ruanda/" in urls
    assert "https://flatnwhite.com/3-cafes-de-especialidad/" in urls

    # Sold-out product ("Sin stock" text in the card) must be skipped.
    assert "https://flatnwhite.com/cafe-especialidad-burundi/" not in urls

    # Equipment / non-coffee pages must be excluded by the path filter.
    assert "https://flatnwhite.com/balanza-flair-brew/" not in urls
    assert "https://flatnwhite.com/cafeteras/" not in urls
