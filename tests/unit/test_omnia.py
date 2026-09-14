"""Unit tests for the Omnia Coffee Roasters scraper.

The tests are fully self-contained (no network): they stub
``_fetch_all_shopify_products`` / ``_fetch_page_with_escalation`` with
synthetic product dicts mirroring the live ``frontpage`` collection
("Our Coffee Offerings", 9 products: 7 beans + 2 subscription packs).

Covered per-scraper behaviour:
- The ``exclude_slugs`` gate drops the subscription packs but keeps every bean.
- Product URLs are canonicalized to the no-collection ``/products/<handle>``
  form that Omnia's pages declare in ``<link rel="canonical">``.
- The any-available-variant stock rule.
- Shopify Markets geo-conversion defence: the CA market param is appended to
  every paginated listing request, the store currency is pinned to CAD with
  ``_currency_detected=True`` so collection-page detection cannot override it,
  and ``postprocess_extracted_bean`` re-stamps CAD.
"""

import pytest

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.omnia import OmniaCoffeeRoastersScraper

PRODUCTS_JSON_URL = "https://www.omniacoffeeroasters.com/collections/frontpage/products.json"


def _product(handle: str, title: str, available: bool = True) -> dict:
    return {
        "handle": handle,
        "title": title,
        "product_type": "Retail Coffee",
        "variants": [{"price": "24.00", "available": available}],
    }


def _live_catalogue() -> list[dict]:
    """Synthetic mirror of the live frontpage collection (9 products)."""
    return [
        _product("elsalvador-mapache-estates", "Diablo"),
        _product("copy-of-colombia-madre-laura-anaerobic-natural", "Colombia Sugarcane Decaf"),
        _product("costa-rica-corazon-de-jesus-salitre", "COSTA RICA CORAZON DE JESUS SALITRE NATURAL"),
        _product("ethiopia-halo-beriti-natural", "Ethiopia Halo Beriti Natural"),
        _product("colombia-finca-el-paraiso-java", "COLOMBIA FINCA EL PARAISO SL28 100g"),
        _product("roasters-subscription-pack", "Roasters Subscription Pack"),
        _product("2-pack-subscription", "Diablo Subscription Pack"),
        _product("colombia-sidra-bourbon", "Colombia Sidra Bourbon"),
        _product("colombia-siete-soles-natural", "COLOMBIA SIETE SOLES NATURAL"),
    ]


def _install_catalogue(scraper: OmniaCoffeeRoastersScraper, products: list[dict]) -> None:
    async def fake_fetch(url: str) -> list[dict]:
        return products

    scraper._fetch_all_shopify_products = fake_fetch  # type: ignore[method-assign]


def _make_bean(url: str) -> CoffeeBean:
    return CoffeeBean(
        name="Ethiopia Halo Beriti Natural", roaster="Omnia Coffee Roasters", url=url, origins=[], price_options=[]
    )


@pytest.fixture
def scraper():
    return OmniaCoffeeRoastersScraper()


class TestExtractProductUrlsFromStore:
    @pytest.mark.asyncio
    async def test_keeps_all_beans_and_drops_subscription_packs(self, scraper):
        _install_catalogue(scraper, _live_catalogue())

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        # 9 captured products, the 2 subscription-pack handles dropped.
        assert len(urls) == 7
        assert not any("subscription" in u for u in urls)

        # Representative members of the live set: single origin, decaf, the
        # 100g bag listing.
        assert "https://www.omniacoffeeroasters.com/products/ethiopia-halo-beriti-natural" in urls
        assert "https://www.omniacoffeeroasters.com/products/copy-of-colombia-madre-laura-anaerobic-natural" in urls
        assert "https://www.omniacoffeeroasters.com/products/colombia-finca-el-paraiso-java" in urls

    @pytest.mark.asyncio
    async def test_canonicalizes_to_no_collection_urls(self, scraper):
        _install_catalogue(scraper, [_product("ethiopia-halo-beriti-natural", "Ethiopia Halo Beriti Natural")])

        urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        assert urls == ["https://www.omniacoffeeroasters.com/products/ethiopia-halo-beriti-natural"]

    @pytest.mark.asyncio
    async def test_marks_in_stock_from_any_available_variant(self, scraper):
        products = [
            _product("ethiopia-halo-beriti-natural", "Ethiopia Halo Beriti Natural"),
            _product("colombia-sidra-bourbon", "Colombia Sidra Bourbon", available=False),
        ]
        _install_catalogue(scraper, products)

        await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

        stock = scraper._shopify_stock_status
        assert stock["https://www.omniacoffeeroasters.com/products/ethiopia-halo-beriti-natural"] is True
        assert stock["https://www.omniacoffeeroasters.com/products/colombia-sidra-bourbon"] is False


class TestCADPinning:
    def test_store_currency_pinned_and_detected(self, scraper):
        # _currency_detected=True prevents _scrape_new_products from fetching
        # the collection page and letting a geo-converted currency in.
        assert scraper.store_currency == "CAD"
        assert scraper._currency_detected is True

    @pytest.mark.asyncio
    async def test_listing_requests_pin_ca_market(self, scraper, mocker):
        recorded_urls = []

        async def fake_escalation(url: str):
            recorded_urls.append(url)
            return {"products": []}, False

        mocker.patch.object(scraper, "_fetch_page_with_escalation", side_effect=fake_escalation)

        await scraper._fetch_all_shopify_products(PRODUCTS_JSON_URL)

        assert recorded_urls == [
            f"{PRODUCTS_JSON_URL}?country=CA&limit=250&page=1",
        ]

    def test_postprocess_forces_cad(self, scraper):
        bean = _make_bean("https://www.omniacoffeeroasters.com/products/ethiopia-halo-beriti-natural")
        bean.currency = "GBP"
        out = scraper.postprocess_extracted_bean(bean)
        assert out is not None
        assert out.currency == "CAD"


class TestRegistryConsistency:
    def test_roaster_name_matches_registry(self, scraper):
        from kissaten.scrapers.registry import get_registry

        info = get_registry().get_scraper_info("omnia")
        assert info is not None
        assert info.roaster_name == "Omnia Coffee Roasters"
        assert info.currency == "CAD"
        assert info.country == "Canada"
