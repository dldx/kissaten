"""Unit tests for the Casa Landino scraper (fixture-based, no network)."""

import json
from pathlib import Path

from kissaten.scrapers.casa_landino import CasaLandinoScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://casalandino.com/collections/cafes-latinos-especiales/products.json"


def _products():
    return json.loads((FIXTURES / "casa_landino_products.json").read_text())["products"]


def _make_scraper() -> CasaLandinoScraper:
    return CasaLandinoScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("casa-landino")
    assert info is not None
    assert info.roaster_name == "Casa Landino"
    # Verified from the site: Colombian roaster (Armenia, Quindío) selling in COP.
    assert info.currency == "COP"
    assert info.country == "Colombia"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Casa Landino"


async def test_extracts_coffees_and_keeps_fermentation_project_kits(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    # The Fermentation Project kit itself must be extracted (flagged for
    # review downstream), not dropped. The Origami dripper bundles are
    # equipment bundles and are excluded by the base class's "origami" URL
    # equipment guard.
    assert urls == [
        "https://casalandino.com/products/james-hoffmann-fermentation-projects-by-casa-landino",
        "https://casalandino.com/products/kit-maestros-bundle",
        "https://casalandino.com/products/maestro-elias-quilcue-copia",
        "https://casalandino.com/products/tierras-de-ata",
    ]
    assert all("/collections/" not in u for u in urls)
    assert not any("origami" in u for u in urls)


def test_currency_pinned_to_home_market():
    scraper = _make_scraper()
    assert scraper.store_currency == "COP"
    assert scraper._currency_detected is True


def test_currency_pinned_in_postprocess():
    from kissaten.schemas import CoffeeBean

    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://casalandino.com/products/test-bean",
        roaster="Casa Landino",
        origins=[],
        price_options=[],
        currency="USD",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "COP"
