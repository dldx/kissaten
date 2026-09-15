"""Unit tests for the 19grams scraper (fixture-based, no network)."""

import json
from pathlib import Path

from kissaten.scrapers.nineteen_grams import NineteenGramsScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://19grams.coffee/collections/all/products.json"


def _products():
    return json.loads((FIXTURES / "nineteen_grams_products.json").read_text())["products"]


def _make_scraper() -> NineteenGramsScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return NineteenGramsScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("19-grams")
    assert info is not None
    assert info.roaster_name == "19grams"
    assert info.currency == "EUR"
    assert info.country == "Germany"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "19grams"


async def test_extracts_coffee_products_with_canonical_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    # The Fermentation Project kit plus the two real beans survive; product
    # URLs are canonicalized to /products/<handle>. The Weihnachtsgeschenkbox
    # coffee bundle is kept (tasting-kit flagging is downstream).
    assert urls == [
        "https://19grams.coffee/products/the-fermentation-project-kaffee-kit-von-mit-james-hoffmann",
        "https://19grams.coffee/products/la-divisa-kolumbien-filter",
        "https://19grams.coffee/products/wild-at-heart",
        "https://19grams.coffee/products/19grams-x-motel-a-miio-weihnachtsgeschenkbox-mit-tassen-und-christmas-coffee",
    ]
    assert all("/collections/" not in u for u in urls)


async def test_excludes_equipment_training_merch_and_gift_cards(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    # Equipment (product_type filter), training/cupping events, gift cards,
    # subscriptions (abo/club) and capsules must never leak.
    assert not any("aeropress" in u for u in urls)
    assert not any("public-cupping" in u for u in urls)
    assert not any("gutschein" in u for u in urls)
    assert not any("abo" in u for u in urls)
    assert not any("club" in u for u in urls)
    assert not any("kapseln" in u for u in urls)
    assert not any("19grams-tasse" in u for u in urls)
    # Coffee gift bundles are coffee for sale: they must NOT be excluded —
    # they flow through for downstream is_tasting_kit/requires_review flagging.
    assert any("weihnachtsgeschenkbox" in u for u in urls)


def test_stock_status_keyed_by_canonical_url(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)

    import asyncio

    asyncio.run(scraper._extract_product_urls_from_store(STORE_URL))
    kit_url = "https://19grams.coffee/products/the-fermentation-project-kaffee-kit-von-mit-james-hoffmann"
    assert kit_url in scraper._shopify_stock_status
    assert scraper._shopify_stock_status[kit_url] is True


def test_currency_pinned_to_home_market():
    scraper = _make_scraper()
    assert scraper.store_currency == "EUR"
    assert scraper._currency_detected is True


def test_currency_pinned_in_postprocess():
    from kissaten.schemas import CoffeeBean

    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://19grams.coffee/products/test-bean",
        roaster="19grams",
        origins=[],
        price_options=[],
        currency="USD",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "EUR"
