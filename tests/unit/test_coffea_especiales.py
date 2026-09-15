"""Unit tests for the Coffea Cafés Especiales scraper (fixture-based, no network).

The fixture is a trimmed copy of the rendered ``/cafes`` SPA catalogue with the
``button.group`` cards and "De regreso pronto" (sold-out) markers the live site
renders. Per-coffee URLs are synthetic (``/cafes/<id>`` from the card image
filename) because the Lovable/React SPA has no per-product routes.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.coffea_especiales import FERMENTATION_PROJECT_URL, CoffeaEspecialesScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> CoffeaEspecialesScraper:
    return CoffeaEspecialesScraper(api_key="test-api-key")


def _cafes_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "coffea_especiales_cafes.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("coffea-cafes-especiales")
    assert info is not None
    assert info.roaster_name == "Coffea Cafés Especiales"
    assert info.currency == "GTQ"
    assert info.country == "Guatemala"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Coffea Cafés Especiales"


async def test_store_urls_use_cafes_catalogue():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == ["https://www.coffea.gt/cafes"]


async def test_builds_synthetic_urls_from_card_images(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _cafes_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.coffea.gt/cafes")
    assert "https://www.coffea.gt/cafes/geisha-lavado-la-hermosa" in urls
    assert "https://www.coffea.gt/cafes/chichupaq-red-honey" in urls
    # The Fermentation Project kit route is always appended.
    assert FERMENTATION_PROJECT_URL in urls


async def test_sold_out_cards_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _cafes_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.coffea.gt/cafes")
    assert "https://www.coffea.gt/cafes/geisha-natural-la-hermosa" not in urls
    assert "https://www.coffea.gt/cafes/petrona-maragogype" not in urls


async def test_only_available_coffees_plus_kit(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _cafes_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.coffea.gt/cafes")
    assert urls == [
        "https://www.coffea.gt/cafes/geisha-lavado-la-hermosa",
        "https://www.coffea.gt/cafes/chichupaq-red-honey",
        FERMENTATION_PROJECT_URL,
    ]


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store("https://www.coffea.gt/cafes")
    assert urls == []


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://www.coffea.gt/cafes/test-bean",
        roaster="Coffea Cafés Especiales",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "GTQ"
