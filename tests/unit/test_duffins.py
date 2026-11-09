"""Unit tests for the Duffin's Coffee scraper (fixture-based, no network).

The fixture is a slice of the live WooCommerce ``/shop/`` index with the
``li.product`` cards. The site's product URLs live under
``/shop/freshly-roasted-speciality-coffee/<slug>/`` (the older
``/shop/coffee/<slug>/`` path is kept as an OR fallback), so the required
path pattern must accept the current path or every card is excluded.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.scrapers.duffins import DuffinsScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> DuffinsScraper:
    return DuffinsScraper(api_key="test-api-key")


def _listing_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "duffins_shop.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("duffins")
    assert info is not None
    assert info.roaster_name == "Duffin's"
    assert info.currency == "GBP"
    assert info.country == "United Kingdom"
    assert info.requires_api_key is True
    assert info.status == "available"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Duffin's"


async def test_store_urls_use_shop_index():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == ["https://duffinscoffee.com/shop/"]


async def test_extracts_current_path_product_urls(monkeypatch):
    """The current canonical path must not be filtered out by the required patterns."""
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://duffinscoffee.com/shop/")
    assert urls, "required path patterns must not exclude the live product paths"
    assert all("/shop/freshly-roasted-speciality-coffee/" in u for u in urls)
    assert "https://duffinscoffee.com/shop/freshly-roasted-speciality-coffee/juicy-gossip-coffee-blend/" in urls
    assert "https://duffinscoffee.com/shop/freshly-roasted-speciality-coffee/chin-wag-coffee-blend/" in urls


async def test_legacy_coffee_path_still_accepted(monkeypatch):
    """The pre-rebrand /shop/coffee/<slug>/ path stays accepted as an OR fallback."""
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        soup = BeautifulSoup("<ul><li class='product'><a href='/shop/coffee/legacy-blend/'>x</a></li></ul>", "lxml")
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://duffinscoffee.com/shop/")
    assert urls == ["https://duffinscoffee.com/shop/coffee/legacy-blend/"]


async def test_gift_card_and_hamper_are_filtered(monkeypatch):
    """Genuine non-coffee products (gift card / gift set / hamper) stay excluded."""
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://duffinscoffee.com/shop/")
    assert "https://duffinscoffee.com/shop/freshly-roasted-speciality-coffee/duffins-gift-card/" not in urls
    assert "https://duffinscoffee.com/shop/freshly-roasted-speciality-coffee/coffee-blend-hamper/" not in urls
    gift_set = (
        "https://duffinscoffee.com/shop/freshly-roasted-speciality-coffee/ugandan-gift-set-chocolate-kalingwe-coffee/"
    )
    assert gift_set not in urls


async def test_sold_out_card_is_excluded(monkeypatch):
    """Class-based sold-out detection runs before URL filtering."""
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        soup = BeautifulSoup(
            "<ul>"
            "<li class='product instock'><a href='/shop/freshly-roasted-speciality-coffee/in-stock-blend/'>a</a></li>"
            "<li class='product outofstock'><a href='/shop/freshly-roasted-speciality-coffee/"
            "sold-out-blend/'>b</a></li>"
            "</ul>",
            "lxml",
        )
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://duffinscoffee.com/shop/")
    assert "https://duffinscoffee.com/shop/freshly-roasted-speciality-coffee/in-stock-blend/" in urls
    assert "https://duffinscoffee.com/shop/freshly-roasted-speciality-coffee/sold-out-blend/" not in urls


async def test_taxonomy_archive_normalised_to_current_path(monkeypatch):
    """A /shop/type/<taxonomy>/<slug>/ card is normalised to the current canonical path."""
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        soup = BeautifulSoup(
            "<ul>"
            "<li class='product instock'><a href='/shop/type/coffee-type/juicy-gossip-coffee-blend/'>a</a></li>"
            "</ul>",
            "lxml",
        )
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://duffinscoffee.com/shop/")
    assert urls == ["https://duffinscoffee.com/shop/freshly-roasted-speciality-coffee/juicy-gossip-coffee-blend/"]
