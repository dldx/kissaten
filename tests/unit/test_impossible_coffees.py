"""Unit tests for the Impossible Coffees scraper (fixture-based, no network).

Impossible Coffees (impossiblecoffees.com) is a WordPress.com/Jetpack showcase
with one storytelling page per coffee and **no published prices** — the COMPRAR
buttons link out to the external shop at shop.deltacoffeehouse.com. The
fixtures are trimmed copies of the real ``<main id="main">`` markup of the
"Os Cafés" listing page and the Café Amboim product page (images/scripts
stripped), so a new coffee page, a renamed slug or a listing redesign fails
the test as a fixture diff. Regenerate by re-curling the pages and trimming
``main#main``.

Covered per-scraper behaviour:
- The ``/cafe-`` path gate (all five showcase pages kept; project pages,
  legal pages and external links never leak in).
- ``fetch_page`` narrowing of product pages to ``main#main`` (token lever).
- Currency pinned to EUR and extracted prices stripped: the only € figures on
  the pages are fundraising counters (e.g. "Valor angariado ... 23078.84 €"),
  never product prices.
- ``translate_to_english=True`` for the Portuguese storytelling pages.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.impossible_coffees import ImpossibleCoffeesScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

LISTING_URL = "https://impossiblecoffees.com/os-cafes/"
AMBOIM_URL = "https://impossiblecoffees.com/cafe-amboim/"

EXPECTED_PRODUCT_URLS = [
    "https://impossiblecoffees.com/cafe-amboim/",
    "https://impossiblecoffees.com/cafe-catoninho/",
    "https://impossiblecoffees.com/cafe-colombia/",
    "https://impossiblecoffees.com/cafe-dos-acores/",
    "https://impossiblecoffees.com/cafe-toki/",
]


def _make_scraper() -> ImpossibleCoffeesScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return ImpossibleCoffeesScraper(api_key="test-api-key")


def _listing_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "impossible-coffees_os-cafes.html").read_text(), "lxml")


def _amboim_soup() -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / "impossible-coffees_cafe-amboim.html").read_text(), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("impossible-coffees")
    assert info is not None
    assert info.roaster_name == "Impossible Coffees"
    assert info.currency == "EUR"
    assert info.country == "Portugal"
    assert info.requires_api_key is True
    assert info.website == "https://impossiblecoffees.com"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Impossible Coffees"
    assert scraper.base_url == "https://impossiblecoffees.com"


async def test_store_urls_point_at_os_cafes_listing():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [LISTING_URL]


async def test_extracts_all_five_coffee_pages(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    # All five showcase pages, in the order the live listing links them.
    assert len(urls) == 5
    assert sorted(urls) == sorted(EXPECTED_PRODUCT_URLS)
    assert "https://impossiblecoffees.com/cafe-amboim/" in urls
    assert "https://impossiblecoffees.com/cafe-toki/" in urls


async def test_project_legal_and_external_pages_do_not_leak(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _listing_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    # The real listing carries o-projeto/, candidaturas/, legal pages,
    # social profiles and the wpcomstaging link — none may leak in.
    assert not any("/o-projeto/" in u or "/candidaturas/" in u for u in urls)
    assert not any("privacidade" in u or "termos" in u or "cookies" in u for u in urls)
    assert all(u.startswith("https://impossiblecoffees.com/cafe-") for u in urls)


def test_fetch_page_narrows_product_soup_to_main():
    scraper = _make_scraper()
    full_soup = _amboim_soup()

    narrowed = scraper._narrow_product_soup(full_soup, AMBOIM_URL)

    # The narrowed soup is the main#main element itself.
    assert narrowed.name == "main"
    assert narrowed.get("id") == "main"
    # The coffee story survives the narrowing.
    assert "Robusta Amboim" in narrowed.get_text(" ", strip=True)
    assert "23078.84" in narrowed.get_text(" ", strip=True)


def test_fetch_page_narrowing_leaves_listing_untouched():
    scraper = _make_scraper()
    listing_soup = _listing_soup()

    assert scraper._narrow_product_soup(listing_soup, LISTING_URL) is listing_soup


def test_postprocess_pins_eur_and_strips_fundraiser_prices():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Café Amboim",
        roaster="Impossible Coffees",
        url=AMBOIM_URL,
        origins=[],
        price_options=[],
    )
    # Simulate the AI extracting a product price — e.g. derived from the
    # "Valor angariado ... 23078.84 €" fundraising counter. (A schema-plausible
    # price is used because CoffeeBean validates price bounds on assignment.)
    from kissaten.schemas import PriceOption

    bean.price_options = [PriceOption(price=22.50, weight=250, currency="EUR")]
    bean.price = 22.50
    bean.currency = "GBP"

    out = scraper.postprocess_extracted_bean(bean)

    assert out.currency == "EUR"
    assert out.price_options == []
    assert out.price is None


async def test_scrape_new_products_translates_to_english(mocker):
    scraper = _make_scraper()

    capture = {}

    async def fake_scrape_with_ai_extraction(**kwargs):
        capture.update(kwargs)
        return []

    mocker.patch.object(scraper, "scrape_with_ai_extraction", side_effect=fake_scrape_with_ai_extraction)

    urls = await scraper._scrape_new_products([AMBOIM_URL])

    assert urls == []
    assert capture["use_playwright"] is False
    assert capture["translate_to_english"] is True
    assert capture["ai_extractor"] is scraper.ai_extractor
    # The URL-provider closure hands back the product URLs unchanged.
    provider = capture["extract_product_urls_function"]
    assert await provider(LISTING_URL) == [AMBOIM_URL]
