"""Unit tests for the Acid Coffee scraper (STORES.jp) — fully mocked, no network.

Fixtures are trimmed captures of the live site:

* ``acid_coffee_sitemap.xml`` — a 14-URL excerpt of the real ``/sitemap.xml``
  ``<urlset>``: 8 coffee items, the 4 ``Goods`` (non-coffee) items and 3 drip-bag
  items (``ACID Drip Bag``, the Advent Calendar sampler and the empty
  filter-paper set).
* ``acid_coffee_item.jsonld.json`` — verbatim JSON-LD from a real item page
  (Kenya Ngacha Estate): ``[Product, BreadcrumbList]``.
* ``acid_coffee_item_page.html`` — the JSON-LD plus the real ``p.item_price``
  range and ``div.variation`` blocks from that same page.

The ``Goods``-category and capsule-assortment products are derived from the real
fixtures by rewriting the JSON-LD ``name`` / ``description`` /
``BreadcrumbList``, which is how the live pages differ (their real breadcrumb
paths were verified: ``HOME > Others > Goods > ACIDCOFFEE Original Dripper``).
"""

import copy
import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.acid_coffee import SITEMAP_URL, AcidCoffeeScraper
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
ITEM_URL = "https://acidcoffee.stores.jp/items/6ab7caf4b21f830e5fc42c9a"
ITEM_HEX = "6ab7caf4b21f830e5fc42c9a"


def _make_scraper() -> AcidCoffeeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return AcidCoffeeScraper(api_key="test-api-key")


def _fixture_jsonld() -> list:
    return json.loads((FIXTURES / "acid_coffee_item.jsonld.json").read_text())


def _fixture_item_page_html() -> str:
    return (FIXTURES / "acid_coffee_item_page.html").read_text()


def _rewrite_jsonld(jsonld, *, name=None, crumbs=None, description=None):
    """Return a copy of the JSON-LD with product name / breadcrumb / description replaced."""
    data = copy.deepcopy(jsonld)
    for node in data:
        if node.get("@type") == "Product":
            if name:
                node["name"] = name
            if description:
                node["description"] = description
        elif node.get("@type") == "BreadcrumbList" and crumbs is not None:
            elements = node["itemListElement"]
            elements[1]["name"] = crumbs[0]
            elements[2]["name"] = crumbs[1]
            elements[3]["name"] = name or elements[3]["name"]
    return data


def _item_page_soup(jsonld=None, *, variation_html=None) -> BeautifulSoup:
    """Build an item page soup from the fixture, optionally swapping the JSON-LD/variations."""
    html = _fixture_item_page_html()
    data = _fixture_jsonld() if jsonld is None else jsonld
    script_start = html.index('<script type="application/ld+json">') + len('<script type="application/ld+json">')
    script_end = html.index("</script>", script_start)
    html = html[:script_start] + json.dumps(data, ensure_ascii=False) + html[script_end:]
    if variation_html is not None:
        first = html.index('<div class="variation"')
        last = html.rindex("</div>", 0, html.index("</div>\n</div>\n</body>")) + len("</div>")
        html = html[:first] + variation_html + html[last:]
    return BeautifulSoup(html, "lxml")


@pytest.fixture
def scraper() -> AcidCoffeeScraper:
    return _make_scraper()


class _FailingFetch:
    """``fetch_page`` stand-in that always raises, like a Cloudflare 403 mid-run."""

    async def __call__(self, *args, **kwargs):
        raise AssertionError("fetch_page must not be reached")


def _patch_fetch(monkeypatch, scraper, soup):
    async def fake_fetch(*args, **kwargs):
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)


def _goods_soup() -> BeautifulSoup:
    """Item page for the real 'Goods' product ACIDCOFFEE Original Dripper.

    The live breadcrumb for that page is ``HOME > Others > Goods >
    ACIDCOFFEE Original Dripper`` (verified 2026-10-04).
    """
    jsonld = _rewrite_jsonld(
        _fixture_jsonld(),
        name="ACIDCOFFEE Original Dripper",
        crumbs=["Others", "Goods"],
        description="ACIDCOFFEE Original Dripper — a coffee dripper, not coffee.",
    )
    return _item_page_soup(jsonld)


def _make_bean(**kwargs) -> CoffeeBean:
    kwargs.setdefault("roaster", "Acid Coffee")
    kwargs.setdefault("url", ITEM_URL)
    kwargs.setdefault("origins", [])
    kwargs.setdefault("price_options", [])
    return CoffeeBean(**kwargs)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_entry():
    info = get_registry().get_scraper_info("acid-coffee")
    assert info is not None
    assert info.roaster_name == "Acid Coffee"
    assert info.currency == "JPY"
    assert info.country == "Japan"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == get_registry().get_scraper_info("acid-coffee").roaster_name


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


def test_client_is_built_with_impersonate(scraper):
    """Cloudflare 403s libcurl's default TLS fingerprint; without impersonate the scrape is empty."""
    assert scraper.client._impersonate == "chrome"


def test_client_does_not_send_web_bot_auth_headers(scraper):
    """Cloudflare 403s the Web Bot Auth signature headers on this host (verified live)."""
    assert scraper.client._auth is None


def test_rate_limit_delay_matches_robots_crawl_delay(scraper):
    # robots.txt: Crawl-delay: 20
    assert scraper.rate_limit_delay >= 20.0


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


async def test_store_urls_returns_sitemap(scraper):
    assert await scraper.get_store_urls() == [SITEMAP_URL]


async def test_discovers_item_urls_from_sitemap(monkeypatch, scraper):
    soup = BeautifulSoup((FIXTURES / "acid_coffee_sitemap.xml").read_text(), "xml")
    _patch_fetch(monkeypatch, scraper, soup)

    urls = await scraper._extract_product_urls_from_store(SITEMAP_URL)

    assert urls, "sitemap discovery must find product URLs"
    assert ITEM_URL in urls
    # 15 sitemap entries: 14 /items/<hex> products plus the homepage.
    assert len(urls) == 14
    for url in urls:
        assert "/items/" in url
        assert "/categories/" not in url
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        assert len(slug) == 24 and all(c in "0123456789abcdef" for c in slug)
    # The homepage <loc> is not a product.
    assert "https://acidcoffee.stores.jp/" not in urls
    # Discovery is deduplicated and order-preserving.
    assert len(set(urls)) == len(urls)


async def test_sitemap_index_is_followed(monkeypatch, scraper):
    index = BeautifulSoup(
        "<sitemapindex><sitemap><loc>https://acidcoffee.stores.jp/sitemap_0.xml</loc></sitemap></sitemapindex>",
        "xml",
    )
    child = BeautifulSoup((FIXTURES / "acid_coffee_sitemap.xml").read_text(), "xml")
    requested: list[str] = []

    async def fake_fetch(url, *args, **kwargs):
        requested.append(url)
        return index if url == SITEMAP_URL else child

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)

    urls = await scraper._extract_product_urls_from_store(SITEMAP_URL)

    assert "https://acidcoffee.stores.jp/sitemap_0.xml" in requested
    assert ITEM_URL in urls
    assert len(urls) == 14


async def test_failed_sitemap_returns_empty(monkeypatch, scraper):
    monkeypatch.setattr(scraper, "fetch_page", _FailingFetch())
    assert await scraper._extract_product_urls_from_store(SITEMAP_URL) == []


async def test_empty_sitemap_response_returns_empty(monkeypatch, scraper):
    _patch_fetch(monkeypatch, scraper, None)
    assert await scraper._extract_product_urls_from_store(SITEMAP_URL) == []


async def test_failed_child_sitemap_returns_empty(monkeypatch, scraper):
    index = BeautifulSoup(
        "<sitemapindex><sitemap><loc>https://acidcoffee.stores.jp/sitemap_0.xml</loc></sitemap></sitemapindex>",
        "xml",
    )

    async def fake_fetch(url, *args, **kwargs):
        return index

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    assert await scraper._extract_product_urls_from_store(SITEMAP_URL) == []


# ---------------------------------------------------------------------------
# JSON-LD parsing
# ---------------------------------------------------------------------------


def test_parses_product_node_and_breadcrumb_path(scraper):
    product, crumbs = scraper._parse_item_page(_item_page_soup())
    assert product is not None
    assert product["name"].startswith("Kenya Ngacha Estate")
    assert product["offers"]["priceCurrency"] == "JPY"
    assert product["offers"]["@type"] == "AggregateOffer"
    # HOME and the product name are stripped; only the category path remains.
    assert crumbs == ["Confidence!!! 〜めっちゃ良いやつ〜", "Washed"]


def test_goods_breadcrumb_is_recognised(scraper):
    product, crumbs = scraper._parse_item_page(_goods_soup())
    assert product["name"] == "ACIDCOFFEE Original Dripper"
    assert crumbs == ["Others", "Goods"]
    assert scraper._is_non_coffee(product["name"], crumbs) is True


@pytest.mark.parametrize(
    "name",
    [
        "【xBloom】ACIDレシピインストール済み",
        "ACID COFFEE BB CAP",
        "ACIDCOFFEE スーパーフルーティ両手マグ",
        "ACID COFFEE PHOTO Tシャツ ver.1",
        "【ACID HEADS】コーヒーサブスクリプション",
        "【ほぼ業務用】Drip Bag 10 個セット【お徳用】",
    ],
)
def test_non_coffee_names_are_excluded(scraper, name):
    assert scraper._is_non_coffee(name, ["Innovative!! 〜ちょっと良いやつ〜", "Washed"]) is True


@pytest.mark.parametrize(
    "name",
    [
        "Kenya Ngacha Estate Auction Lot, SL28,SL34 - Anaerobic Washed",
        "カプセルコーヒー10個アソート",
        "2025Advent Calendar【Drip Bag】",
        "ACID Drip Bag",
        "ETHIOPIA SIDAMO(99.9DECAF) 100g",
    ],
)
def test_coffee_names_are_not_excluded(scraper, name):
    assert scraper._is_non_coffee(name, ["Daily! 〜初めての方も〜", "Washed"]) is False


# ---------------------------------------------------------------------------
# Compact soup
# ---------------------------------------------------------------------------


def test_variant_prices_and_sizes_are_extracted(scraper):
    soup = _item_page_soup()

    variations = scraper._parse_variations(soup)

    sizes = [v["size"] for v in variations]
    assert sizes == ["16g", "32g", "100g", "300g", "500g"]

    by_size = {v["size"]: v for v in variations}
    assert by_size["300g"]["price"] == "¥21,000"
    assert by_size["300g"]["stock"] == "残り3点"
    assert by_size["500g"]["price"] == "¥34,000"
    assert by_size["500g"]["stock"] == "残り2点"
    # An in-stock variant renders no stock_item label.
    assert by_size["16g"]["price"] == "¥1,500"
    assert by_size["16g"]["stock"] == ""

    product, crumbs = scraper._parse_item_page(soup)
    compact = str(scraper._build_item_soup(soup, product, crumbs))
    assert "300g" in compact
    assert "21,000" in compact
    assert "残り3点" in compact
    assert "Price range (tax included): JPY 1500 - 34000" in compact
    assert "In stock" in compact
    # Images are preserved as og:image so the base JSON-LD/og image backfill works.
    assert 'property="og:image"' in compact
    assert "imagedelivery.net" in compact
    # The raw server-rendered page is far larger than the compact soup.
    assert len(compact) < len(str(soup))


def _meta_currency(compact_html: str) -> str | None:
    """Return the ``og:price:currency`` content of a compact soup (None when absent)."""
    meta = BeautifulSoup(compact_html, "html.parser").find("meta", property="og:price:currency")
    return meta.get("content") if meta else None


def test_currency_is_stated_as_machine_readable_data(scraper):
    """The soup must name the currency explicitly, not leave the model to guess it.

    ``CoffeeBean.currency`` defaults to ``GBP``, so an unset field made the model
    validate ¥1,500/16 g as £1,500/16 g and ``check_prices`` dropped the bean.
    """
    soup = _item_page_soup()
    product, crumbs = scraper._parse_item_page(soup)

    compact = str(scraper._build_item_soup(soup, product, crumbs))

    assert "<p>Currency: JPY</p>" in compact
    assert _meta_currency(compact) == "JPY"


def test_variant_lines_carry_the_currency_code(scraper):
    """Per-variant prices are rendered as a bare "¥1,500" glyph; relabel them."""
    soup = _item_page_soup()
    product, crumbs = scraper._parse_item_page(soup)

    compact = str(scraper._build_item_soup(soup, product, crumbs))

    assert "Variants (size / price in JPY / stock):" in compact
    assert "- 16g / JPY 1,500 / in stock" in compact
    assert "- 32g / JPY 2,500 / in stock" in compact
    assert "- 300g / JPY 21,000 / 残り3点" in compact
    # The bare glyph is gone from the per-variant lines, so the model cannot
    # map a symbol onto the wrong currency field.
    variant_block = compact.split("Variants (")[1].split("</pre>")[0]
    assert "¥" not in variant_block


def test_price_currency_meta_is_present_without_an_image(scraper):
    """Currency is stated independently of the image, so a product with no
    image still carries an explicit ``og:price:currency``."""
    soup = _item_page_soup()
    product, crumbs = scraper._parse_item_page(soup)
    assert product["image"], "fixture must start with an image"

    product["image"] = []
    compact = str(scraper._build_item_soup(soup, product, crumbs))

    assert "<p>Currency: JPY</p>" in compact
    assert _meta_currency(compact) == "JPY"
    assert 'property="og:image"' not in compact


def test_out_of_stock_availability_is_labelled(scraper):
    soup = _item_page_soup(_rewrite_jsonld(_fixture_jsonld(), description="【acho】"))
    product, crumbs = scraper._parse_item_page(soup)
    product["offers"]["availability"] = "https://schema.org/OutOfStock"
    compact = str(scraper._build_item_soup(soup, product, crumbs))
    assert "Out of stock" in compact


def test_missing_jsonld_product_returns_none(scraper):
    assert scraper._parse_item_page(BeautifulSoup("<html><body>no ld+json</body></html>", "lxml")) == (None, [])


# ---------------------------------------------------------------------------
# _extract_bean_with_ai hook (None-safety is exercised through the base pipeline)
# ---------------------------------------------------------------------------


async def test_goods_category_products_are_excluded(scraper):
    bean = await scraper._extract_bean_with_ai(
        scraper.ai_extractor,
        _goods_soup(),
        "https://acidcoffee.stores.jp/items/6672b01ae080d90038805ab2",
    )

    assert bean is None


async def test_non_coffee_name_is_excluded_before_ai_call(scraper):
    soup = _item_page_soup(_rewrite_jsonld(_fixture_jsonld(), name="【ACID HEADS】コーヒーサブスクリプション"))

    assert await scraper._extract_bean_with_ai(scraper.ai_extractor, soup, ITEM_URL) is None


async def test_page_without_jsonld_is_excluded(scraper):
    soup = BeautifulSoup("<html><body>nothing here</body></html>", "lxml")
    assert await scraper._extract_bean_with_ai(scraper.ai_extractor, soup, ITEM_URL) is None


async def test_base_pipeline_accepts_none_from_the_hook(monkeypatch, scraper):
    """``scrape_with_ai_extraction`` must survive a None return from the hook (Goods product)."""
    _patch_fetch(monkeypatch, scraper, _goods_soup())
    scraper.start_session()

    beans = await scraper._scrape_new_products([ITEM_URL])

    assert beans == []


async def test_coffee_product_reaches_the_ai_extractor(monkeypatch, scraper):
    """A real coffee page must be forwarded to the AI extractor as the compact soup."""
    soup = _item_page_soup()
    _patch_fetch(monkeypatch, scraper, soup)
    seen: dict = {}

    async def fake_extract(self, ai_extractor, compact_soup, product_url, **kwargs):
        seen["html"] = str(compact_soup)
        seen["url"] = product_url
        return _make_bean(name="Kenya Ngacha Estate", url=product_url, price=7500, currency="JPY", in_stock=True)

    # Patch the base so AcidCoffeeScraper's override still runs (and narrows).
    monkeypatch.setattr(BaseScraper, "_extract_bean_with_ai", fake_extract)

    bean = await scraper._extract_bean_with_ai(scraper.ai_extractor, soup, ITEM_URL, translate_to_english=True)

    assert bean is not None
    assert seen["url"] == ITEM_URL
    assert "300g" in seen["html"]
    assert "JPY 21,000" in seen["html"]
    # Compact soup, not the raw server-rendered page.
    assert "ng-app" not in seen["html"]
    assert len(seen["html"]) < len(str(soup))


# ---------------------------------------------------------------------------
# Screenshots (Cloudflare 403s Playwright on this host)
# ---------------------------------------------------------------------------


async def test_take_screenshot_is_a_no_op(scraper):
    """Playwright is 403'd by Cloudflare here, so no screenshot is attempted."""
    assert await scraper.take_screenshot(ITEM_URL) is None
    assert await scraper.take_screenshot(ITEM_URL, full_page=True) is None


async def test_take_screenshot_does_not_touch_playwright(monkeypatch, scraper):
    """No browser may be launched: that navigation is exactly the wasted request."""

    async def boom(*args, **kwargs):
        raise AssertionError("take_screenshot must not launch a browser")

    monkeypatch.setattr(BaseScraper, "_get_browser", boom)

    assert await scraper.take_screenshot(ITEM_URL, full_page=True) is None


# ---------------------------------------------------------------------------
# Review-flag / currency hooks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "カプセルコーヒー10個アソート",
        "2025Advent Calendar【Drip Bag】",
        "ACID Drip Bag 試飲セット",
        "PANAMA STARTER PACK 16g × 4種類",
    ],
)
def test_tasting_kit_names_are_flagged(scraper, name):
    bean = _make_bean(name=name)
    assert scraper.postprocess_review_flags(bean, ITEM_URL).is_tasting_kit is True


def test_plain_coffee_is_not_flagged_as_a_kit(scraper):
    bean = _make_bean(name="Kenya Ngacha Estate, SL28 - Anaerobic Washed")
    assert scraper.postprocess_review_flags(bean, ITEM_URL).is_tasting_kit is False


def test_tasting_kits_are_flagged_not_excluded(scraper):
    """The capsule assortment is coffee: kept by the name filter, flagged for review."""
    name = "カプセルコーヒー10個アソート"
    assert scraper._is_non_coffee(name, ["Innovative!! 〜ちょっと良いやつ〜", "その他特殊プロセス"]) is False

    bean = _make_bean(name=name)
    scraper._apply_product_flags(bean, ITEM_URL, is_new=True)

    assert bean.is_tasting_kit is True
    assert bean.requires_review is True


def test_currency_pinned_in_postprocess(scraper):
    bean = _make_bean(name="Kenya Ngacha Estate", currency="GBP")
    result = scraper.postprocess_extracted_bean(bean)
    assert result is not None
    assert result.currency == "JPY"
