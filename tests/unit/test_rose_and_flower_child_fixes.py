"""Unit tests for the Rose Coffee and Flower Child Coffee scraper fixes.

Rose Coffee:
- ``_extract_product_urls_from_store`` now applies the central
  ``is_coffee_product_url()`` check, so non-coffee equipment (drippers, TIMEMORE
  products) no longer leaks into AI extraction.
- ``excluded_products`` no longer drops ``tasting-pack``: curated samplers are
  extracted and routed to the admin review queue instead of being silently
  dropped.

Flower Child Coffee:
- Only the ``active-coffee`` collection is scraped. The ``archive`` collection
  (~93 historical/out-of-stock products) is deliberately excluded (kept
  commented, like Sey) so it does not inflate the active bean count / in-stock
  ratio.
- ``_extract_bean_with_ai`` mirrors Sey's archive handling: any archived
  product (all Shopify variants unavailable) is marked out of stock.
- The existing ``preprocess_product_url`` / ``_canonicalize_url`` overrides are
  preserved.

Follows the style of ``test_shopify_url_canonicalization.py`` and
``test_tasting_kit_flags.py``, using the ``CoffeeDataExtractor`` monkeypatch to
construct scrapers without a real AI key.
"""

import pytest
from bs4 import BeautifulSoup

from kissaten import ai as ai_module
from kissaten.schemas import CoffeeBean
from kissaten.scrapers.shopify_base import ShopifyJsonScraper


@pytest.fixture
def rose_scraper(monkeypatch):
    from kissaten.scrapers import rose_coffee

    # Avoid constructing a real AI extractor (needs an API key + Agent). Rose
    # imports CoffeeDataExtractor from the kissaten.ai package inside __init__.
    monkeypatch.setattr(ai_module, "CoffeeDataExtractor", lambda api_key=None: None)
    return rose_coffee.RoseCoffeeScraper()


@pytest.fixture
def flower_child(monkeypatch):
    from kissaten.scrapers import flower_child_coffee

    monkeypatch.setattr(ai_module, "CoffeeDataExtractor", lambda api_key=None: None)
    return flower_child_coffee.FlowerChildCoffeeScraper()


class TestRoseCoffeeProductUrlFiltering:
    def test_dripper_excluded(self, rose_scraper):
        assert rose_scraper.is_coffee_product_url("https://rose-coffee.com/products/timemore-vector-dripper") is False

    def test_real_bean_kept(self, rose_scraper):
        assert rose_scraper.is_coffee_product_url("https://rose-coffee.com/products/colombia-huila") is True

    def test_tasting_pack_not_excluded(self, rose_scraper):
        assert "tasting-pack" not in rose_scraper.excluded_products

    def test_subscription_still_excluded(self, rose_scraper):
        assert "subscription" in rose_scraper.excluded_products

    def test_giftcard_and_sibarist_still_excluded(self, rose_scraper):
        assert "giftcard" in rose_scraper.excluded_products
        assert "sibarist" in rose_scraper.excluded_products

    @pytest.mark.asyncio
    async def test_extract_urls_skips_equipment(self, rose_scraper, monkeypatch):
        """_extract_product_urls_from_store keeps only coffee product URLs."""
        html = """
        <html><body>
        <div><div><a href="/products/timemore-vector-dripper">TIMEMORE Vector Dripper</a></div></div>
        <div><div><a href="/products/colombia-huila">Colombia Huila</a></div></div>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")

        async def fake_fetch(store_url, **kwargs):
            return soup

        monkeypatch.setattr(rose_scraper, "fetch_page", fake_fetch)

        urls = await rose_scraper._extract_product_urls_from_store("https://rose-coffee.com/collections/all-coffees")
        assert urls == ["https://rose-coffee.com/products/colombia-huila"]


class TestFlowerChildActiveOnly:
    def test_active_coffee_included(self, flower_child):
        assert any("active-coffee" in u for u in flower_child.products_json_urls)

    def test_archive_excluded(self, flower_child):
        assert not any(u and "archive" in u for u in flower_child.products_json_urls)

    def test_canonicalization_still_works(self, flower_child):
        assert (
            flower_child.preprocess_product_url(
                "https://flowerchildcoffee.com/collections/active-coffee/products/colombia-huila"
            )
            == "https://flowerchildcoffee.com/products/colombia-huila"
        )


class TestFlowerChildArchiveOutOfStock:
    """The ``_extract_bean_with_ai`` override marks archived products out of stock.

    Flower Child canonicalises product URLs to ``/products/<handle>`` (the
    collection segment is stripped by ``preprocess_product_url``), so the
    override cannot detect the archive via the URL. It instead relies on the
    Shopify stock status: a product whose variants are all unavailable
    (``self._shopify_stock_status[url] is False``) is treated as archived.
    """

    URL = "https://flowerchildcoffee.com/products/colombia-huila"

    @pytest.fixture
    def bean(self):
        return CoffeeBean(
            name="Colombia Huila",
            roaster="Flower Child Coffee",
            url=self.URL,
            origins=[],
            price_options=[],
        )

    @pytest.fixture
    def empty_soup(self):
        return BeautifulSoup("<html><body></body></html>", "lxml")

    def _patch_parent_extract(self, flower_child, monkeypatch, bean):
        """Monkeypatch the parent ``_extract_bean_with_ai`` to return ``bean``.

        The fake takes an explicit ``self`` first parameter so that when it is
        bound (via ``super()`` lookup) the instance is consumed as ``self`` and
        the remaining arguments map 1:1 to ``ai_extractor``, ``soup``, ...
        """

        async def fake_extract(
            self, ai_extractor, soup, product_url, use_optimized_mode=False, translate_to_english=False
        ):
            return bean

        monkeypatch.setattr(ShopifyJsonScraper, "_extract_bean_with_ai", fake_extract)

    @pytest.mark.asyncio
    async def test_archived_bean_marked_out_of_stock(self, flower_child, monkeypatch, bean, empty_soup):
        self._patch_parent_extract(flower_child, monkeypatch, bean)
        flower_child._shopify_stock_status[self.URL] = False

        result = await flower_child._extract_bean_with_ai(None, empty_soup, self.URL)

        assert result is bean
        assert result.in_stock is False

    @pytest.mark.asyncio
    async def test_in_stock_bean_keeps_status(self, flower_child, monkeypatch, bean, empty_soup):
        bean.in_stock = True
        self._patch_parent_extract(flower_child, monkeypatch, bean)
        flower_child._shopify_stock_status[self.URL] = True

        result = await flower_child._extract_bean_with_ai(None, empty_soup, self.URL)

        assert result is bean
        assert result.in_stock is True

    @pytest.mark.asyncio
    async def test_unknown_url_keeps_status(self, flower_child, monkeypatch, bean, empty_soup):
        """URL not in the stock-status map (e.g. from history) is left as-is."""
        bean.in_stock = True
        self._patch_parent_extract(flower_child, monkeypatch, bean)

        result = await flower_child._extract_bean_with_ai(None, empty_soup, self.URL)

        assert result is bean
        assert result.in_stock is True
