"""Unit tests for the NiR Coffee scraper (fixture-based, no network).

NiR Coffee's React SPA is backed by a public JSON catalogue API; the scraper
builds beans directly from those documents.
"""

import json
from pathlib import Path

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.nir_coffee import PRODUCTS_API_URL, NirCoffeeScraper, _parse_altitude, _slugify
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _products() -> list[dict]:
    return json.loads((FIXTURES / "nir_coffee_products.json").read_text())["data"]


def _by_name(name: str) -> dict:
    return next(product for product in _products() if product["name"] == name)


def _make_scraper() -> NirCoffeeScraper:
    return NirCoffeeScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("nir-coffee")
    assert info is not None
    assert info.roaster_name == "NiR Coffee"
    assert info.currency == "IDR"
    assert info.country == "Indonesia"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    assert _make_scraper().roaster_name == "NiR Coffee"


async def test_store_urls():
    assert await _make_scraper().get_store_urls() == [PRODUCTS_API_URL]


def test_slugify_matches_site_routes():
    assert (
        _slugify("Flores Gulang #349 Natural Anaerob Fast Dry Filter")
        == "flores-gulang-349-natural-anaerob-fast-dry-filter"
    )
    assert _slugify("El Diviso Chiroso Special Selection Lot") == "el-diviso-chiroso-special-selection-lot"


def test_altitude_parsing():
    assert _parse_altitude("1500-1700") == (1500, 1700)
    assert _parse_altitude("1850") == (1850, 1850)
    assert _parse_altitude(None) == (0, 0)
    # Schema bounds are 0-3000 m.
    assert _parse_altitude("3200-3500") == (3000, 3000)


def test_product_url_builder():
    scraper = _make_scraper()
    assert (
        scraper._product_url(_by_name("Arjuna Budug Asu Natural Espresso"))
        == "https://nircoffee.id/shop/daily/espresso/arjuna-budug-asu-natural-espresso"
    )
    assert (
        scraper._product_url(_by_name("Peru Finca Lorifunde Sl-09"))
        == "https://nircoffee.id/shop/limited/filter/peru-finca-lorifunde-sl-09"
    )
    assert (
        scraper._product_url(_by_name("The Fermentation Project × James Hoffmann"))
        == "https://nircoffee.id/fermentation-project"
    )


async def test_extracts_only_in_stock_products(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch_products():
        return _products()

    monkeypatch.setattr(scraper, "_fetch_products", fake_fetch_products)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_API_URL)

    assert "https://nircoffee.id/shop/daily/espresso/arjuna-budug-asu-natural-espresso" in urls
    assert "https://nircoffee.id/shop/limited/filter/peru-finca-lorifunde-sl-09" in urls
    # Sold-out Fermentation kit is excluded from the current URL list.
    assert "https://nircoffee.id/fermentation-project" not in urls


async def test_failed_api_fetch_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch_products():
        return None

    monkeypatch.setattr(scraper, "_fetch_products", fake_fetch_products)
    assert await scraper._extract_product_urls_from_store(PRODUCTS_API_URL) == []


def test_build_bean_from_api_document():
    scraper = _make_scraper()
    product = _by_name("Arjuna Budug Asu Natural Espresso")
    url = scraper._product_url(product)
    bean = scraper._build_bean(product, url)

    assert bean is not None
    assert bean.name == "Arjuna Budug Asu Natural Espresso"
    assert bean.roaster == "NiR Coffee"
    assert bean.currency == "IDR"
    assert bean.is_single_origin is True
    # The schema stores enum values as plain strings.
    assert bean.roast_level == "Medium-Light"
    assert bean.roast_profile == "Espresso"
    assert bean.tasting_notes == ["Tangerine", "Lychee", "Black Tea"]
    assert bean.in_stock is True
    assert bean.image_url is not None

    # Two weight/price options, cheapest drives the top-level price.
    assert [(option.weight, option.price) for option in bean.price_options] == [(200, 59000.0), (1000, 250000.0)]
    assert bean.price == 59000.0
    assert bean.weight == 200

    origin = bean.origins[0]
    assert origin.country == "ID"
    assert origin.region == "Arjuna"
    assert origin.producer == "Andri"
    assert origin.farm == "Budug Asu"
    assert origin.process == "Natural"
    assert origin.variety == "Mixed Varietals"
    assert (origin.elevation_min, origin.elevation_max) == (1500, 1700)


def test_tasting_kit_bean_has_no_origins():
    scraper = _make_scraper()
    product = _by_name("The Fermentation Project × James Hoffmann")
    url = scraper._product_url(product)
    bean = scraper._build_bean(product, url)

    assert bean is not None
    assert bean.origins == []
    assert bean.is_single_origin is False
    assert bean.weight is None


def test_tasting_kit_review_flag():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="The Fermentation Project × James Hoffmann",
        url="https://nircoffee.id/fermentation-project",
        roaster="NiR Coffee",
        origins=[],
        price_options=[],
        currency="IDR",
    )
    scraper.postprocess_review_flags(bean, str(bean.url))
    assert bean.is_tasting_kit is True

    scraper._apply_product_flags(bean, str(bean.url), is_new=True)
    assert bean.requires_review is True


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://nircoffee.id/shop/daily/espresso/test-bean",
        roaster="NiR Coffee",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    assert scraper.postprocess_extracted_bean(bean).currency == "IDR"
