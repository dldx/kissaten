"""Tests for the DAK Coffee Roasters scraper (WooCommerce Store API)."""

import json
from pathlib import Path

from kissaten.scrapers.dak import DakCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).parent.parent / "fixtures" / "dak_store_api_products.json"


def _load_fixture() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_registry_entry():
    info = get_registry().get_scraper_info("dak-coffee")
    assert info is not None
    assert info.roaster_name == "DAK Coffee Roasters"
    assert info.currency == "EUR"
    assert info.country == "Netherlands"
    assert info.website == "https://www.dakcoffeeroasters.com"


def test_filter_keeps_coffee_and_excludes_steeped_and_merch():
    scraper = DakCoffeeScraper()
    products = _load_fixture()
    coffee = scraper._filter_coffee_products(products)
    slugs = {p["slug"] for p in coffee}
    # "steeped" (bag-in-box packs) and merch (t-shirt) must be dropped
    assert slugs == {"choco-loco", "lady-in-red", "peachy-daze"}


def test_parse_single_origin_bean_fields():
    scraper = DakCoffeeScraper()
    product = next(p for p in _load_fixture() if p["slug"] == "choco-loco")
    bean = scraper._parse_product(product)

    assert bean is not None
    assert bean.name == "Choco Loco"
    assert bean.roaster == "DAK Coffee Roasters"
    assert str(bean.url) == "https://www.dakcoffeeroasters.com/product/choco-loco"
    assert bean.currency == "EUR"
    # prices are in minor units: 1780 -> 17.80 EUR
    assert bean.price == 17.80
    assert bean.weight == 250  # min of 250g / 1kg options
    assert [p.model_dump() for p in bean.price_options] == [{"weight": 250, "price": 17.80, "currency": "EUR"}]
    assert bean.in_stock is True
    assert bean.is_single_origin is True
    assert bean.roast_profile == "Espresso"

    origin = bean.origins[0]
    assert origin.country == "BR"
    assert origin.region == "Sul De Minas"  # schema title-cases regions
    assert origin.producer == "Edir José de Carvalho"
    assert origin.process == "Natural"
    assert origin.variety == "Yellow Catuai"
    assert origin.elevation_min == 1260
    assert origin.elevation_max == 1260

    assert bean.tasting_notes == ["Milk Chocolate", "Nougat", "Raisins"]
    assert bean.image_url is not None
    assert "cloudfront.net" in str(bean.image_url)
    assert bean.description and "Brazilian" in bean.description


def test_parse_both_roast_profiles_and_elevation_range():
    scraper = DakCoffeeScraper()
    product = next(p for p in _load_fixture() if p["slug"] == "peachy-daze")
    bean = scraper._parse_product(product)

    assert bean is not None
    # Espresso + Filter terms offered as separate options -> "Both"
    assert bean.roast_profile == "Both"
    origin = bean.origins[0]
    assert origin.country == "ET"
    assert origin.elevation_min == 2173
    assert origin.elevation_max == 2173


def test_parse_single_weight_product():
    scraper = DakCoffeeScraper()
    product = next(p for p in _load_fixture() if p["slug"] == "lady-in-red")
    bean = scraper._parse_product(product)

    assert bean is not None
    assert bean.weight == 125
    assert bean.roast_profile == "Filter"
    assert bean.origins[0].process == "Advanced Anaerobic Natural"
