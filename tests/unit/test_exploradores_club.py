"""Unit tests for the Exploradores Club de Cafe scraper (fixture-based, no network).

Exploradores De Café (grupoexploradores.com) is a Squarespace storefront; the
fixtures are trimmed copies of the real coffee collection listing page (newer
``div.product-list-item`` markup) and a ``/tienda/p/`` product page (meta tags +
``Static.SQUARESPACE_CONTEXT`` variants).
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.exploradores_club import ExploradoresClubScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URLS = [
    "https://www.grupoexploradores.com/tienda/caf-especialidad",
    "https://www.grupoexploradores.com/tienda/caf-orgnico",
    "https://www.grupoexploradores.com/tienda/caf-descafeinado",
]


def _make_scraper() -> ExploradoresClubScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return ExploradoresClubScraper(api_key="test-api-key")


def _shop_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "exploradores_club_tienda.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("exploradores-club-de-cafe")
    assert info is not None
    assert info.roaster_name == "Exploradores Club de Cafe"
    assert info.currency == "MXN"
    assert info.country == "Mexico"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Exploradores Club de Cafe"


async def test_store_urls_cover_the_coffee_collections():
    scraper = _make_scraper()
    assert await scraper.get_store_urls() == STORE_URLS


async def test_extracts_product_urls_from_collection_fixture(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URLS[0])
    assert (
        "https://www.grupoexploradores.com/tienda/p/amarena-cafe-calidad-especialidad-estilo-moderno-250g-y-1kg" in urls
    )
    # Curated coffee kits (kit-de-cafe-*) are extracted, not excluded.
    assert "https://www.grupoexploradores.com/tienda/p/kit-de-cafe-organico-de-especialidad-experiencia-tueste" in urls
    # Every extracted URL uses the Squarespace /tienda/p/ permalink format.
    assert all("/tienda/p/" in u for u in urls)


async def test_equipment_products_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URLS[0])
    # Acaia scale — excluded via the "bascula" URL token.
    assert not any("acaia-lunar" in u for u in urls)


async def test_sold_out_card_is_excluded_but_fermentation_kit_kept(monkeypatch):
    scraper = _make_scraper()
    kit_url = (
        "https://www.grupoexploradores.com/tienda/p/the-fermentation-project-james-hoffmann-x-luca-sols-kit-de-cata"
    )

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URLS[0])
    assert kit_url in urls


async def test_fermentation_kit_dropped_once_scraped_historically(monkeypatch):
    scraper = _make_scraper()
    kit_url = (
        "https://www.grupoexploradores.com/tienda/p/the-fermentation-project-james-hoffmann-x-luca-sols-kit-de-cata"
    )

    async def fake_fetch(url, **kwargs):
        return _shop_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URLS[0])
    assert kit_url in urls

    scraper._mark_bean_as_scraped(kit_url)
    urls = await scraper._extract_product_urls_from_store(STORE_URLS[0])
    assert kit_url not in urls


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URLS[0])
    assert urls == []


def test_compact_product_soup_keeps_meta_and_variants():
    scraper = _make_scraper()
    soup = BeautifulSoup((FIXTURES / "exploradores_club_product.html").read_text(), "lxml")
    compact = scraper._compact_product_soup(soup)

    assert compact.find("meta", property="og:title") is not None
    assert compact.find("meta", property="product:price:currency")["content"] == "MXN"
    assert compact.find("meta", property="product:price:amount")["content"] == "300.00"
    body_text = compact.body.get_text(" ", strip=True)
    assert "Variants:" in body_text
    assert "250g" in body_text
    assert "En Grano" in body_text
    # Page body copy must not leak into the compacted soup
    assert "boilerplate" not in str(compact)
    assert "preparación" not in str(compact)


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://www.grupoexploradores.com/tienda/p/amarena-cafe",
        roaster="Exploradores Club de Cafe",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "MXN"


def test_tasting_kit_url_patterns_cover_kits():
    scraper = _make_scraper()
    assert scraper.is_tasting_kit_url(
        "https://www.grupoexploradores.com/tienda/p/the-fermentation-project-james-hoffmann-x-luca-sols-kit-de-cata"
    )
    assert scraper.is_tasting_kit_url(
        "https://www.grupoexploradores.com/tienda/p/kit-de-cafe-organico-de-especialidad-experiencia-tueste"
    )
    assert not scraper.is_tasting_kit_url(
        "https://www.grupoexploradores.com/tienda/p/amarena-cafe-calidad-especialidad-estilo-moderno-250g-y-1kg"
    )
