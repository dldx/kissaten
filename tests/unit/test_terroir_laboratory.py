"""Unit tests for the Terroir Laboratory scraper (terroiridn.com).

Terroir Laboratory's storefront is localized under ``/en`` but canonical
product URLs are the plain ``/products/<handle>`` form, so the scraper's
``preprocess_product_url`` must strip the localized collection segment.
The ``/collections/all`` catalogue mixes coffee with branded apparel, so
the scraper excludes merch slugs (t-shirts etc.).
"""

import pytest

from kissaten import ai as ai_module
from kissaten.scrapers import terroir_laboratory


@pytest.fixture
def terroir(monkeypatch):
    # Avoid constructing a real AI extractor (needs an API key + Agent).
    monkeypatch.setattr(ai_module, "CoffeeDataExtractor", lambda api_key=None: None)
    return terroir_laboratory.TerroirLaboratoryScraper()


class TestRegistry:
    def test_registered(self):
        from kissaten.scrapers.registry import get_registry

        info = get_registry().get_scraper_info("terroir-laboratory")
        assert info is not None
        assert info.display_name == "Terroir Laboratory"
        assert info.country == "Indonesia"
        assert info.currency == "IDR"
        assert info.requires_api_key is True


class TestUrlCanonicalization:
    def test_strips_localized_collection_segment(self, terroir):
        url = "https://terroiridn.com/en/collections/all/products/black-original-omni-roast"
        assert terroir.preprocess_product_url(url) == "https://terroiridn.com/products/black-original-omni-roast"

    def test_plain_product_url_unchanged(self, terroir):
        url = "https://terroiridn.com/products/best-of-panama-2025"
        assert terroir.preprocess_product_url(url) == url

    def test_base_url_matches_store(self, terroir):
        assert terroir.base_url == "https://terroiridn.com"


class TestExclusions:
    def test_apparel_excluded(self, terroir):
        url = "https://terroiridn.com/products/t-shirt-in-geisha-we-trust-project-brewboy"
        assert not terroir.is_coffee_product_url(url)

    def test_coffee_url_included(self, terroir):
        url = "https://terroiridn.com/products/black-original-omni-roast"
        assert terroir.is_coffee_product_url(url)


class TestCurrencyPinned:
    """The store is IDR-only; geo-detection must not override it."""

    def test_store_currency_pinned(self, terroir):
        assert terroir.store_currency == "IDR"
        assert terroir._currency_detected is True


class TestSoupPruning:
    def test_prunes_to_product_information(self, terroir):
        from bs4 import BeautifulSoup

        html = """
        <html><body>
          <nav>menu</nav>
          <div class="product-information">
            <h1>Black Original</h1>
            <details><summary>Specifications</summary><div class="details-content">
              <p>• Roast Level : Omni Roast</p>
            </div></details>
          </div>
          <footer>shipping boilerplate</footer>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        pruned = terroir.preprocess_product_soup(soup)
        assert "product-information" in (pruned.get("class") or [])
        assert pruned.find("h1") is not None
        assert pruned.find("footer") is None

    def test_fallback_returns_full_soup(self, terroir):
        from bs4 import BeautifulSoup

        soup = BeautifulSoup("<html><body><h1>No info div</h1></body></html>", "lxml")
        assert terroir.preprocess_product_soup(soup) is soup
