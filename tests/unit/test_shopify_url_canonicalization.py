"""Unit tests for Shopify collection-prefixed product URL canonicalization.

Archers Coffee and Flower Child Coffee list the same physical product under
multiple collections (e.g. active-coffee + archive, espresso-milk + pour-over).
Each overrides ``preprocess_product_url`` to collapse the collection segment so
the same handle merges across collections into a single ``/products/<handle>``
URL, avoiding duplicate beans — while distinct filter/espresso products keep
different handles and stay separate.

The tests also cover the ``_canonicalize_url`` history hook: old
``/collections/<slug>/products/<handle>`` history entries must be recognised as
the same bean as their canonical ``/products/<handle>`` form so they are not
re-scraped and not mis-marked out-of-stock during the URL-format transition.
"""

import pytest

from kissaten.scrapers.base import BaseScraper


class MockPlainScraper(BaseScraper):
    """Minimal concrete BaseScraper (default identity ``_canonicalize_url``)."""

    def __init__(self):
        super().__init__(
            roaster_name="Proper Roaster",
            base_url="https://proper-roaster.com",
            rate_limit_delay=0,
        )

    async def get_store_urls(self) -> list[str]:
        return ["https://proper-roaster.com/collections/all"]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        return []


@pytest.fixture
def archers(monkeypatch):
    from kissaten import ai as ai_module
    from kissaten.scrapers import archers_coffee

    # Avoid constructing a real AI extractor (needs an API key + Agent).
    monkeypatch.setattr(ai_module, "CoffeeDataExtractor", lambda api_key=None: None)
    return archers_coffee.ArchersCoffeeScraper()


@pytest.fixture
def flower_child(monkeypatch):
    from kissaten import ai as ai_module
    from kissaten.scrapers import flower_child_coffee

    monkeypatch.setattr(ai_module, "CoffeeDataExtractor", lambda api_key=None: None)
    return flower_child_coffee.FlowerChildCoffeeScraper()


class TestBaseCanonicalizeIdentity:
    """Default ``_canonicalize_url`` is the identity for all other scrapers."""

    def test_identity_returns_url_unchanged(self):
        scraper = MockPlainScraper()
        url = "https://x.com/products/a"
        assert scraper._canonicalize_url(url) == url

    def test_identity_normalize_roundtrip(self):
        scraper = MockPlainScraper()
        url = "https://x.com/collections/a/products/b"
        assert scraper._normalize_url(scraper._canonicalize_url(url)) == scraper._normalize_url(url)



class TestArchersCanonicalization:
    def test_collection_prefixed_url_canonicalized(self, archers):
        url = "https://archerscoffee.com/collections/espresso-milk-coffees-2025/products/benchmark"
        assert archers.preprocess_product_url(url) == "https://archerscoffee.com/products/benchmark"

    def test_canonicalize_url_collapses_collection(self, archers):
        assert (
            archers._canonicalize_url(
                "https://archerscoffee.com/collections/espresso-milk-coffees-2025/products/benchmark"
            )
            == "https://archerscoffee.com/products/benchmark"
        )

    def test_preprocess_product_url_delegates_to_canonicalize(self, archers):
        url = "https://archerscoffee.com/collections/espresso-milk-coffees-2025/products/benchmark"
        assert archers.preprocess_product_url(url) == archers._canonicalize_url(url)

    def test_pour_over_collection_canonicalized(self, archers):
        url = "https://archerscoffee.com/collections/pour-over-coffees-2025/products/benchmark"
        assert archers.preprocess_product_url(url) == "https://archerscoffee.com/products/benchmark"

    def test_plain_product_url_unchanged(self, archers):
        url = "https://archerscoffee.com/products/benchmark"
        assert archers.preprocess_product_url(url) == url

    def test_mark_then_query_symmetry(self, archers):
        """Marking the canonical form makes old collection forms count as scraped."""
        archers._mark_bean_as_scraped("https://archerscoffee.com/products/benchmark")
        assert (
            archers._is_bean_already_scraped_historically(
                "https://archerscoffee.com/collections/bespoke-blends-2025/products/benchmark"
            )
            is True
        )
        assert (
            archers._is_bean_already_scraped_anywhere(
                "https://archerscoffee.com/collections/espresso-milk-coffees-2025/products/benchmark"
            )
            is True
        )

    def test_history_load_detects_old_collection_url(self, archers, tmp_path):
        """Old collection-prefixed history entries map to the canonical bean.

        Proves old-format products are detected and won't be re-scraped (full AI
        re-extraction) and won't be mis-marked out-of-stock.
        """
        session_dir = tmp_path / "roasters" / "archers_coffee" / "20240101"
        session_dir.mkdir(parents=True)
        (session_dir / "benchmark.json").write_text(
            '{"url": "https://archerscoffee.com/collections/bespoke-blends-2025/products/benchmark", '
            '"name": "Benchmark", "roaster": "Archers Coffee"}',
            encoding="utf-8",
        )

        archers._load_existing_beans_from_all_sessions(tmp_path)

        assert archers._is_bean_already_scraped_anywhere("https://archerscoffee.com/products/benchmark") is True



class TestFlowerChildCanonicalization:
    def test_archive_collection_canonicalized(self, flower_child):
        url = "https://flowerchildcoffee.com/collections/archive/products/colombia-huila"
        assert flower_child.preprocess_product_url(url) == "https://flowerchildcoffee.com/products/colombia-huila"

    def test_active_collection_canonicalized(self, flower_child):
        url = "https://flowerchildcoffee.com/collections/active-coffee/products/colombia-huila"
        assert flower_child.preprocess_product_url(url) == "https://flowerchildcoffee.com/products/colombia-huila"

    def test_plain_product_url_unchanged(self, flower_child):
        url = "https://flowerchildcoffee.com/products/colombia-huila"
        assert flower_child.preprocess_product_url(url) == url


class TestExtractionCanonicalization:
    """The Shopify extractor applies preprocess_product_url and still excludes
    non-coffee handles (e.g. gift-card)."""

    @pytest.mark.asyncio
    async def test_archers_extract_canonical_and_excludes_gift_card(self, archers, monkeypatch):
        products = [
            {"handle": "benchmark", "title": "Benchmark Espresso", "variants": [{"available": True}]},
            {"handle": "gift-card", "title": "Gift Card", "variants": [{"available": True}]},
        ]

        async def fake_fetch(products_json_url):
            return products

        monkeypatch.setattr(archers, "_fetch_all_shopify_products", fake_fetch)

        urls = await archers._extract_product_urls_from_store(
            "https://archerscoffee.com/collections/espresso-milk-coffees-2025/products.json"
        )
        assert urls == ["https://archerscoffee.com/products/benchmark"]
