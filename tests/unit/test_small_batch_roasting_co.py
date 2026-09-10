"""Unit tests for the Small Batch Roasting Co. (Melbourne, AU) scraper."""

import pytest
from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.small_batch_roasting_co import SmallBatchRoastingCoScraper

HTML_SAMPLE = """
<div class="products">
    <div class="product_item">
        <a href="https://www.smallbatch.com.au/shop/espresso/candyman-espresso-blend/">
            <h3>Candyman Espresso Blend</h3>
        </a>
        <span class="price">$20 – $68</span>
    </div>
    <div class="product_item">
        <a href="https://www.smallbatch.com.au/shop/filter/golden-ticket-filter/">
            <h3>Golden Ticket</h3>
        </a>
        <span class="price">$21 – $70</span>
    </div>
    <div class="product_item">
        <a href="https://www.smallbatch.com.au/shop/bundles/4_bundle/">
            <h3>4 x 250g Bundle</h3>
        </a>
        <span class="price">$80</span>
    </div>
    <!-- Sold out item -->
    <div class="product_item">
        <a href="https://www.smallbatch.com.au/shop/filter/sold-out-coffee/">
            <h3>Sold Out Coffee</h3>
        </a>
        <span class="price">$25</span>
        <span class="badge">Sold Out</span>
    </div>
    <!-- Out of stock item -->
    <div class="product_item">
        <a href="https://www.smallbatch.com.au/shop/espresso/unavailable-lot/">
            <h3>Unavailable Lot</h3>
        </a>
        <span class="price">$25</span>
        <span>Out of stock</span>
    </div>
    <!-- Non-coffee item (merchandise) -->
    <div class="product_item">
        <a href="https://www.smallbatch.com.au/shop/merchandise/tshirt/">
            <h3>Roastery T-Shirt</h3>
        </a>
        <span class="price">$35</span>
    </div>
    <!-- Invalid non-product link -->
    <div class="product_item">
        <a href="https://www.smallbatch.com.au/about-us/">
            <h3>About Us</h3>
        </a>
    </div>
</div>
"""


def test_registry_registration():
    registry = get_registry()
    info = registry.get_scraper_info("small-batch-roasting-co")
    assert info is not None
    assert info.name == "small-batch-roasting-co"
    assert info.display_name == "Small Batch Roasting Co."
    assert info.roaster_name == "Small Batch"
    assert info.website == "https://www.smallbatch.com.au"
    assert info.country == "Australia"
    assert info.currency == "AUD"
    assert info.directory_name == "small_batch"


def test_directory_name_distinct_from_uk():
    registry = get_registry()
    au_info = registry.get_scraper_info("small-batch-roasting-co")
    uk_info = registry.get_scraper_info("small-batch")

    assert au_info is not None
    assert uk_info is not None
    assert au_info.directory_name == "small_batch"
    assert uk_info.directory_name == "small_batch_coffee_roasters"
    assert au_info.roaster_name == "Small Batch"
    assert uk_info.roaster_name == "Small Batch Coffee Roasters"


@pytest.mark.asyncio
async def test_extract_product_urls_from_store(monkeypatch: pytest.MonkeyPatch):
    scraper = SmallBatchRoastingCoScraper(api_key="test-api-key")
    soup = BeautifulSoup(HTML_SAMPLE, "lxml")

    async def fake_fetch_page(url: str, retries: int = 0, use_playwright: bool = False) -> BeautifulSoup | None:
        return soup

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch_page)

    urls = await scraper._extract_product_urls_from_store("https://www.smallbatch.com.au/product-category/espresso/")

    # Should keep Candyman, Golden Ticket, and 4 x 250g Bundle
    assert len(urls) == 3
    assert "https://www.smallbatch.com.au/shop/espresso/candyman-espresso-blend/" in urls
    assert "https://www.smallbatch.com.au/shop/filter/golden-ticket-filter/" in urls
    assert "https://www.smallbatch.com.au/shop/bundles/4_bundle/" in urls

    # Sold out / out of stock should be excluded
    assert "https://www.smallbatch.com.au/shop/filter/sold-out-coffee/" not in urls
    assert "https://www.smallbatch.com.au/shop/espresso/unavailable-lot/" not in urls

    # Non-coffee merchandise should be excluded
    assert "https://www.smallbatch.com.au/shop/merchandise/tshirt/" not in urls


@pytest.mark.asyncio
async def test_failed_listing_url_recorded(monkeypatch: pytest.MonkeyPatch):
    scraper = SmallBatchRoastingCoScraper(api_key="test-api-key")

    async def fake_fetch_page(url: str, retries: int = 0, use_playwright: bool = False) -> BeautifulSoup | None:
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch_page)

    store_url = "https://www.smallbatch.com.au/product-category/espresso/"
    urls = await scraper._extract_product_urls_from_store(store_url)

    assert urls == []
    assert store_url in scraper._failed_listing_urls


def test_tasting_kit_and_review_flags():
    scraper = SmallBatchRoastingCoScraper(api_key="test-api-key")

    bundle_bean = CoffeeBean(
        name="4 x 250g Bundle",
        roaster="Small Batch",
        url="https://www.smallbatch.com.au/shop/bundles/4_bundle/",
        origins=[],
        price_options=[],
        price=80.0,
        currency="AUD",
    )
    scraper._apply_product_flags(bundle_bean, str(bundle_bean.url), is_new=True)
    assert bundle_bean.is_tasting_kit is True
    assert bundle_bean.requires_review is True

    single_bean = CoffeeBean(
        name="Candyman Espresso Blend",
        roaster="Small Batch",
        url="https://www.smallbatch.com.au/shop/espresso/candyman-espresso-blend/",
        origins=[],
        price_options=[],
        price=20.0,
        currency="AUD",
    )
    scraper._apply_product_flags(single_bean, str(single_bean.url), is_new=True)
    assert single_bean.is_tasting_kit is False
    assert single_bean.requires_review is False


def test_postprocess_extracted_bean():
    scraper = SmallBatchRoastingCoScraper(api_key="test-api-key")
    bean = CoffeeBean(
        name="Candyman Espresso Blend",
        roaster="Small Batch",
        url="https://www.smallbatch.com.au/shop/espresso/candyman-espresso-blend/",
        origins=[],
        price_options=[],
        price=20.0,
        currency="USD",
    )
    processed = scraper.postprocess_extracted_bean(bean)
    assert processed is not None
    assert processed.currency == "AUD"
