"""Unit tests for the Delicate Coffee scraper (fixture-based, no network)."""

import asyncio
import json
from pathlib import Path

from kissaten.scrapers.delicate_coffee import DelicateCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://delicate.coffee/collections/shop/products.json"


def _products():
    return json.loads((FIXTURES / "delicate_coffee_products.json").read_text())["products"]


def _make_scraper() -> DelicateCoffeeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return DelicateCoffeeScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("delicate-coffee")
    assert info is not None
    assert info.roaster_name == "Delicate Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Delicate Coffee"


async def test_extracts_coffee_products_with_canonical_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    # Lot names are concise ("getuya AA", "kathima AB - rested"), so the
    # assertion is on the canonical product URLs, not the titles.
    assert "https://delicate.coffee/products/getuya-aa" in urls
    assert "https://delicate.coffee/products/kathima-ab-rested" in urls
    assert "https://delicate.coffee/products/halo-beriti-special-prep" in urls
    assert "https://delicate.coffee/products/bare-special-prep" in urls
    assert "https://delicate.coffee/products/kii-aa-1" in urls

    assert all(u.startswith("https://delicate.coffee/products/") for u in urls)
    assert all("/collections/" not in u for u in urls)


async def test_retired_prints_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    # print-1..print-4 are retired "coffee bud" art prints, not coffee.
    assert not any("print" in u for u in urls)
    for handle in ("print-1", "print-2", "print-3", "print-4"):
        assert f"/products/{handle}" not in urls


def test_stock_status_keyed_by_canonical_url(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    asyncio.run(scraper._extract_product_urls_from_store(STORE_URL))

    stock = scraper._shopify_stock_status
    assert stock["https://delicate.coffee/products/getuya-aa"] is True
    assert stock["https://delicate.coffee/products/kathima-ab-rested"] is True
    # kathima-ab is the sold-out sibling of the rested lot.
    assert stock["https://delicate.coffee/products/kathima-ab"] is False
    # Excluded prints never get a stock entry.
    assert "https://delicate.coffee/products/print-1" not in stock
    assert all("/collections/" not in url for url in stock)


def test_currency_pinned_to_home_market():
    scraper = _make_scraper()
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True


def test_currency_pinned_in_postprocess():
    from kissaten.schemas import CoffeeBean

    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://delicate.coffee/products/test-bean",
        roaster="Delicate Coffee",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "USD"


def test_top_level_price_is_derived_from_price_options():
    """Regression: 3 of 6 live beans stored ``price: null``.

    Every Delicate coffee is 125 g at a flat USD 19.00, and the extractor
    reported that correctly in ``price_options`` — but it also reported
    ``weight=125`` with no top-level ``price``. ``set_default_price_option``
    only ran when *both* price and weight were unset, so the bean was stored
    with a null price and normalized to a null ``price_usd`` at refresh time.
    """
    from kissaten.schemas import CoffeeBean

    bean = CoffeeBean(
        name="Halo Beriti - Special Prep",
        url="https://delicate.coffee/products/halo-beriti-special-prep",
        roaster="Delicate Coffee",
        origins=[{"country": "ID"}],
        price_options=[{"weight": 125, "price": 19.0, "currency": "USD"}],
        weight=125,
        currency="USD",
    )

    assert bean.price == 19.0
    assert bean.weight == 125
    assert bean.price_options[0].price == 19.0


def test_top_level_price_is_not_overwritten_when_present():
    from kissaten.schemas import CoffeeBean

    bean = CoffeeBean(
        name="Kii AA",
        url="https://delicate.coffee/products/kii-aa-1",
        roaster="Delicate Coffee",
        origins=[{"country": "KE"}],
        price_options=[{"weight": 125, "price": 19.0}],
        price=17.5,
        weight=125,
        currency="USD",
    )

    assert bean.price == 17.5


def test_price_stays_none_without_price_options():
    from kissaten.schemas import CoffeeBean

    bean = CoffeeBean(
        name="Giveaway",
        url="https://delicate.coffee/products/giveaway",
        roaster="Delicate Coffee",
        origins=[{"country": "KE"}],
        price_options=[],
        weight=125,
        currency="USD",
    )

    assert bean.price is None


def test_price_stays_none_when_options_carry_no_weight():
    # A price option without a weight cannot be promoted to a per-gram price,
    # so the top-level price stays unset rather than being guessed.
    from kissaten.schemas import CoffeeBean

    bean = CoffeeBean(
        name="Weight Unknown Lot",
        url="https://delicate.coffee/products/weight-unknown",
        roaster="Delicate Coffee",
        origins=[{"country": "KE"}],
        price_options=[{"price": 19.0}],
        currency="USD",
    )

    assert bean.price is None
    assert bean.weight is None


def _bean_without_price(url: str, price_options: list[dict] | None = None):
    """Build the exact shape the live run stored: a bag size but no top-level price."""
    from kissaten.schemas import CoffeeBean

    return CoffeeBean(
        name="Halo Beriti - Special Prep",
        url=url,
        roaster="Delicate Coffee",
        origins=[{"country": "ID"}],
        price_options=price_options if price_options is not None else [],
        weight=125,
        currency="USD",
    )


async def _seeded_scraper(handle: str = "halo-beriti-special-prep") -> DelicateCoffeeScraper:
    """Scraper whose ``_shopify_product_data`` holds the fixture products."""
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    scraper._fetch_all_shopify_products = fake_fetch
    await scraper._extract_product_urls_from_store(STORE_URL)
    assert f"https://delicate.coffee/products/{handle}" in scraper._shopify_product_data
    return scraper


def test_price_backfilled_from_shopify_variant_when_top_level_price_missing():
    """Regression: 3 of 6 live beans stored ``price: null``.

    The JSON-only path never shows the extractor a rendered price, so it
    reported 19.00 in ``price_options`` but left the optional top-level
    ``price`` unset. ``variants[0]["price"]`` is authoritative, so
    ``postprocess_extracted_bean`` re-derives the top-level price from it.
    """
    scraper = asyncio.run(_seeded_scraper())
    bean = _bean_without_price("https://delicate.coffee/products/halo-beriti-special-prep")

    assert bean.price is None

    out = scraper.postprocess_extracted_bean(bean)

    assert out.price == 19.0
    assert out.weight == 125
    assert out.currency == "USD"


def test_price_backfill_assignment_passes_check_prices():
    # CoffeeBean validates assignment, so the backfill re-runs the per-gram
    # range check. 19.00 USD for 125 g is $0.15/g — inside the accepted band,
    # so no ValidationError and the bean survives postprocessing.
    from pydantic import ValidationError

    scraper = asyncio.run(_seeded_scraper())
    bean = _bean_without_price("https://delicate.coffee/products/getuya-aa")

    try:
        out = scraper.postprocess_extracted_bean(bean)
    except ValidationError as e:  # pragma: no cover - regression guard
        raise AssertionError(f"price backfill failed CoffeeBean validation: {e}") from e

    assert out is not None
    assert out.price == 19.0


def test_price_backfill_does_not_overwrite_an_extracted_price():
    scraper = asyncio.run(_seeded_scraper())
    bean = _bean_without_price(
        "https://delicate.coffee/products/danche",
        price_options=[{"weight": 125, "price": 19.0, "currency": "USD"}],
    )
    bean.price = 21.0  # a promo price the extractor read off the page

    out = scraper.postprocess_extracted_bean(bean)

    assert out.price == 21.0


def test_price_backfill_prefers_an_available_variant():
    # The retired art prints are the products whose only variant is sold out
    # and priced at "0.00"; neither may become a bean price.
    scraper = _make_scraper()
    scraper._shopify_product_data["https://delicate.coffee/products/print-1"] = {
        "variants": [{"title": "Default Title", "price": "0.00", "available": False}]
    }
    bean = _bean_without_price("https://delicate.coffee/products/print-1")

    out = scraper.postprocess_extracted_bean(bean)

    assert out.price is None


def test_price_backfill_skips_unusable_variant_amounts():
    scraper = _make_scraper()
    scraper._shopify_product_data["https://delicate.coffee/products/broken"] = {
        "variants": [
            {"price": None, "available": True},
            {"price": "n/a", "available": True},
            {"price": "0", "available": True},
            {"price": "19.00", "available": True},
        ]
    }
    bean = _bean_without_price("https://delicate.coffee/products/broken")

    out = scraper.postprocess_extracted_bean(bean)

    assert out.price == 19.0


def test_price_backfill_falls_back_to_product_level_price():
    # Newer payloads can carry the amount outside the variants array.
    scraper = _make_scraper()
    scraper._shopify_product_data["https://delicate.coffee/products/new-shape"] = {
        "variants": [],
        "prices": {"price": "19.00"},
    }
    bean = _bean_without_price("https://delicate.coffee/products/new-shape")

    out = scraper.postprocess_extracted_bean(bean)

    assert out.price == 19.0


def test_price_backfill_without_product_data_is_a_no_op():
    # A URL the store listing never carried (or an out-of-session bean) must
    # leave the price alone rather than raising.
    scraper = _make_scraper()
    bean = _bean_without_price("https://delicate.coffee/products/unknown-lot")

    out = scraper.postprocess_extracted_bean(bean)

    assert out.price is None
    assert out.currency == "USD"


def test_price_backfill_matches_percent_encoded_handles():
    # products.json returns raw non-ASCII handles while CoffeeBean.url is an
    # HttpUrl, so the lookup falls back to the decoded comparison.
    scraper = _make_scraper()
    scraper._shopify_product_data["https://delicate.coffee/products/サマーブレンド"] = {
        "variants": [{"price": "19.00", "available": True}]
    }
    bean = _bean_without_price(
        "https://delicate.coffee/products/%E3%82%B5%E3%83%9E%E3%83%BC%E3%83%96%E3%83%AC%E3%83%B3%E3%83%89"
    )

    out = scraper.postprocess_extracted_bean(bean)

    assert out.price == 19.0


def test_price_options_currency_pinned_to_usd():
    # A guessed/unset option currency poisons price_usd normalization at
    # refresh time, so every option is pinned to the store currency.
    scraper = asyncio.run(_seeded_scraper())
    bean = _bean_without_price(
        "https://delicate.coffee/products/kii-aa",
        price_options=[
            {"weight": 125, "price": 19.0, "currency": "GBP"},
            {"weight": 1000, "price": 150.0, "currency": None},
        ],
    )

    out = scraper.postprocess_extracted_bean(bean)

    assert out.currency == "USD"
    assert [opt.currency for opt in out.price_options] == ["USD", "USD"]


async def test_extraction_backfills_price_when_the_ai_omits_it(mocker):
    """End-to-end through the real extraction path.

    Stubs the extractor with the worst case seen live — a bean with a bag size
    but no top-level ``price`` and no usable price option — and asserts the
    products.json variant price still lands on the bean, so a coffee is never
    stored at ``price: null`` / null ``price_usd``.
    """
    from bs4 import BeautifulSoup

    scraper = await _seeded_scraper("getuya-aa")
    url = "https://delicate.coffee/products/getuya-aa"
    ai_extractor = mocker.AsyncMock()
    ai_extractor.extract_coffee_data.return_value = _bean_without_price(url)

    bean = await scraper._extract_bean_with_ai(ai_extractor, BeautifulSoup("<html><body></body></html>", "lxml"), url)

    assert bean is not None
    assert bean.price == 19.0
    assert bean.currency == "USD"
