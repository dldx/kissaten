"""Unit tests for the Wanderlust Espresso scraper (Wix storefront).

Tests run against **synthetic Wix Stores markup** shaped like the live
``/coffee-beans`` listing (``div[data-hook="product-item-root"]`` cards with
``/product-page/`` anchors and a Wix add-to-cart button). No network is
touched: ``fetch_page`` is stubbed with the fixture soup.

Live-site facts baked in at authoring time (2026-09, verified by hand):
- The store sells exactly four bean products (cosmic-blend, aeronautblend,
  beleza-blend, decaf-brazil); everything else in the catalogue is brewing
  kit (Hario/Kinto/V60), art prints and event services — all on other pages
  and/or caught by the base URL exclusion net.
- Currency is GBP, present only in the embedded rendered-state JSON (no
  ``og:price:currency`` meta tag), so the scraper pins GBP in postprocessing.
- Wix renders sold-out products with a disabled add-to-cart button reading
  "Out of Stock" inside the product-item-root card; that text (case-
  insensitive) is the sold-out signal the listing filter uses.
"""

import pytest
from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.wanderlust import WanderlustEspressoScraper

STORE_URL = "https://www.wanderlust-espresso.com/coffee-beans"
BASE = "https://www.wanderlust-espresso.com"


def _card(slug: str, in_stock: bool = True, name: str | None = None, href: str | None = None) -> str:
    """Build a Wix Stores product-item-root card like the live /coffee-beans listing."""
    href = href or f"{BASE}/product-page/{slug}"
    button = (
        '<button data-hook="product-item-add-to-cart-button"><span>Add to Cart</span></button>'
        if in_stock
        else '<button data-hook="product-item-add-to-cart-button" disabled="" aria-disabled="true">'
        "<span>Out of Stock</span></button>"
    )
    return f"""
    <div data-hook="product-item-root">
      <a data-hook="product-item-product-details-link" href="{href}">{name or slug}</a>
      <h3 data-hook="product-item-name">{name or slug}</h3>
      <span data-hook="product-item-price-to-pay">£8.50</span>
      {button}
    </div>
    """


def _listing(*cards: str) -> BeautifulSoup:
    return BeautifulSoup(f"<html><body><div>{''.join(cards)}</div></body></html>", "lxml")


def _make_scraper() -> WanderlustEspressoScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return WanderlustEspressoScraper(api_key="test-api-key")


async def _extract(soup: BeautifulSoup) -> list[str]:
    scraper = _make_scraper()

    async def fake_fetch_page(url, *args, **kwargs):
        return soup

    scraper.fetch_page = fake_fetch_page
    return await scraper._extract_product_urls_from_store(STORE_URL)


class TestExtractProductUrlsFromStore:
    """Wix listing extraction: in-stock bean cards in, sold-out and kit out."""

    @pytest.mark.asyncio
    async def test_extracts_in_stock_beans(self):
        soup = _listing(
            _card("cosmic-blend"),
            _card("beleza-blend", name="Beleza Espresso"),
            _card("decaf-brazil", name="Decaf - Colombia"),
        )

        urls = await _extract(soup)

        assert urls == [
            f"{BASE}/product-page/cosmic-blend",
            f"{BASE}/product-page/beleza-blend",
            f"{BASE}/product-page/decaf-brazil",
        ]

    @pytest.mark.asyncio
    async def test_strips_query_string_and_resolves_relative_hrefs(self):
        soup = _listing(
            _card("cosmic-blend", href=f"{BASE}/product-page/cosmic-blend?ref=4"),
            _card("beleza-blend", href="/product-page/beleza-blend"),
        )

        urls = await _extract(soup)

        assert urls == [f"{BASE}/product-page/cosmic-blend", f"{BASE}/product-page/beleza-blend"]

    @pytest.mark.asyncio
    async def test_sold_out_cards_excluded(self):
        soup = _listing(
            _card("cosmic-blend", in_stock=True),
            _card("aeronautblend", in_stock=False, name="Aeronaut Espresso"),
            _card("decaf-brazil", in_stock=False, name="Decaf - Colombia"),
        )

        urls = await _extract(soup)

        assert urls == [f"{BASE}/product-page/cosmic-blend"]

    @pytest.mark.asyncio
    async def test_sold_out_detection_is_case_insensitive(self):
        # Wix button labels vary in casing between app versions ("Out of Stock",
        # "Sold out", "SOLD OUT"); all must be caught.
        soup = BeautifulSoup(
            "<html><body>"
            + _card("cosmic-blend")
            + _card("aeronautblend", in_stock=False).replace("Out of Stock", "Sold Out")
            + _card("beleza-blend", in_stock=False).replace("Out of Stock", "SOLD OUT")
            + _card("decaf-brazil", in_stock=False).replace("Out of Stock", "Unavailable")
            + "</body></html>",
            "lxml",
        )

        urls = await _extract(soup)

        assert urls == [f"{BASE}/product-page/cosmic-blend"]

    @pytest.mark.asyncio
    async def test_non_coffee_products_excluded_if_they_leak_in(self):
        # Brewing kit slugs caught by the base URL exclusion net (the live shop
        # sells Hario/Kinto/V60 kit on a separate page).
        soup = _listing(
            _card("cosmic-blend", name="Cosmic Blend"),
            _card("hario-v60-plastic-coffee-dripper-02", name="Hario V60 Plastic Dripper"),
            _card("hario-x-project-waterfall-v60-filter-papers-100-pack", name="Hario V60 Filter Papers"),
            _card("wanderlust-gift-card", name="Gift Card"),
        )

        urls = await _extract(soup)

        assert urls == [f"{BASE}/product-page/cosmic-blend"]

    @pytest.mark.asyncio
    async def test_deduplicates_repeated_cards(self):
        soup = _listing(_card("cosmic-blend"), _card("cosmic-blend"))

        urls = await _extract(soup)

        assert urls == [f"{BASE}/product-page/cosmic-blend"]

    def test_wix_path_pattern_is_required(self):
        # Platform gotcha: base.is_coffee_product_url's default patterns
        # (/product/, /products/) do not match Wix's /product-page/ — the
        # scraper must pass required_path_patterns=["/product-page/"].
        scraper = _make_scraper()
        assert (
            scraper.is_coffee_product_url(f"{BASE}/product/cosmic-blend", required_path_patterns=["/product-page/"])
            is False
        )
        assert scraper.is_coffee_product_url(
            f"{BASE}/product-page/cosmic-blend", required_path_patterns=["/product-page/"]
        )

    @pytest.mark.asyncio
    async def test_extraction_uses_store_url_fetch_only(self):
        soup = _listing(_card("cosmic-blend"))
        scraper = _make_scraper()
        calls = []

        async def fake_fetch_page(url, *args, **kwargs):
            calls.append(url)
            return soup

        scraper.fetch_page = fake_fetch_page

        await scraper._extract_product_urls_from_store(STORE_URL)

        # Extraction must not fan out to product pages: exactly one fetch, of
        # the listing itself.
        assert calls == [STORE_URL]

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_fetch_fails(self):
        scraper = _make_scraper()

        async def fake_fetch_page(url, *args, **kwargs):
            return None

        scraper.fetch_page = fake_fetch_page

        assert await scraper._extract_product_urls_from_store(STORE_URL) == []


class TestFetchPageNarrowing:
    """Product detail pages are narrowed to div[data-hook='product-page']."""

    @pytest.mark.asyncio
    async def test_product_page_narrowed_to_product_container(self, mocker):
        scraper = _make_scraper()
        product_container = BeautifulSoup(
            '<html><body><nav>menu junk</nav>'
            '<div data-hook="product-page"><h1>Cosmic Blend</h1><p>£8.50</p></div>'
            "<footer>footer junk</footer></body></html>",
            "lxml",
        )

        async def fake_base_fetch_page(url, *args, **kwargs):
            return product_container

        mocker.patch.object(BaseScraper, "fetch_page", side_effect=fake_base_fetch_page)

        result = await scraper.fetch_page(f"{BASE}/product-page/cosmic-blend")

        text = result.get_text(" ", strip=True)
        assert "Cosmic Blend" in text
        assert "menu junk" not in text
        assert "footer junk" not in text

    @pytest.mark.asyncio
    async def test_listing_page_left_untouched(self, mocker):
        scraper = _make_scraper()
        listing = _listing(_card("cosmic-blend"))

        async def fake_base_fetch_page(url, *args, **kwargs):
            return listing

        mocker.patch.object(BaseScraper, "fetch_page", side_effect=fake_base_fetch_page)

        result = await scraper.fetch_page(STORE_URL)

        assert result.select('[data-hook="product-item-root"]')
        assert not result.select("div[data-hook='product-page']")


class TestCurrencyPinning:
    """GBP pinned: Wix pages have no og:price:currency meta for base detection."""

    def test_postprocess_forces_gbp(self):
        scraper = _make_scraper()
        bean = CoffeeBean(
            name="Cosmic Blend",
            roaster="Wanderlust Espresso",
            url=f"{BASE}/product-page/cosmic-blend",
            origins=[{"country": "BRA"}],
            price_options=[{"weight": 250, "price": 8.5}],
            price=8.5,
            weight=250,
            currency="USD",  # a misdetected currency must be overwritten
        )

        result = scraper.postprocess_extracted_bean(bean)

        assert result is bean
        assert bean.currency == "GBP"

    def test_store_currency_defaults_to_gbp(self):
        scraper = _make_scraper()
        assert scraper.store_currency == "GBP"


class TestRegistry:
    """Registry wiring and the roaster-name byte-identity invariant."""

    def test_registered_with_expected_fields(self):
        info = get_registry().get_scraper_info("wanderlust-espresso")

        assert info is not None
        assert info.name == "wanderlust-espresso"
        assert info.display_name == "Wanderlust Espresso"
        assert info.roaster_name == "Wanderlust Espresso"
        assert info.website == "https://www.wanderlust-espresso.com"
        assert info.currency == "GBP"
        assert info.country == "United Kingdom"
        assert info.requires_api_key is True
        assert info.scraper_class is WanderlustEspressoScraper

    def test_roaster_name_matches_registry(self):
        # BaseScraper._validate_roaster_name raises on mismatch, so clean
        # construction proves the @register_scraper and super().__init__
        # roaster_name strings are byte-identical.
        scraper = _make_scraper()
        assert scraper.roaster_name == "Wanderlust Espresso"

    @pytest.mark.asyncio
    async def test_store_urls(self):
        scraper = _make_scraper()

        urls = await scraper.get_store_urls()

        assert urls == ["https://www.wanderlust-espresso.com/coffee-beans"]
