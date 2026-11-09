"""Unit tests for the Nord Kaffe scraper (fixture-based, no network)."""

import copy
import json
from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.nord_kaffe import NordKaffeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
LISTING_URL = NordKaffeScraper._STORE_API_URL + "?" + NordKaffeScraper._LISTING_QUERY.format(page=1)
PRODUCT_URL = "https://nordoslo.no/butikk/kaffe/filter/colombia-condor/"

COLOMBIA_CONDOR = "https://nordoslo.no/butikk/kaffe/filter/colombia-condor/"
BRURUNDI_KIBINGO = "https://nordoslo.no/butikk/kaffe/filter/burundi-kibingo-intenso/"
EL_TESORO = "https://nordoslo.no/butikk/kaffe/filter/colombia-el-tesoro-microlot/"
KOFFEINFRI = "https://nordoslo.no/butikk/kaffe/filter/nord-koffeinfri-espresso/"
ESPRESSO_BRASIL = "https://nordoslo.no/butikk/kaffe/espresso/nord-espresso-fra-brasil/"
ESPRESSO_ORGANIC = "https://nordoslo.no/butikk/kaffe/espresso/nord-okologisk-espresso/"


def _fixture_products() -> list[dict]:
    return json.loads((FIXTURES / "nord_kaffe_products_api.json").read_text())


def _product_by_slug(slug: str) -> dict:
    return next(p for p in _fixture_products() if p["slug"] == slug)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeClient:
    """Minimal stand-in for the httpx async client, keyed by URL substring."""

    def __init__(self, routes):
        self._routes = routes

    async def get(self, url):
        for token, payload in self._routes.items():
            if token in url:
                return _FakeResponse(payload)
        raise AssertionError(f"Unexpected URL requested in test: {url}")


def _make_scraper() -> NordKaffeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return NordKaffeScraper(api_key="test-api-key")


def _patch_listing(mocker, scraper: NordKaffeScraper, products: list[dict]) -> None:
    # Page 1 serves the fixture, page 2 is empty (ends the pagination loop).
    mocker.patch.object(
        scraper,
        "client",
        _FakeClient({"page=1": products, "page=2": []}),
    )


def test_registry_entry():
    info = get_registry().get_scraper_info("nord-kaffe")
    assert info is not None
    assert info.roaster_name == "Nord Kaffe"
    assert info.currency == "NOK"
    assert info.country == "Norway"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Nord Kaffe"


async def test_store_urls_use_store_api_listing():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == ["https://nordoslo.no/wp-json/wc/store/v1/products?per_page=100&page=1"]
    assert urls == [LISTING_URL]


async def test_extracts_coffee_urls_from_store_api(mocker):
    scraper = _make_scraper()
    _patch_listing(mocker, scraper, _fixture_products())

    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    # Filter-roasted single origins (categories ["Filter", "Kaffe"]).
    assert COLOMBIA_CONDOR in urls
    assert BRURUNDI_KIBINGO in urls
    assert EL_TESORO in urls
    assert KOFFEINFRI in urls
    # Espresso blends live under /butikk/kaffe/espresso/ and are coffee too.
    assert ESPRESSO_BRASIL in urls
    assert ESPRESSO_ORGANIC in urls
    # Every extracted URL uses the Norwegian /butikk/ store path.
    assert all("/butikk/" in u for u in urls)
    assert len(urls) == 6


async def test_sold_out_products_are_skipped(mocker):
    scraper = _make_scraper()
    _patch_listing(mocker, scraper, _fixture_products())

    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    # Both fixture sold-out items carry is_in_stock = false.
    assert "https://nordoslo.no/butikk/abonnement/kaffe-abonnement/" not in urls
    assert "https://nordoslo.no/butikk/kaffe/espresso/kaffeabonnement/" not in urls

    # Sold-out is checked BEFORE coffee-URL filtering, so flipping an
    # otherwise-valid in-stock coffee to sold out removes it on its own.
    products = copy.deepcopy(_fixture_products())
    condor = next(p for p in products if p["slug"] == "colombia-condor")
    condor["is_in_stock"] = False
    _patch_listing(mocker, scraper, products)

    urls = await scraper._extract_product_urls_from_store(LISTING_URL)
    assert COLOMBIA_CONDOR not in urls
    assert ESPRESSO_BRASIL in urls


async def test_equipment_and_subscription_products_are_excluded(mocker):
    scraper = _make_scraper()
    _patch_listing(mocker, scraper, _fixture_products())

    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    # Hario items live in "Utstyr"; the subscriptions in "Abonnement" (one of
    # them is even filed under the /butikk/kaffe/espresso/ path, so it only
    # gets caught by the abonnement/utstyr slug guard).
    assert not any("hario" in u for u in urls)
    assert not any("v60" in u for u in urls)
    assert not any("utstyr" in u for u in urls)
    assert not any("abonnement" in u for u in urls)


async def test_failed_listing_returns_empty(mocker):
    scraper = _make_scraper()

    class _FailingClient:
        async def get(self, url):
            raise RuntimeError("network down")

    mocker.patch.object(scraper, "client", _FailingClient())
    urls = await scraper._extract_product_urls_from_store(LISTING_URL)
    assert urls == []


def test_format_price_from_minor_units():
    prices = {
        "currency_minor_unit": 2,
        "currency_prefix": "",
        "currency_suffix": " kr",
        "currency_decimal_separator": ",",
    }
    assert NordKaffeScraper._format_price("28300", prices) == "283,00 kr"
    assert NordKaffeScraper._format_price(None, prices) == ""
    # The real Nord Kaffe payload uses a "kr " prefix with no suffix.
    condor = _product_by_slug("colombia-condor")["prices"]
    assert NordKaffeScraper._format_price("18500", condor) == "kr 185.00"


def test_build_product_soup_contains_product_facts():
    product = _product_by_slug("colombia-condor")
    soup = NordKaffeScraper._build_product_soup(product)
    text = soup.get_text(" ", strip=True)

    assert product["name"] in text
    assert "Price: kr 185.00 - kr 629.00" in text
    assert "Availability: In stock" in text
    # Norwegian description (origin/process/tasting notes for AI extraction).
    assert "smaksnotater" in text.lower()
    assert "plomme" in text


def test_build_product_soup_collapses_variant_attributes():
    product = _product_by_slug("colombia-condor")
    soup = NordKaffeScraper._build_product_soup(product)
    text = soup.get_text(" ", strip=True)

    # 8 variations collapse to unique values per attribute (250 g / 1 kg ×
    # four Kverningsgrad options).
    assert "Variants:" in text
    assert "Størrelse: 1000, 250" in text
    assert "Kverningsgrad: filtermalt, hele-bonner, kokmalt, presskannemalt" in text
    # Duplicates are collapsed, not repeated 8 times.
    assert text.count("presskannemalt") == 1


async def test_fetch_page_routes_product_urls_to_store_api(mocker):
    scraper = _make_scraper()
    product = _product_by_slug("colombia-condor")
    mocker.patch.object(
        scraper,
        "client",
        _FakeClient({"products?slug=colombia-condor": [product]}),
    )

    result = await scraper.fetch_page(PRODUCT_URL, use_playwright=False)
    assert result is not None
    assert product["name"] in result.get_text()


async def test_fetch_page_falls_back_to_html_for_non_product_urls(mocker):
    scraper = _make_scraper()
    sentinel = BeautifulSoup("<html><body>listing</body></html>", "lxml")

    async def fake_base_fetch(self, url, **kwargs):
        return sentinel

    mocker.patch.object(BaseScraper, "fetch_page", fake_base_fetch)
    result = await scraper.fetch_page("https://nordoslo.no/butikk/", use_playwright=False)
    assert result is sentinel


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://nordoslo.no/butikk/kaffe/filter/test-bean/",
        roaster="Nord Kaffe",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "NOK"


def test_home_currency_pinned_so_ai_default_is_not_gbp():
    # The Store API listing is a JSON document with no og:price:currency meta
    # tag, so the base class cannot detect the currency and falls back to GBP.
    # That GBP default was echoed into the extracted beans.
    scraper = _make_scraper()
    assert scraper.store_currency == "NOK"
    assert scraper._currency_detected is True


# ---------------------------------------------------------------------------
# BUG 1: price/currency reaching the AI extractor
# ---------------------------------------------------------------------------


def _variation_of(product: dict) -> dict:
    """A ``?slug=`` response entry of the kind WooCommerce returns first.

    A real variation carries only its own ``prices.price`` and one
    variation-specific image — neither text field, and a ``null`` price_range.
    """
    return {
        "id": (product.get("id") or 0) + 9000,
        "type": "variation",
        "slug": product.get("slug"),
        "name": product.get("name"),
        "permalink": product.get("permalink"),
        "description": "",
        "short_description": "",
        "images": [{"src": "https://nordoslo.no/variation-only.png"}],
        "variations": [],
        "prices": {
            "price": "50700",
            "price_range": None,
            "currency_code": "NOK",
            "currency_minor_unit": 2,
            "currency_prefix": "kr ",
        },
    }


def test_select_store_product_skips_variation_entries():
    # ?slug=colombia-condor can return the 629.00 NOK 1 kg variation first and
    # the parent second; the variation has neither text field.
    parent = _product_by_slug("colombia-condor")
    variation = _variation_of(parent)

    assert NordKaffeScraper._select_store_product([variation, parent]) is parent
    # Order-independent: the parent also wins when it comes first.
    assert NordKaffeScraper._select_store_product([parent, variation]) is parent
    # A response holding nothing but variations still yields something.
    assert NordKaffeScraper._select_store_product([variation]) is variation
    assert NordKaffeScraper._select_store_product([]) is None


async def test_fetch_page_ignores_variation_entry_for_soup(mocker):
    # Regression: taking items[0] built a soup with only the product name, so
    # the extractor had no origin, no tasting notes and no price to work from.
    scraper = _make_scraper()
    parent = _product_by_slug("colombia-condor")
    mocker.patch.object(
        scraper,
        "client",
        _FakeClient({"products?slug=colombia-condor": [_variation_of(parent), parent]}),
    )

    soup = await scraper.fetch_page(COLOMBIA_CONDOR, use_playwright=False)
    text = soup.get_text(" ", strip=True)

    assert "kr 185.00" in text
    assert "kr 629.00" in text
    # Norwegian prose from the parent product survived.
    assert "smaksnotater" in text.lower()


def test_build_product_soup_falls_back_to_price_when_range_is_null():
    # price_range is null for every flat-priced product, so the real price was
    # missing from the soup and the extractor invented one.
    kibingo = _product_by_slug("burundi-kibingo-intenso")
    assert kibingo["prices"]["price_range"] is None

    text = NordKaffeScraper._build_product_soup(kibingo).get_text(" ", strip=True)
    assert "Price: kr 252.00" in text


def test_format_price_ignores_zero_amounts():
    # PriceOption.price is gt=0, so a "kr 0.00" line would only earn a failed
    # validation round-trip (WooCommerce giveaway / placeholder products).
    prices = {"currency_minor_unit": 2, "currency_prefix": "kr "}
    assert NordKaffeScraper._format_price("0", prices) == ""


def test_build_product_soup_states_the_currency_code():
    # Without an explicit currency the extractor defaulted to GBP, which then
    # failed the check_prices range check once NOK was pinned.
    for slug in ("burundi-kibingo-intenso", "colombia-condor", "colombia-el-tesoro-microlot"):
        text = NordKaffeScraper._build_product_soup(_product_by_slug(slug)).get_text(" ", strip=True)
        assert "Currency: NOK" in text, slug


def test_postprocess_accepts_real_nok_price_after_currency_pin():
    # The live crash: pinning NOK re-ran check_prices on a price the extractor
    # had chosen in GBP, which fell below the NOK per-gram minimum.
    scraper = _make_scraper()
    kibingo = _product_by_slug("burundi-kibingo-intenso")
    soup = NordKaffeScraper._build_product_soup(kibingo)
    text = soup.get_text(" ", strip=True)
    assert "Price: kr 252.00" in text

    bean = CoffeeBean(
        name="Burundi Kibingo Intenso",
        url=BRURUNDI_KIBINGO,
        roaster="Nord Kaffe",
        origins=[{"country": "BI"}],
        price_options=[{"weight": 250, "price": 252.0}],
        weight=250,
        price=252.0,
        currency="NOK",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "NOK"
    assert out.price_options[0].currency == "NOK"


def test_postprocess_normalises_every_price_option_currency():
    # The live run stored one bean with a GBP price_option and two with null,
    # against an NOK bean currency — that poisons price_usd normalization.
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Burundi Kibingo Intenso",
        url=BRURUNDI_KIBINGO,
        roaster="Nord Kaffe",
        origins=[{"country": "BI"}],
        price_options=[
            {"weight": 250, "price": 252.0, "currency": "GBP"},
            {"weight": 1000, "price": 900.0, "currency": None},
        ],
        weight=250,
        price=252.0,
        currency="NOK",
    )

    out = scraper.postprocess_extracted_bean(bean)

    assert out.currency == "NOK"
    assert [opt.currency for opt in out.price_options] == ["NOK", "NOK"]


# ---------------------------------------------------------------------------
# BUG 1: both WooCommerce text fields must reach the extractor
# ---------------------------------------------------------------------------


def test_build_product_soup_carries_both_text_fields():
    """Regression: ``description or short_description`` dropped the origin half.

    ``short_description`` holds the region/producer/payment prose and
    ``description`` the tasting notes. They are complementary, so the soup must
    carry both — otherwise the extractor never sees the region, the producer or
    the direct-payment figure.
    """
    product = _product_by_slug("colombia-condor")
    text = NordKaffeScraper._build_product_soup(product).get_text(" ", strip=True)

    # short_description: region, producer/cooperative, direct-payment figure.
    assert "Huila" in text
    assert "Forest Academy" in text
    assert "350 000 COP" in text
    # description: the tasting-note block.
    assert "smaksnotater" in text.lower()
    assert "plomme" in text


def test_build_product_soup_labels_each_text_field_separately():
    product = _product_by_slug("colombia-condor")
    soup = NordKaffeScraper._build_product_soup(product)

    assert NordKaffeScraper._SHORT_DESCRIPTION_HEADING in soup.get_text()
    assert NordKaffeScraper._DESCRIPTION_HEADING in soup.get_text()
    assert NordKaffeScraper._SHORT_DESCRIPTION_HEADING != NordKaffeScraper._DESCRIPTION_HEADING
    # The origin prose comes first, so it survives any downstream truncation.
    text = soup.get_text(" ", strip=True)
    assert text.index(NordKaffeScraper._SHORT_DESCRIPTION_HEADING) < text.index("smaksnotater")


def test_short_description_alone_still_emits_the_description():
    product = copy.deepcopy(_product_by_slug("colombia-condor"))
    product["short_description"] = ""
    text = NordKaffeScraper._build_product_soup(product).get_text(" ", strip=True)

    assert NordKaffeScraper._SHORT_DESCRIPTION_HEADING not in text
    assert NordKaffeScraper._DESCRIPTION_HEADING in text
    assert "smaksnotater" in text.lower()


def test_description_alone_still_emits_the_short_description():
    product = copy.deepcopy(_product_by_slug("colombia-condor"))
    product["description"] = ""
    text = NordKaffeScraper._build_product_soup(product).get_text(" ", strip=True)

    assert NordKaffeScraper._DESCRIPTION_HEADING not in text
    assert NordKaffeScraper._SHORT_DESCRIPTION_HEADING in text
    assert "Huila" in text
    assert "350 000 COP" in text


def test_both_text_fields_empty_emits_neither_heading():
    product = copy.deepcopy(_product_by_slug("colombia-condor"))
    product["description"] = ""
    product["short_description"] = ""
    text = NordKaffeScraper._build_product_soup(product).get_text(" ", strip=True)

    assert NordKaffeScraper._SHORT_DESCRIPTION_HEADING not in text
    assert NordKaffeScraper._DESCRIPTION_HEADING not in text
    # The rest of the soup is unaffected.
    assert "Colombia Condor" in text
    assert "kr 185.00" in text


# ---------------------------------------------------------------------------
# BUG 2: og:image from the Store API media set, <img> stripped from the text
# ---------------------------------------------------------------------------

STALE_ATTACHMENT = "https://nordoslo.no/wp-content/uploads/2023/08/burundi-kibingo-intenso-300%C3%97300.webp"


def test_store_product_payload_carries_images():
    product = _product_by_slug("colombia-condor")
    assert product["images"], "fixture must carry the Store API images array"
    assert product["images"][0]["src"].startswith("https://")


def test_soup_declares_og_image_from_the_store_media_set():
    product = _product_by_slug("colombia-condor")
    soup = NordKaffeScraper._build_product_soup(product)

    meta = soup.find("meta", attrs={"property": "og:image"})
    assert meta is not None
    assert meta["content"] == product["images"][0]["src"]
    # og:image is the first thing the base extractor reads, so the compact soup
    # now resolves an image without any post-extraction machinery.
    assert BaseScraper._extract_image_url_from_soup(soup) == product["images"][0]["src"]


def test_og_image_falls_back_to_the_thumbnail():
    product = copy.deepcopy(_product_by_slug("colombia-condor"))
    del product["images"][0]["src"]
    soup = NordKaffeScraper._build_product_soup(product)

    assert BaseScraper._extract_image_url_from_soup(soup) == product["images"][0]["thumbnail"]


def test_og_image_skips_unusable_entries():
    product = copy.deepcopy(_product_by_slug("colombia-condor"))
    product["images"] = [
        "not-a-dict",
        {"src": "/relative/path.png"},
        {"thumbnail": "relative.png"},
        {"src": "https://nordoslo.no/ok.png"},
    ]
    soup = NordKaffeScraper._build_product_soup(product)

    assert BaseScraper._extract_image_url_from_soup(soup) == "https://nordoslo.no/ok.png"


def test_og_image_absent_when_the_product_has_no_images():
    product = copy.deepcopy(_product_by_slug("colombia-condor"))
    product["images"] = []
    soup = NordKaffeScraper._build_product_soup(product)

    assert soup.find("meta", attrs={"property": "og:image"}) is None
    assert BaseScraper._extract_image_url_from_soup(soup) is None
    # The text blocks are still emitted.
    assert "Huila" in soup.get_text(" ", strip=True)


def test_og_image_with_query_string_round_trips():
    # The content attribute is HTML-escaped; BeautifulSoup must decode it back
    # to the URL the store serves.
    product = copy.deepcopy(_product_by_slug("colombia-condor"))
    product["images"][0]["src"] = "https://nordoslo.no/wp-content/uploads/shot.png?w=600&h=600"
    soup = NordKaffeScraper._build_product_soup(product)

    assert (
        BaseScraper._extract_image_url_from_soup(soup) == "https://nordoslo.no/wp-content/uploads/shot.png?w=600&h=600"
    )


def test_stale_attachment_image_never_reaches_the_soup():
    """The text fields embed WordPress attachment links that go stale.

    An ``<img>`` left in the description would let the extractor pick a dead
    attachment URL, and since the base only fills ``image_url`` when the bean
    has none, ``og:image`` would never win. Stripping the tags removes the
    hazard at source.
    """
    product = copy.deepcopy(_product_by_slug("burundi-kibingo-intenso"))
    product["description"] = f'<p><img src="{STALE_ATTACHMENT}" alt="Kibingo"></p><p>Flavor notes: gooseberries</p>'
    product["short_description"] = f'<p><img srcset="{STALE_ATTACHMENT} 2x"></p><p>Kayanza, Burundi</p>'
    soup = NordKaffeScraper._build_product_soup(product)

    assert soup.find("img") is None
    assert STALE_ATTACHMENT not in str(soup)
    # The prose around the images survives, and og:image still resolves.
    assert "gooseberries" in soup.get_text(" ", strip=True)
    assert BaseScraper._extract_image_url_from_soup(soup) == product["images"][0]["src"]


def test_text_field_with_only_an_image_emits_nothing():
    product = copy.deepcopy(_product_by_slug("colombia-condor"))
    product["short_description"] = f'<p><img src="{STALE_ATTACHMENT}"></p>'
    text = NordKaffeScraper._build_product_soup(product).get_text(" ", strip=True)

    assert NordKaffeScraper._SHORT_DESCRIPTION_HEADING not in text
    assert NordKaffeScraper._DESCRIPTION_HEADING in text
