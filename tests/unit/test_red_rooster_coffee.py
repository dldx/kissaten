"""Unit tests for the Red Rooster Coffee scraper (fixture-based, no network).

Fixtures are trimmed copies of the Next.js ``__NEXT_DATA__`` JSON islands that
the site embeds on its /shop grid and /products/<slug> detail pages.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.red_rooster_coffee import RedRoosterCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
SHOP_URL = "https://www.redroostercoffee.com/shop"
PRODUCT_URL = "https://www.redroostercoffee.com/products/ethiopia-wush-wush-natural"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text()


def _make_scraper() -> RedRoosterCoffeeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return RedRoosterCoffeeScraper(api_key="test-api-key")


def _shop_soup() -> BeautifulSoup:
    return BeautifulSoup(_load("red_rooster_shop_next_data.html"), "lxml")


def _product_soup() -> BeautifulSoup:
    return BeautifulSoup(_load("red_rooster_product_next_data.html"), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("red-rooster-coffee")
    assert info is not None
    assert info.roaster_name == "Red Rooster"
    assert info.display_name == "Red Rooster"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Red Rooster"


async def test_store_urls_use_shop_grid():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [SHOP_URL]


def test_parse_next_data_extracts_payload():
    data = RedRoosterCoffeeScraper.parse_next_data(_shop_soup())
    assert data is not None
    tiles = data["props"]["pageProps"]["tiles"]
    assert len(tiles) > 0


def test_parse_next_data_returns_none_without_island():
    soup = BeautifulSoup("<html><body>no data island</body></html>", "lxml")
    assert RedRoosterCoffeeScraper.parse_next_data(soup) is None


async def test_extracts_coffee_urls_from_shop_grid(mocker):
    scraper = _make_scraper()
    mocker.patch.object(BaseScraper, "fetch_page", return_value=_shop_soup())

    urls = await scraper._extract_product_urls_from_store(SHOP_URL)

    assert "https://www.redroostercoffee.com/products/tree-of-life-regenerative-organic-certified" in urls
    assert "https://www.redroostercoffee.com/products/kenya-karimikui-kirinyaga-washed" in urls
    assert "https://www.redroostercoffee.com/products/best-sellers" in urls
    # Every extracted URL uses the /products/ path format.
    assert all("/products/" in u for u in urls)
    assert len(urls) == 8


async def test_sold_out_products_are_skipped(mocker):
    scraper = _make_scraper()
    mocker.patch.object(BaseScraper, "fetch_page", return_value=_shop_soup())

    urls = await scraper._extract_product_urls_from_store(SHOP_URL)

    # Wush Wush Natural carries all-variant zero inventory in the shop grid.
    assert "https://www.redroostercoffee.com/products/ethiopia-wush-wush-natural" not in urls


async def test_banner_tiles_and_merch_are_ignored(mocker):
    scraper = _make_scraper()
    mocker.patch.object(BaseScraper, "fetch_page", return_value=_shop_soup())

    urls = await scraper._extract_product_urls_from_store(SHOP_URL)

    # Banner tiles carry no product; the two remaining tiles are coffee-only
    # so no merch slugs can appear.
    assert len(urls) == 8
    assert all(u.startswith("https://www.redroostercoffee.com/products/") for u in urls)


async def test_failed_listing_returns_empty(mocker):
    scraper = _make_scraper()
    mocker.patch.object(BaseScraper, "fetch_page", return_value=None)

    urls = await scraper._extract_product_urls_from_store(SHOP_URL)
    assert urls == []


def test_tile_sold_out_helper():
    sold_out = {"product": {"variants": [{"inventoryQuantity": 0}, {"inventoryQuantity": 0}]}}
    in_stock = {"product": {"variants": [{"inventoryQuantity": 0}, {"inventoryQuantity": 9986}]}}
    no_variants = {"product": {"variants": []}}
    assert RedRoosterCoffeeScraper._tile_is_sold_out(sold_out) is True
    assert RedRoosterCoffeeScraper._tile_is_sold_out(in_stock) is False
    assert RedRoosterCoffeeScraper._tile_is_sold_out(no_variants) is False


def test_build_product_soup_contains_product_facts():
    data = RedRoosterCoffeeScraper.parse_next_data(_product_soup())
    page_props = data["props"]["pageProps"]
    soup = RedRoosterCoffeeScraper._build_product_soup(page_props)
    text = soup.get_text(" ", strip=True)

    assert "Ethiopia Wush Wush Natural" in text
    assert "Price: $22.00" in text
    # The Wush Wush Natural lot is sold out (disablePurchase + zero-qty variants).
    assert "Availability: Out of stock" in text
    # Tags / tasting notes / variant options.
    assert "Natural Process" in text
    assert "Raspberry Lemonade" in text
    assert "12OZ / Whole Bean" in text
    # Description and structured spec sheet for AI extraction.
    assert "Wush Wush washing station" in text
    assert "Keffa, Ginbo, Ethiopia" in text
    assert "Landrace" in text
    assert "1,912 masl" in text


async def test_fetch_page_narrows_product_urls_to_next_data(mocker):
    scraper = _make_scraper()

    async def fake_base_fetch(self, url, **kwargs):
        return _product_soup()

    mocker.patch.object(BaseScraper, "fetch_page", fake_base_fetch)
    result = await scraper.fetch_page(PRODUCT_URL, use_playwright=False)
    assert result is not None
    text = result.get_text(" ", strip=True)
    assert "Ethiopia Wush Wush Natural" in text
    assert "Keffa, Ginbo, Ethiopia" in text
    # The compact soup must drop the 600+ KB React markup.
    assert len(str(result)) < 10000


async def test_fetch_page_returns_non_product_pages_untouched(mocker):
    scraper = _make_scraper()
    sentinel = _shop_soup()

    async def fake_base_fetch(self, url, **kwargs):
        return sentinel

    mocker.patch.object(BaseScraper, "fetch_page", fake_base_fetch)
    result = await scraper.fetch_page(SHOP_URL, use_playwright=False)
    assert result is sentinel


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://www.redroostercoffee.com/products/test-bean",
        roaster="Red Rooster",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "USD"
