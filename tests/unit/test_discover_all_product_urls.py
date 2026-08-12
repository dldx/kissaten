"""Unit tests for BaseScraper.discover_all_product_urls.

The method discovers every coffee product URL across all store/listing pages
without doing any extraction. These tests are fully self-contained (no
network): they stub only the two abstract hooks that the method depends on,
``get_store_urls`` and ``_extract_product_urls_from_store``.
"""

import pytest

from kissaten.scrapers.base import BaseScraper


class MockScraper(BaseScraper):
    """Minimal concrete BaseScraper for testing URL discovery."""

    def __init__(self, store_urls, products_by_store):
        super().__init__(
            roaster_name="Proper Roaster",
            base_url="https://proper-roaster.com",
            rate_limit_delay=0,
        )
        self._store_urls = store_urls
        self._products_by_store = products_by_store

    async def get_store_urls(self) -> list[str]:
        return self._store_urls

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        return self._products_by_store.get(store_url, [])


class TestDiscoverAllProductUrls:
    @pytest.mark.asyncio
    async def test_deduplicates_and_preserves_order_within_and_across_stores(self):
        store_a = "https://proper-roaster.com/collections/all"
        store_b = "https://proper-roaster.com/collections/2"
        scraper = MockScraper(
            store_urls=[store_a, store_b],
            products_by_store={
                # Overlap between pages is deliberate to test cross-page dedup
                store_a: ["/products/ethiopia", "/products/colombia", "/products/ethiopia"],
                store_b: ["/products/colombia", "/products/kenya", "/products/kenya"],
            },
        )

        urls = await scraper.discover_all_product_urls()

        # First-seen order wins; duplicates (within and across pages) removed
        assert urls == ["/products/ethiopia", "/products/colombia", "/products/kenya"]
        assert len(urls) == 3

    @pytest.mark.asyncio
    async def test_starts_session_when_none_exists(self):
        scraper = MockScraper(
            store_urls=["https://proper-roaster.com/collections/all"],
            products_by_store={"https://proper-roaster.com/collections/all": ["/products/ethiopia"]},
        )
        assert scraper.session is None

        await scraper.discover_all_product_urls()

        assert scraper.session is not None
        assert scraper.session.roaster_name == "Proper Roaster"

    @pytest.mark.asyncio
    async def test_records_empty_listing_page_in_failed_listing_urls(self):
        store_ok = "https://proper-roaster.com/collections/all"
        store_failed = "https://proper-roaster.com/collections/broken"
        scraper = MockScraper(
            store_urls=[store_ok, store_failed],
            products_by_store={
                store_ok: ["/products/ethiopia"],
                store_failed: [],  # e.g. a listing fetch that failed
            },
        )

        urls = await scraper.discover_all_product_urls()

        assert urls == ["/products/ethiopia"]
        assert store_failed in scraper._failed_listing_urls
        assert store_ok not in scraper._failed_listing_urls

    @pytest.mark.asyncio
    async def test_empty_result_when_all_pages_yield_no_products(self):
        store_a = "https://proper-roaster.com/collections/all"
        store_b = "https://proper-roaster.com/collections/2"
        scraper = MockScraper(store_urls=[store_a, store_b], products_by_store={store_a: [], store_b: []})

        urls = await scraper.discover_all_product_urls()

        assert urls == []
        assert scraper._failed_listing_urls == [store_a, store_b]
