"""Unit tests for the deterministic image_url backfill and Squarespace spec prose.

Covers the two extraction fixes from ``openwiki/operations/extraction-audit-2026-09.md``:

- Phase A: ``og:image`` + product spec prose survive the 15 Squarespace
  scrapers' meta-only ``fetch_page`` compaction.
- Phase B: ``BaseScraper`` records the raw page image at fetch time and
  backfills ``bean.image_url`` deterministically (page soup first, then the
  recorded URL, then the Shopify products.json payload for JSON-only scrapers).

It also pins the extraction-failure guard in ``_extract_bean_with_ai`` — a page
that yields neither an origin nor a price is not recorded — and the tasting-kit
exemption/review-flagging that sits alongside it.

All network access and cache/disk writes are stubbed — nothing in ``data/`` is
ever touched.
"""

import json

import pytest
from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers import _curl_http as httpx
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.blue_hour import BlueHourScraper
from kissaten.scrapers.coopers_coffee import CoopersCoffeeScraper
from kissaten.scrapers.echelon import EchelonScraper
from kissaten.scrapers.fifty_one_degrees_north import FiftyOneDegreesNorthScraper
from kissaten.scrapers.fika import FikaScraper
from kissaten.scrapers.forge import ForgeScraper
from kissaten.scrapers.fortitude import FortitudeScraper
from kissaten.scrapers.full_court_press import FullCourtPressScraper

# The 15 Squarespace scrapers that share the meta-only fetch_page helper.
from kissaten.scrapers.opal_coffee_roasters import OpalCoffeeRoastersScraper
from kissaten.scrapers.pala_kaffebrenneri import PalaKaffebrenneriScraper
from kissaten.scrapers.shopify_base import ShopifyJsonScraper
from kissaten.scrapers.smugglers_drop import SmugglersDropScraper
from kissaten.scrapers.spaceboy import SpaceboyCoffeeScraper
from kissaten.scrapers.sunday_coffee import SundayCoffeeScraper
from kissaten.scrapers.swan_song import SwanSongScraper
from kissaten.scrapers.tilted import TiltedScraper

# ---------------------------------------------------------------------------
# Test doubles (mirror tests/unit/test_shopify_scraper.py)
# ---------------------------------------------------------------------------


class _StubResponse:
    """httpx.Response-shaped stand-in for ``_install_client_stub``."""

    def __init__(self, status_code, *, text=""):
        self.status_code = status_code
        self.text = text
        self.content = (text or "").encode("utf-8")
        self.headers = {}
        self.url = ""

    def json(self):
        raise ValueError("no json payload set on stub")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(f"HTTP {self.status_code}", response=self)


def _install_client_stub(scraper, response_factory):
    """Replace ``scraper.client.get`` with an async stub."""

    async def fake_get(url, **kwargs):
        return response_factory(url, **kwargs)

    scraper.client.get = fake_get
    scraper._force_playwright = False


class _MinimalScraper(BaseScraper):
    """Concrete BaseScraper for unit tests (no registry entry)."""

    def __init__(self):
        super().__init__(
            roaster_name="Test Roaster",
            base_url="https://test-roaster.example",
            rate_limit_delay=0,
        )

    async def scrape(self, force_full_update: bool = False) -> list[CoffeeBean]:  # pragma: no cover
        return []

    async def get_store_urls(self) -> list[str]:  # pragma: no cover
        return []

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:  # pragma: no cover
        return []


class _MockShopifyScraper(ShopifyJsonScraper):
    def __init__(self):
        super().__init__(
            roaster_name="Proper Roaster",
            base_url="https://proper-roaster.com",
            products_json_urls=["https://proper-roaster.com/products.json"],
            rate_limit_delay=0,
        )


def _make_bean(image_url: str | None = None) -> CoffeeBean:
    return CoffeeBean(
        name="Test Bean",
        roaster="Test Roaster",
        url="https://test-roaster.example/product/1",
        image_url=image_url,
        origins=[{"country": "Ethiopia"}],
        price_options=[{"weight": 250, "price": 15.0}],
    )


def _stub_ai_extractor(mocker, bean: CoffeeBean):
    """Return an AsyncMock whose extract_coffee_data returns ``bean``."""
    ai_extractor = mocker.AsyncMock()
    ai_extractor.extract_coffee_data.return_value = bean
    return ai_extractor


# ---------------------------------------------------------------------------
# B1: _extract_image_url_from_soup
# ---------------------------------------------------------------------------


def _soup_with(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def test_extract_image_url_from_og_image_meta():
    soup = _soup_with('<meta property="og:image" content="https://cdn.example.com/bean.jpg">')
    assert BaseScraper._extract_image_url_from_soup(soup) == "https://cdn.example.com/bean.jpg"


def test_extract_image_url_from_twitter_image_meta():
    soup = _soup_with('<meta name="twitter:image" content="https://cdn.example.com/tw.jpg">')
    assert BaseScraper._extract_image_url_from_soup(soup) == "https://cdn.example.com/tw.jpg"


def test_extract_image_url_og_image_wins_over_twitter():
    soup = _soup_with(
        '<meta name="twitter:image" content="https://cdn.example.com/tw.jpg">'
        '<meta property="og:image" content="https://cdn.example.com/og.jpg">'
    )
    assert BaseScraper._extract_image_url_from_soup(soup) == "https://cdn.example.com/og.jpg"


def test_extract_image_url_from_json_ld_string():
    ld = json.dumps({"@type": "Product", "image": "https://cdn.example.com/ld.jpg"})
    soup = _soup_with(f'<script type="application/ld+json">{ld}</script>')
    assert BaseScraper._extract_image_url_from_soup(soup) == "https://cdn.example.com/ld.jpg"


def test_extract_image_url_from_json_ld_dict():
    ld = json.dumps({"@type": "Product", "image": {"url": "https://cdn.example.com/dict.jpg"}})
    soup = _soup_with(f'<script type="application/ld+json">{ld}</script>')
    assert BaseScraper._extract_image_url_from_soup(soup) == "https://cdn.example.com/dict.jpg"


def test_extract_image_url_from_json_ld_list_first_valid():
    ld = json.dumps(
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "Product",
                    "image": [{"url": "https://cdn.example.com/a.jpg"}, "https://cdn.example.com/b.jpg"],
                }
            ],
        }
    )
    soup = _soup_with(f'<script type="application/ld+json">{ld}</script>')
    assert BaseScraper._extract_image_url_from_soup(soup) == "https://cdn.example.com/a.jpg"


def test_extract_image_url_protocol_relative_is_upgraded():
    soup = _soup_with('<meta property="og:image" content="//cdn.example.com/bean.jpg">')
    assert BaseScraper._extract_image_url_from_soup(soup) == "https://cdn.example.com/bean.jpg"


def test_extract_image_url_rejects_data_url():
    soup = _soup_with('<meta property="og:image" content="data:image/png;base64,AAAA">')
    assert BaseScraper._extract_image_url_from_soup(soup) is None


def test_extract_image_url_rejects_relative_url():
    soup = _soup_with('<meta property="og:image" content="/images/bean.jpg">')
    assert BaseScraper._extract_image_url_from_soup(soup) is None


def test_extract_image_url_returns_none_when_absent():
    soup = _soup_with("<html><head></head><body><p>no image here</p></body></html>")
    assert BaseScraper._extract_image_url_from_soup(soup) is None


def test_extract_image_url_html_unescapes():
    soup = _soup_with('<meta property="og:image" content="https://cdn.example.com/a&amp;b.jpg">')
    assert BaseScraper._extract_image_url_from_soup(soup) == "https://cdn.example.com/a&b.jpg"


# ---------------------------------------------------------------------------
# A1: _extract_product_description_tag
# ---------------------------------------------------------------------------


DESCRIPTION_HTML = """
<html><body>
  <div class="product-description">
    <h3>Origin: Colombia</h3>
    <p>Altitude: 1800 - 2000 MASL</p>
    <p>Varietal: Caturra</p>
    <p>Process: Washed</p>
  </div>
  <div class="product-related-products">
    <a href="/shop/p/other">Related: Some Other Bean</a>
  </div>
</body></html>
"""


@pytest.fixture(scope="module")
def helper_scraper():
    return _MinimalScraper()


def test_extract_product_description_tag_finds_spec_prose(helper_scraper):
    tag = helper_scraper._extract_product_description_tag(BeautifulSoup(DESCRIPTION_HTML, "lxml"))
    assert tag is not None
    assert "Origin: Colombia" in tag.string
    assert "Altitude: 1800 - 2000 MASL" in tag.string


def test_extract_product_description_tag_excludes_related_products(helper_scraper):
    tag = helper_scraper._extract_product_description_tag(BeautifulSoup(DESCRIPTION_HTML, "lxml"))
    assert "Some Other Bean" not in tag.string


def test_extract_product_description_tag_dedupes_repeated_nodes(helper_scraper):
    spec = (
        "Origin: Colombia with a tasting profile of plum and dark chocolate that is long enough to pass the threshold"
    )
    html = f"""
    <html><body>
      <div class="product-description"><p>{spec}</p></div>
      <div class="product-description"><p>{spec}</p></div>
    </body></html>
    """
    tag = helper_scraper._extract_product_description_tag(BeautifulSoup(html, "lxml"))
    assert tag.string.count(spec) == 1


def test_extract_product_description_tag_caps_length(helper_scraper):
    html = """
    <html><body>
      <div class="product-description">origin: aaaa origin: bbbb origin: cccc origin: dddd origin: eeee
        origin: ffff origin: gggg origin: hhhh origin: iiii origin: jjjj</div>
    </body></html>
    """
    tag = helper_scraper._extract_product_description_tag(BeautifulSoup(html, "lxml"), max_chars=40)
    assert len(tag.string) == 40


def test_extract_product_description_tag_none_when_absent(helper_scraper):
    soup = BeautifulSoup("<html><body><p>tiny text</p></body></html>", "lxml")
    assert helper_scraper._extract_product_description_tag(soup) is None


def test_extract_product_description_tag_none_when_too_short(helper_scraper):
    soup = BeautifulSoup('<div class="product-description">short</div>', "lxml")
    assert helper_scraper._extract_product_description_tag(soup) is None


def test_extract_product_description_tag_does_not_mutate_input(helper_scraper):
    soup = BeautifulSoup(DESCRIPTION_HTML, "lxml")
    before = str(soup)
    helper_scraper._extract_product_description_tag(soup)
    assert str(soup) == before


# ---------------------------------------------------------------------------
# A2: all 15 Squarespace scrapers keep og:image + spec prose, drop related text
# ---------------------------------------------------------------------------

SQUARESPACE_SCRAPERS = [
    (OpalCoffeeRoastersScraper, "https://www.opalcoffeeroasters.co.uk/seasonal-coffee/p/migoti-hill"),
    (BlueHourScraper, "https://www.bluehourcoffee.co.uk/shop-coffee/p/sunrise"),
    (SundayCoffeeScraper, "https://sundaycoffee.co.uk/coffees/guatemala"),
    (FortitudeScraper, "https://www.fortitudecoffee.com/webshop/p/nyabihu"),
    (CoopersCoffeeScraper, "https://cooperstradingcompany.com/shop/p/colombia"),
    (FiftyOneDegreesNorthScraper, "https://www.51degreesnorthcoffee.com/single-origin-coffee/p/ethiopia"),
    (TiltedScraper, "https://tiltedcoffee.com/coffee-store/p/style-01"),
    (PalaKaffebrenneriScraper, "https://pala.no/butikk/p/ethiopia"),
    (SwanSongScraper, "https://www.swansong.coffee/coffee/p/bolivia"),
    (SmugglersDropScraper, "https://www.smugglersdrop.co.uk/shop/p/ace-of-clubs"),
    (FikaScraper, "https://www.fikacoffeeroasters.co.uk/coffee/p/colombia"),
    (EchelonScraper, "https://www.echeloncoffee.co.uk/shop/p/colombia"),
    (ForgeScraper, "https://www.forgecoffeeroasters.co.uk/store/p/popayan"),
    (SpaceboyCoffeeScraper, "https://spaceboycoffee.co.uk/shop/p/natural"),
    (FullCourtPressScraper, "https://www.fcp.coffee/products/p/full-court"),
]


def _squarespace_product_fixture() -> str:
    return """
    <html><head>
      <meta property="og:title" content="Test Bean">
      <meta property="og:description" content="Delicious single origin">
      <meta property="og:url" content="https://example.com/p/test">
      <meta property="og:type" content="product">
      <meta property="og:image" content="https://images.squarespace-cdn.com/bean.jpg">
      <meta property="product:price:amount" content="17.25">
      <meta property="product:price:currency" content="GBP">
      <meta property="product:availability" content="instock">
    </head><body>
      <div class="product-description">
        <p>Origin: Colombia</p>
        <p>Altitude: 1800 - 2000 MASL</p>
        <p>Varietal: Caturra</p>
        <p>Process: Washed</p>
        <p>Producer: Finca La Esperanza</p>
      </div>
      <div class="product-related-products">
        <a href="/p/other">Related: Some Other Bean</a>
      </div>
    </body></html>
    """


@pytest.mark.parametrize("scraper_cls,url", SQUARESPACE_SCRAPERS)
async def test_squarespace_fetch_page_keeps_og_image_and_spec_prose(monkeypatch, scraper_cls, url):
    scraper = scraper_cls()
    fixture_soup = BeautifulSoup(_squarespace_product_fixture(), "lxml")

    async def fake_fetch_page_with_screenshot(self, url, retries=0, use_playwright=False):
        return fixture_soup, None

    monkeypatch.setattr(BaseScraper, "fetch_page_with_screenshot", fake_fetch_page_with_screenshot)

    compact = await scraper.fetch_page(url)

    html = str(compact)
    # og:image survives the whitelist
    assert 'property="og:image"' in html
    assert 'content="https://images.squarespace-cdn.com/bean.jpg"' in html
    # spec prose survives compaction
    assert "Origin: Colombia" in compact.get_text()
    assert "Altitude: 1800 - 2000 MASL" in compact.get_text()
    # related-products block is still excluded
    assert "Some Other Bean" not in compact.get_text()


# ---------------------------------------------------------------------------
# B3: base backfill in _extract_bean_with_ai
# ---------------------------------------------------------------------------


async def test_extract_bean_with_ai_backfills_image_url_from_soup(mocker):
    scraper = _MinimalScraper()
    scraper._currency_detected = True
    ai_extractor = _stub_ai_extractor(mocker, _make_bean(image_url=None))

    soup = BeautifulSoup(
        '<meta property="og:image" content="https://cdn.example.com/og.jpg"><html><body></body></html>', "lxml"
    )
    bean = await scraper._extract_bean_with_ai(ai_extractor, soup, "https://test-roaster.example/product/1")

    assert str(bean.image_url) == "https://cdn.example.com/og.jpg"


async def test_extract_bean_with_ai_backfills_image_url_from_recorded_page(mocker):
    scraper = _MinimalScraper()
    scraper._currency_detected = True
    ai_extractor = _stub_ai_extractor(mocker, _make_bean(image_url=None))

    # Soup has no og:image — fall back to the URL recorded at raw-fetch time.
    soup = BeautifulSoup("<html><body></body></html>", "lxml")
    scraper._page_image_urls["https://test-roaster.example/product/1"] = "https://cdn.example.com/recorded.jpg"

    bean = await scraper._extract_bean_with_ai(ai_extractor, soup, "https://test-roaster.example/product/1")

    assert str(bean.image_url) == "https://cdn.example.com/recorded.jpg"


async def test_extract_bean_with_ai_does_not_override_existing_image_url(mocker):
    scraper = _MinimalScraper()
    scraper._currency_detected = True
    ai_extractor = _stub_ai_extractor(mocker, _make_bean(image_url="https://cdn.example.com/from-ai.jpg"))

    soup = BeautifulSoup(
        '<meta property="og:image" content="https://cdn.example.com/og.jpg"><html><body></body></html>', "lxml"
    )
    bean = await scraper._extract_bean_with_ai(ai_extractor, soup, "https://test-roaster.example/product/1")

    assert str(bean.image_url) == "https://cdn.example.com/from-ai.jpg"


async def test_extract_bean_with_ai_malformed_recorded_url_is_ignored(mocker):
    scraper = _MinimalScraper()
    scraper._currency_detected = True
    ai_extractor = _stub_ai_extractor(mocker, _make_bean(image_url=None))

    soup = BeautifulSoup("<html><body></body></html>", "lxml")
    scraper._page_image_urls["https://test-roaster.example/product/1"] = "not a url"

    bean = await scraper._extract_bean_with_ai(ai_extractor, soup, "https://test-roaster.example/product/1")

    assert bean is not None
    assert bean.image_url is None


# ---------------------------------------------------------------------------
# B4: Shopify JSON-only backfill
# ---------------------------------------------------------------------------


async def test_shopify_json_backfills_image_from_product_images(mocker):
    scraper = _MockShopifyScraper()
    scraper._currency_detected = True
    url = "https://proper-roaster.com/products/test-bean"
    scraper._shopify_product_data[url] = {
        "images": [{"src": "https://cdn.example.com/x.jpg"}],
        "variants": [{"featured_image": {"src": "https://cdn.example.com/other.jpg"}}],
    }
    ai_extractor = _stub_ai_extractor(mocker, _make_bean(image_url=None))

    bean = await scraper._extract_bean_with_ai(ai_extractor, BeautifulSoup("<html><body></body></html>", "lxml"), url)

    assert str(bean.image_url) == "https://cdn.example.com/x.jpg"


async def test_shopify_json_backfills_from_variant_featured_image(mocker):
    scraper = _MockShopifyScraper()
    scraper._currency_detected = True
    url = "https://proper-roaster.com/products/test-bean"
    scraper._shopify_product_data[url] = {
        "images": [],
        "variants": [{"featured_image": {"src": "https://cdn.example.com/variant.jpg"}}],
    }
    ai_extractor = _stub_ai_extractor(mocker, _make_bean(image_url=None))

    bean = await scraper._extract_bean_with_ai(ai_extractor, BeautifulSoup("<html><body></body></html>", "lxml"), url)

    assert str(bean.image_url) == "https://cdn.example.com/variant.jpg"


async def test_shopify_json_does_not_override_existing_image_url(mocker):
    scraper = _MockShopifyScraper()
    scraper._currency_detected = True
    url = "https://proper-roaster.com/products/test-bean"
    scraper._shopify_product_data[url] = {"images": [{"src": "https://cdn.example.com/x.jpg"}], "variants": []}
    ai_extractor = _stub_ai_extractor(mocker, _make_bean(image_url="https://cdn.example.com/from-ai.jpg"))

    bean = await scraper._extract_bean_with_ai(ai_extractor, BeautifulSoup("<html><body></body></html>", "lxml"), url)

    assert str(bean.image_url) == "https://cdn.example.com/from-ai.jpg"


# ---------------------------------------------------------------------------
# B2: recording at fetch time + start_session clearing
# ---------------------------------------------------------------------------


async def test_fetch_page_with_screenshot_records_image_url(mocker):
    scraper = _MinimalScraper()

    def response_for_url(url, **kwargs):
        return _StubResponse(
            200,
            text='<html><head><meta property="og:image" content="https://cdn.example.com/og.jpg"></head>'
            "<body></body></html>",
        )

    _install_client_stub(scraper, response_for_url)
    mocker.patch.object(scraper, "take_screenshot", new=mocker.AsyncMock(return_value=None))
    mocker.patch.object(scraper, "_save_page_cache", new=mocker.AsyncMock(return_value=None))

    url = "https://test-roaster.example/product/1"
    soup, _ = await scraper.fetch_page_with_screenshot(url)

    assert soup is not None
    assert scraper._page_image_urls[url] == "https://cdn.example.com/og.jpg"


async def test_start_session_clears_recorded_image_urls(mocker):
    scraper = _MinimalScraper()
    scraper._page_image_urls["https://example.com/x"] = "https://cdn.example.com/x.jpg"

    scraper.start_session()

    assert scraper._page_image_urls == {}


async def test_fetch_page_with_screenshot_missing_image_not_recorded(mocker):
    scraper = _MinimalScraper()

    def response_for_url(url, **kwargs):
        return _StubResponse(200, text="<html><body>no image</body></html>")

    _install_client_stub(scraper, response_for_url)
    mocker.patch.object(scraper, "take_screenshot", new=mocker.AsyncMock(return_value=None))
    mocker.patch.object(scraper, "_save_page_cache", new=mocker.AsyncMock(return_value=None))

    await scraper.fetch_page_with_screenshot("https://test-roaster.example/product/2")

    assert scraper._page_image_urls == {}


# ---------------------------------------------------------------------------
# B4: the origin-less guard in _extract_bean_with_ai
# ---------------------------------------------------------------------------


def _originless_bean(**kwargs) -> CoffeeBean:
    """A bean the extractor produced from a page that states no origin."""
    fields = {
        "name": "Test Espresso Blend",
        "roaster": "Test Roaster",
        "url": "https://test-roaster.example/product/blend",
        "origins": [],
        "price_options": [{"weight": 250, "price": 15.0}],
        "price": 15.0,
        "weight": 250,
    }
    fields.update(kwargs)
    return CoffeeBean(**fields)


def _blank_origin_bean(**kwargs) -> CoffeeBean:
    """The other shape: ``origins`` holds one ``Bean`` with nothing set."""
    return _originless_bean(origins=[{}], **kwargs)


async def test_empty_origins_with_price_is_kept(mocker):
    # A blend, a decaf blend or a giveaway states no single origin, and the
    # extractor answers with an empty list. A recovered price proves the page is
    # a real product page, so the bean is kept.
    scraper = _MinimalScraper()
    scraper._currency_detected = True
    ai_extractor = _stub_ai_extractor(mocker, _originless_bean())

    bean = await scraper._extract_bean_with_ai(
        ai_extractor, BeautifulSoup("<html><body></body></html>", "lxml"), "https://test-roaster.example/product/blend"
    )

    assert bean is not None
    assert bean.origins == []
    assert bean.name == "Test Espresso Blend"


async def test_blank_origin_bean_with_price_is_kept(mocker):
    # ``origins=[Bean()]`` is the other way the extractor reports "no origin".
    scraper = _MinimalScraper()
    scraper._currency_detected = True
    ai_extractor = _stub_ai_extractor(mocker, _blank_origin_bean())

    bean = await scraper._extract_bean_with_ai(
        ai_extractor, BeautifulSoup("<html><body></body></html>", "lxml"), "https://test-roaster.example/product/blend"
    )

    assert bean is not None
    assert len(bean.origins) == 1


async def test_price_option_alone_counts_as_a_recovered_price(mocker):
    # The extractor sometimes returns price_options but leaves the top-level
    # price/weight unset.
    scraper = _MinimalScraper()
    scraper._currency_detected = True
    bean = _originless_bean(price=None, weight=250, price_options=[{"weight": 250, "price": 15.0}])
    ai_extractor = _stub_ai_extractor(mocker, bean)

    out = await scraper._extract_bean_with_ai(
        ai_extractor, BeautifulSoup("<html><body></body></html>", "lxml"), "https://test-roaster.example/product/blend"
    )

    assert out is not None


async def test_empty_origins_without_any_price_is_still_dropped(mocker):
    # The case the guard exists for: the extractor recovered neither an origin
    # nor a price, so the page is not really a coffee product.
    scraper = _MinimalScraper()
    scraper._currency_detected = True
    ai_extractor = _stub_ai_extractor(mocker, _originless_bean(price_options=[], price=None, weight=None))

    bean = await scraper._extract_bean_with_ai(
        ai_extractor, BeautifulSoup("<html><body></body></html>", "lxml"), "https://test-roaster.example/product/junk"
    )

    assert bean is None


async def test_blank_origin_bean_without_any_price_is_still_dropped(mocker):
    scraper = _MinimalScraper()
    scraper._currency_detected = True
    ai_extractor = _stub_ai_extractor(mocker, _blank_origin_bean(price_options=[], price=None, weight=None))

    bean = await scraper._extract_bean_with_ai(
        ai_extractor, BeautifulSoup("<html><body></body></html>", "lxml"), "https://test-roaster.example/product/junk"
    )

    assert bean is None


async def test_tasting_kit_without_price_is_still_kept(mocker):
    # Pre-existing exemption: a curated sampler has no origin and often no
    # usable price either, and is flagged is_tasting_kit/requires_review.
    scraper = _MinimalScraper()
    scraper._currency_detected = True
    bean = _originless_bean(
        name="Taster Box",
        price_options=[],
        price=None,
        weight=None,
        url="https://test-roaster.example/product/taster-box",
    )
    ai_extractor = _stub_ai_extractor(mocker, bean)

    out = await scraper._extract_bean_with_ai(
        ai_extractor, BeautifulSoup("<html><body></body></html>", "lxml"), bean.url
    )

    assert out is not None


def test_has_usable_origin_predicate():
    assert BaseScraper._has_usable_origin(_originless_bean(origins=[{"country": "CO"}])) is True
    assert BaseScraper._has_usable_origin(_originless_bean(origins=[{"process": "Washed"}])) is True
    assert BaseScraper._has_usable_origin(_originless_bean(origins=[{"variety": "Bourbon"}])) is True
    assert BaseScraper._has_usable_origin(_originless_bean(origins=[{}])) is False
    assert BaseScraper._has_usable_origin(_originless_bean(origins=[])) is False


def test_has_recovered_price_predicate():
    assert BaseScraper._has_recovered_price(_originless_bean()) is True
    assert BaseScraper._has_recovered_price(_originless_bean(price=None, weight=None, price_options=[])) is False


# ---------------------------------------------------------------------------
# Characterization of what the origin-less guard admits
#
# The guard is: a product page that yields neither an origin nor a price is not
# worth recording. Origin-less products are legitimate on their own terms —
# a blend states no single origin, a curated kit states none at all — so a
# recovered price is the independent evidence that the page really is a
# sellable product rather than a nav page, an equipment listing or an error
# page rendered as HTML.
#
# Deliberately NOT part of this rule: origin-less products are *not* flagged
# ``requires_review``. Every house/espresso/seasonal blend on every storefront
# is origin-less by definition, so review-flagging them would put essentially
# the whole catalogue in the admin queue and make that queue unusable. The
# review gate is reserved for the genuinely ambiguous case — a curated
# multi-coffee kit — which is what ``is_tasting_kit``/``requires_review`` mean.
# ---------------------------------------------------------------------------


async def _extract(scraper, mocker, bean, url=None):
    """Run one bean through the real extraction path, then the flagging step.

    ``_apply_product_flags`` is invoked explicitly because it lives in the
    caller (``scrape_with_ai_extraction``), not in ``_extract_bean_with_ai``;
    calling it here keeps these tests on the real ordering without standing up
    a whole scrape session.
    """
    url = url or str(bean.url)
    out = await scraper._extract_bean_with_ai(
        _stub_ai_extractor(mocker, bean), BeautifulSoup("<html><body></body></html>", "lxml"), url
    )
    scraper._apply_product_flags(out, url, is_new=True)
    return out


def _scraper() -> "_MinimalScraper":
    scraper = _MinimalScraper()
    # Pin the currency so the test never depends on the product page HTML.
    scraper._currency_detected = True
    return scraper


async def test_priced_origin_less_blend_is_admitted_and_is_not_review_flagged(mocker):
    # The admission itself: a priced product page with no origin survives, and
    # stays visible in public search (see the note above on why it is not sent
    # to the review queue).
    out = await _extract(_scraper(), mocker, _originless_bean())

    assert out is not None
    assert out.origins == []
    assert out.is_tasting_kit is False
    assert out.requires_review is False


async def test_priced_origin_less_equipment_name_is_still_rejected(mocker):
    # A recovered price says "this page sells something", not "this page sells
    # coffee", so the name blocklist has to keep doing the second half of the
    # job for this shape. The pipeline drops the bean when the name is not a
    # coffee name.
    #
    # Note the residual gap: the base blocklist is a fixed English token list
    # (``grinder``, ``dripper``, ``tumbler``, ...) and does not cover every
    # piece of drinkware — "mug" and "cup" are absent, so a priced origin-less
    # product named e.g. "Ceramic Mug" would pass. Roasters whose catalogues
    # carry that shape filter it themselves (see ``acid_coffee.py``, which
    # rejects the whole ``Goods`` breadcrumb category because the base list is
    # English-only). Widening the base list is a separate change from this one.
    scraper = _scraper()
    out = await _extract(
        scraper,
        mocker,
        _originless_bean(name="Comandante C40 Hand Grinder", url="https://test-roaster.example/product/c40"),
    )

    assert out is not None, "the guard must not confuse 'priced' with 'coffee'"
    assert out.name == "Comandante C40 Hand Grinder"
    assert scraper.is_coffee_product_name(out.name) is False


async def test_kit_url_without_origin_or_price_is_kept_and_flagged(mocker):
    # KIT_REVIEW invariant: a curated sampler states no origin and frequently
    # carries no extractable price either, so the kit-URL exemption admits it
    # and the review gate is what keeps it out of public search until an admin
    # approves it.
    bean = _originless_bean(
        name="Around The World Coffee Sampler Gift Box",
        price_options=[],
        price=None,
        weight=None,
        url="https://test-roaster.example/product/sampler",
    )

    out = await _extract(_scraper(), mocker, bean)

    assert out is not None
    assert out.is_tasting_kit is True
    assert out.requires_review is True


async def test_blank_origin_bean_with_kit_url_is_kept_and_flagged(mocker):
    # GAP 4: the exemption is expressed in terms of "no usable origin", not
    # "empty origins list", so both origin-less shapes it reports qualify —
    # an empty list and a list holding one blank ``Bean``. Both are exempted by
    # the same rule, and both end up behind the same review gate.
    bean = _blank_origin_bean(
        name="Seasonal Sampler",
        price_options=[],
        price=None,
        weight=None,
        url="https://test-roaster.example/product/seasonal-sampler",
    )

    out = await _extract(_scraper(), mocker, bean)

    assert out is not None
    assert len(out.origins) == 1
    assert out.is_tasting_kit is True
    assert out.requires_review is True


async def test_priced_origin_less_non_kit_page_with_a_kit_named_url_is_flagged_by_name(mocker):
    # The two detectors are independent and both feed the review gate: a
    # sampler named on a non-kit URL is still caught by the name check, which
    # keeps kits whose handles carry no kit token out of public search.
    out = await _extract(
        _scraper(),
        mocker,
        _originless_bean(name="Discovery Sampler", url="https://test-roaster.example/products/discovery"),
    )

    assert out is not None
    assert out.is_tasting_kit is True
    assert out.requires_review is True


# ---------------------------------------------------------------------------
# Persistence: the validator-derived price has to reach the artifact refresh reads
# ---------------------------------------------------------------------------


async def test_validator_filled_price_reaches_the_saved_json(tmp_path, mocker):
    # ``_extract_bean_with_ai`` returns a bean whose top-level price was filled
    # by ``set_default_price_option``; ``save_bean_to_file`` serialises that
    # same object. If the fill happened anywhere other than on the model, the
    # on-disk artifact would carry ``price: null`` and the row would land in
    # the DB with no price at all.
    scraper = _scraper()
    bean = _originless_bean(
        price=None,
        weight=250,
        price_options=[{"weight": 100, "price": 8.0}, {"weight": 250, "price": 15.0}],
    )
    out = await _extract(scraper, mocker, bean)

    assert out.price == 15.0

    path = scraper.save_bean_to_file(out, tmp_path)
    saved = json.loads(path.read_text())

    assert saved["price"] == 15.0
    assert saved["weight"] == 250


async def test_validator_skipped_fill_reaches_the_saved_json_as_null(tmp_path, mocker):
    # The other half of the invariant: when no option matches the reported
    # weight nothing is invented, and the artifact says so plainly.
    scraper = _scraper()
    bean = _originless_bean(
        price=None,
        weight=250,
        price_options=[{"weight": 100, "price": 8.0}, {"weight": 500, "price": 30.0}],
    )
    out = await _extract(scraper, mocker, bean)

    assert out.price is None

    path = scraper.save_bean_to_file(out, tmp_path)
    saved = json.loads(path.read_text())

    assert saved["price"] is None
    assert saved["weight"] == 250
