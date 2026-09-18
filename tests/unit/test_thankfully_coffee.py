"""Unit tests for the Thankfully Coffee scraper (fixture-based, no network).

Thankfully Coffee is Shopify-hosted but has Shopify's JSON routes disabled,
so the fixture is the rendered ``/collections/coffee`` listing page (with the
real ``three-bags-per-month-roasters-choice`` subscription link injected for
exclusion coverage).
"""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.thankfully_coffee import ThankfullyCoffeeScraper

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
COLLECTION_FIXTURE = FIXTURES / "thankfully_coffee_collection.html"


def _collection_soup() -> BeautifulSoup:
    return BeautifulSoup(COLLECTION_FIXTURE.read_text(), "lxml")


@pytest.fixture
def scraper():
    return ThankfullyCoffeeScraper()


def test_registry_entry(scraper):
    info = get_registry().get_scraper_info("thankfully-coffee")
    assert info is not None
    assert info.roaster_name == "Thankfully"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Thankfully"


async def test_store_urls_use_curated_coffee_collection(scraper):
    urls = await scraper.get_store_urls()
    assert urls == ["https://thankfullycoffee.com/collections/coffee"]


async def test_extracts_product_urls_from_collection_fixture(scraper, mocker):
    mocker.patch.object(scraper, "fetch_page", return_value=_collection_soup())

    urls = await scraper._extract_product_urls_from_store(
        "https://thankfullycoffee.com/collections/coffee"
    )

    assert all(u.startswith("https://thankfullycoffee.com/products/") for u in urls)
    assert "https://thankfullycoffee.com/products/chelbesa-g1" in urls
    assert "https://thankfullycoffee.com/products/edinea-sartori-catucai-785" in urls
    assert "https://thankfullycoffee.com/products/fincas-del-putushio-mejorado" in urls
    assert "https://thankfullycoffee.com/products/guatemala-san-agustin-espresso" in urls


async def test_subscriptions_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "fetch_page", return_value=_collection_soup())

    urls = await scraper._extract_product_urls_from_store(
        "https://thankfullycoffee.com/collections/coffee"
    )

    # `new-product` is the 2-Bag Subscription; roasters-choice handles are
    # the Roasters Choice subscription plans.
    assert "https://thankfullycoffee.com/products/new-product" not in urls
    assert not any("roasters-choice" in u for u in urls)
    assert not any("subscription" in u for u in urls)


def test_postprocess_forces_usd(scraper):
    bean = CoffeeBean(
        name="Chelbesa",
        roaster="Thankfully",
        url="https://thankfullycoffee.com/products/chelbesa-g1",
        origins=[],
        price_options=[{"weight": 150, "price": 22.5, "currency": "USD"}],
    )
    bean.currency = "EUR"
    processed = scraper.postprocess_extracted_bean(bean)
    assert processed is not None
    assert processed.currency == "USD"
