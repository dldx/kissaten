"""Unit tests for the Espresso Winkel scraper (fixture-based, no network).

Espresso Winkel (espressowinkel.nl) is a Lightspeed eCom storefront; the
fixtures are trimmed copies of the real per-collection AJAX listing JSON
(``<collection>/pageN.ajax?format=json``).
"""

import json
from pathlib import Path

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.espresso_winkel import EspressoWinkelScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

GEBRANDE_URL = "https://www.espressowinkel.nl/koffie/gebrande-koffie/"
FERMENTATION_URL = "https://www.espressowinkel.nl/koffie/the-fermentation-project-van-james-hoffmann/"


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self) -> dict:
        return self._payload


def _make_scraper() -> EspressoWinkelScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return EspressoWinkelScraper(api_key="test-api-key")


def _gebrande_payload() -> dict:
    return json.loads((FIXTURES / "espresso_winkel_gebrande_page1.json").read_text())


def _fermentation_payload() -> dict:
    return json.loads((FIXTURES / "espresso_winkel_fermentation_page1.json").read_text())


def test_registry_entry():
    info = get_registry().get_scraper_info("espresso-winkel")
    assert info is not None
    assert info.roaster_name == "Espresso Winkel"
    assert info.currency == "EUR"
    assert info.country == "Netherlands"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Espresso Winkel"


async def test_store_urls_cover_roasted_and_fermentation_categories():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [GEBRANDE_URL, FERMENTATION_URL]


async def test_extracts_available_products_from_ajax_listing(monkeypatch):
    scraper = _make_scraper()

    async def fake_get(url, **kwargs):
        assert "page1.ajax?format=json" in url
        if "gebrande-koffie" in url:
            return _FakeResponse(_gebrande_payload())
        return _FakeResponse(_fermentation_payload())

    monkeypatch.setattr(scraper.client, "get", fake_get)

    urls = await scraper._extract_product_urls_from_store(GEBRANDE_URL)
    assert "https://www.espressowinkel.nl/milano-1kilo.html" in urls
    assert "https://www.espressowinkel.nl/proefpakket-1.html" in urls
    # Every extracted URL uses the flat Lightspeed .html product format.
    assert all(u.endswith(".html") for u in urls)


async def test_sold_out_product_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_get(url, **kwargs):
        return _FakeResponse(_gebrande_payload())

    monkeypatch.setattr(scraper.client, "get", fake_get)
    urls = await scraper._extract_product_urls_from_store(GEBRANDE_URL)
    assert "https://www.espressowinkel.nl/uganda-500-gram.html" not in urls


async def test_gift_cards_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_get(url, **kwargs):
        return _FakeResponse(_gebrande_payload())

    monkeypatch.setattr(scraper.client, "get", fake_get)
    urls = await scraper._extract_product_urls_from_store(GEBRANDE_URL)
    assert not any("cadeaubon" in u for u in urls)


async def test_fermentation_project_kit_is_kept_even_when_sold_out(monkeypatch):
    scraper = _make_scraper()

    async def fake_get(url, **kwargs):
        return _FakeResponse(_fermentation_payload())

    monkeypatch.setattr(scraper.client, "get", fake_get)
    urls = await scraper._extract_product_urls_from_store(FERMENTATION_URL)
    # The sold-out cupping set must still be extracted (tasting-kit review flow)
    assert "https://www.espressowinkel.nl/the-fermentation-project-cupping-set.html" in urls
    assert "https://www.espressowinkel.nl/the-fermentation-project-4x100gr.html" in urls


async def test_fermentation_kit_dropped_once_scraped_historically(monkeypatch):
    scraper = _make_scraper()

    async def fake_get(url, **kwargs):
        return _FakeResponse(_fermentation_payload())

    monkeypatch.setattr(scraper.client, "get", fake_get)
    cupping_set = "https://www.espressowinkel.nl/the-fermentation-project-cupping-set.html"

    # First run keeps the sold-out kit so it gets extracted.
    urls = await scraper._extract_product_urls_from_store(FERMENTATION_URL)
    assert cupping_set in urls

    # Once scraped, it leaves the current URL list so the next refresh marks
    # it out of stock via diffjson.
    scraper._mark_bean_as_scraped(cupping_set)
    urls = await scraper._extract_product_urls_from_store(FERMENTATION_URL)
    assert cupping_set not in urls
    assert "https://www.espressowinkel.nl/the-fermentation-project-4x100gr.html" in urls


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_get(url, **kwargs):
        raise RuntimeError("connection error")

    monkeypatch.setattr(scraper.client, "get", fake_get)
    urls = await scraper._extract_product_urls_from_store(GEBRANDE_URL)
    assert urls == []


async def test_pagination_walks_reported_pages(monkeypatch):
    scraper = _make_scraper()
    page2_payload = {
        "pages": 2,
        "count": 2,
        "products": [
            {
                "id": 1,
                "title": "Imola 500 gram",
                "url": "https://www.espressowinkel.nl/imola-500-gram.html",
                "available": True,
            }
        ],
    }

    async def fake_get(url, **kwargs):
        assert "page1.ajax?format=json" in url or "page2.ajax?format=json" in url
        if "page2.ajax" in url:
            return _FakeResponse(page2_payload)
        # Page 1 must declare the total page count for the walk to continue.
        page1_payload = _gebrande_payload()
        page1_payload["pages"] = 2
        return _FakeResponse(page1_payload)

    monkeypatch.setattr(scraper.client, "get", fake_get)
    urls = await scraper._extract_product_urls_from_store(GEBRANDE_URL)
    assert "https://www.espressowinkel.nl/imola-500-gram.html" in urls


def test_tasting_kit_url_patterns_cover_proefpakket_and_fermentation():
    scraper = _make_scraper()
    assert scraper.is_tasting_kit_url("https://www.espressowinkel.nl/proefpakket-1.html")
    assert scraper.is_tasting_kit_url("https://www.espressowinkel.nl/the-fermentation-project-4x100gr.html")
    assert not scraper.is_tasting_kit_url("https://www.espressowinkel.nl/milano-1kilo.html")


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://www.espressowinkel.nl/milano-1kilo.html",
        roaster="Espresso Winkel",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "EUR"
