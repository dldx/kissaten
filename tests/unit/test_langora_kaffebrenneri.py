"""Unit tests for the Langøra Kaffebrenneri scraper.

The primary test runs against a **captured fixture** of the live ``produkter``
collection (30 products on capture across the product types ``Kaffe``,
``Kaffeutstyr``, ``Merch``, ``Abonnement`` and ``Adventskalender``), so
catalogue drift — a renamed product_type, a new collection member, a
URL-format change — fails the test and is visible as a fixture diff.
Regenerate with ``.venv/bin/python tests/fixtures/capture.py`` (see the
fixture module docstring).

The captured fixture has 11 ``Kaffe`` products; exactly 10 extract. The
eleventh, "Test roast 1,4kg", is dropped upstream by the base class's global
``test-roast`` URL exclusion (``_get_excluded_url_patterns``) — deliberate
framework policy, not this scraper, and therefore pinned as an expectation
here rather than overridden.

The bespoke logic worth guarding is the two ``postprocess_review_flags``
cases: the multi-coffee bundle (flagged) vs. the single-format packs
(unflagged) — and the NOK currency pin.
"""

import json
from datetime import datetime
from pathlib import Path

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.langora_kaffebrenneri import LangoraKaffebrenneriScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "langora_produkter_products.json"
PRODUCTS_JSON_URL = "https://langorakaffe.no/collections/produkter/products.json"


def make_scraper() -> LangoraKaffebrenneriScraper:
    scraper = LangoraKaffebrenneriScraper()
    scraper._force_playwright = False
    return scraper


def make_bean(name: str, url: str) -> CoffeeBean:
    return CoffeeBean(
        name=name,
        roaster="Langøra Kaffebrenneri",
        url=url,
        origins=[{"country": "Kenya"}],
        price_options=[{"weight": 250, "price": 249.0}],
        currency="NOK",
        scraped_timestamp=datetime.now(),
    )


def _install_fixture(scraper: LangoraKaffebrenneriScraper) -> None:
    async def fake_fetch(url: str) -> list[dict]:
        return json.loads(FIXTURE.read_text())["products"]

    scraper._fetch_all_shopify_products = fake_fetch  # type: ignore[method-assign]


async def test_captured_catalogue_extracts_kaffe_set_only():
    scraper = make_scraper()
    _install_fixture(scraper)

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # 11 Kaffe products in the capture; test-roast-1-4kg is dropped by the
    # base class's global `test-roast` URL exclusion, so 10 survive.
    assert len(urls) == 10
    assert all(u.startswith("https://www.langorakaffe.no/products/") for u in urls)
    assert "https://www.langorakaffe.no/products/test-roast-1-4kg" not in urls

    # The whole live Kaffe set is present, incl. the multi-coffee bundle and
    # the drip-bag pack that must flow through the review pipeline.
    for handle in (
        "inoi-kianderi-aa-kenya",
        "amenaza-menor-decaf",
        "sitio-vargem-espresso",
        "dagens-kaffe-4-pack",
        "hverdag-fest",
        "grut-pa-tur-8-x-drip-bags",
    ):
        assert f"https://www.langorakaffe.no/products/{handle}" in urls

    # Genuine non-bean products never reach the catalogue: equipment/grinder,
    # merch, the subscription club and the Advent calendar are all excluded.
    non_bean = ("aeropress", "kaffekvern", "tote", "t-skjorte", "manedens-kaffe", "adventskalender")
    joined = " ".join(urls)
    assert not any(token in joined for token in non_bean)


async def test_marks_in_stock_from_any_available_variant():
    # Synthetic mixed-availability case (the capture has everything in stock):
    # one sold-out variant must not take the whole product out of stock.
    scraper = make_scraper()
    products = [
        {
            "id": 1,
            "title": "Inoi Kianderi AA – Kenya",
            "handle": "inoi-kianderi-aa-kenya",
            "product_type": "Kaffe",
            "body_html": "",
            "variants": [
                {"title": "250g.", "price": "249.00", "available": True},
                {"title": "1kg.", "price": "899.00", "available": False},
            ],
        },
    ]
    async def fake_fetch(url: str) -> list[dict]:
        return products

    scraper._fetch_all_shopify_products = fake_fetch  # type: ignore[method-assign]

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert scraper._shopify_stock_status["https://www.langorakaffe.no/products/inoi-kianderi-aa-kenya"] is True


def test_hverdag_fest_multi_coffee_bundle_flagged_as_kit():
    scraper = make_scraper()
    bean = make_bean("Hverdag + Fest | 4-pk", "https://www.langorakaffe.no/products/hverdag-fest")

    scraper._apply_product_flags(bean, "https://www.langorakaffe.no/products/hverdag-fest", is_new=True)

    assert bean.is_tasting_kit is True
    assert bean.requires_review is True


def test_single_format_packs_not_flagged_as_kit():
    scraper = make_scraper()

    # Dagens Kaffe 4-pk is 4x the same blend — not a multi-coffee kit.
    dagens = make_bean("Dagens Kaffe 4-pk", "https://www.langorakaffe.no/products/dagens-kaffe-4-pack")
    scraper._apply_product_flags(dagens, "https://www.langorakaffe.no/products/dagens-kaffe-4-pack", is_new=True)
    assert not dagens.is_tasting_kit

    # Grut På Tur is a single coffee in drip-bag format — not a kit.
    grut = make_bean("Grut På Tur - 8 x drip bags", "https://www.langorakaffe.no/products/grut-pa-tur-8-x-drip-bags")
    scraper._apply_product_flags(grut, "https://www.langorakaffe.no/products/grut-pa-tur-8-x-drip-bags", is_new=True)
    assert not grut.is_tasting_kit

    # A plain single origin is unflagged and unreviewed.
    single = make_bean("Inoi Kianderi AA – Kenya", "https://www.langorakaffe.no/products/inoi-kianderi-aa-kenya")
    scraper._apply_product_flags(single, "https://www.langorakaffe.no/products/inoi-kianderi-aa-kenya", is_new=True)
    assert not single.is_tasting_kit
    assert not single.requires_review


def test_currency_pinned_to_nok_in_init():
    scraper = make_scraper()

    assert scraper.store_currency == "NOK"
    assert scraper._currency_detected is True
    # Accept-Language removed so a geo-localized currency can't be served.
    assert "Accept-Language" not in scraper.headers
    assert "Accept-Language" not in getattr(scraper.client, "_base_headers", {})
    # The geo-detection override forces NOK regardless of the HTML payload.
    assert scraper._extract_currency_from_html(None) == "NOK"


def test_postprocess_extracted_bean_forces_nok():
    scraper = make_scraper()
    bean = make_bean("Inoi Kianderi AA – Kenya", "https://www.langorakaffe.no/products/inoi-kianderi-aa-kenya")
    bean.currency = "EUR"  # simulate a geo-converted extraction

    result = scraper.postprocess_extracted_bean(bean)

    assert result.currency == "NOK"
