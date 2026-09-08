"""Unit tests for the BeBerry Coffee scraper.

The primary extraction test runs against a **captured fixture** of the live
``/categories/kava/`` page (12 ``li.product`` cards on capture — the same
markup the scraper reads: card classes + ``/product/`` anchors), so catalogue
drift — a moved product, a renamed slug, a new category member, a class
rename — fails the test and is visible as a fixture diff. Regenerate with
``.venv/bin/python tests/fixtures/capture.py`` (see the fixture module
docstring).

Two things the live capture cannot exercise, so they stay synthetic:
- The ``outofstock`` branch: on capture every card was ``instock``. The test
  keeps a hand-built card to guard the sold-out filter, including the trap
  that made class detection mandatory — every in-stock variable card also
  renders a disabled "Dočasně vyprodáno" add-to-cart button, so substring
  detection would false-positive the whole catalogue.
- The currency pin: no WooCommerce currency meta exists, so the bean must be
  forced to CZK.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.beberry_coffee import BeBerryCoffeeScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "beberry_kava_category.html"
KAVA_URL = "https://www.beberrycoffee.cz/categories/kava/"


def _make_scraper() -> BeBerryCoffeeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return BeBerryCoffeeScraper(api_key="test-api-key")


async def _extract_from_soup(soup: BeautifulSoup) -> list[str]:
    scraper = _make_scraper()

    async def fake_fetch_page(url, *args, **kwargs):
        return soup

    scraper.fetch_page = fake_fetch_page
    return await scraper._extract_product_urls_from_store(KAVA_URL)


async def test_captured_category_extracts_in_stock_beans():
    soup = BeautifulSoup(FIXTURE.read_text(), "lxml")

    urls = await _extract_from_soup(soup)

    # 12 captured cards → 10 whole-bean coffees (the two teas are excluded).
    assert len(urls) == 10
    assert all(url.startswith("https://www.beberrycoffee.cz/product/") and url.endswith("/") for url in urls)

    slugs = {url.rsplit("/", 2)[-2] for url in urls}
    # Every bean present in the live capture…
    expected = {
        "burundi-kibingo",
        "colombia-alirio-rodriguez",
        "colombia-rigoberto-herrera",
        "decaff-colombia",
        "ethiopia-chelbesa-2",
        "ethiopia-ephrem-mulugeta",
        "kenya-david-muge",
        "kenya-great-rift",
        "kenya-peponi",
        "uganda-norman-mukuru",
    }
    assert slugs == expected
    # …and the coffee-cherry/blossom teas are never treated as beans.
    assert "cascara-coffee-cherry-tea" not in slugs
    assert "kavovy-kvet" not in slugs


async def test_outofstock_card_excluded_via_class_not_text():
    # A real in-stock variable card carries a disabled "Dočasně vyprodáno"
    # (temporarily sold out) add-to-cart button even while in stock, so text
    # detection must not decide; the WooCommerce status class decides.
    def card(css_class: str, slug: str) -> str:
        return (
            f'<li class="product {css_class}">'
            f'<a href="https://www.beberrycoffee.cz/product/{slug}/">{slug}</a>'
            '<button class="button add_to_cart_button disabled" disabled="">'
            "Dočasně vyprodáno</button>"
            "</li>"
        )

    soup = BeautifulSoup(
        "<html><body><ul class='products'>"
        + card("type-product instock", "burundi-kibingo")
        + card("type-product outofstock", "kenya-great-rift")
        + "</ul></body></html>",
        "lxml",
    )

    urls = await _extract_from_soup(soup)

    # The outofstock card is dropped; the in-stock card survives despite the
    # vyprodáno text on both cards.
    assert urls == ["https://www.beberrycoffee.cz/product/burundi-kibingo/"]


async def test_extract_uses_store_url_fetch_only():
    soup = BeautifulSoup(FIXTURE.read_text(), "lxml")
    scraper = _make_scraper()
    calls = []

    async def fake_fetch_page(url, *args, **kwargs):
        calls.append(url)
        return soup

    scraper.fetch_page = fake_fetch_page

    await scraper._extract_product_urls_from_store(KAVA_URL)

    # Extraction must not fan out to product pages: exactly one fetch, of the
    # category listing itself.
    assert calls == [KAVA_URL]


def test_postprocess_extracted_bean_pins_czk_currency():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="BURUNDI Kibingo",
        roaster="BeBerry Coffee",
        url="https://www.beberrycoffee.cz/product/burundi-kibingo/",
        origins=[{"country": "BDI"}],
        price_options=[{"weight": 250, "price": 349.0}],
        price=349.0,
        weight=250,
        currency="EUR",  # base detection never fires on WooCommerce; must be pinned
    )

    result = scraper.postprocess_extracted_bean(bean)

    assert result is bean
    assert bean.currency == "CZK"
