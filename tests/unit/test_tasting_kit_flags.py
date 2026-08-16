"""Unit tests for the tasting-kit / review-flag helpers.

The tasting-kit review pipeline flags curated sampler/taster-pack products with
``is_tasting_kit`` and hides them from public search (``requires_review``) until
an admin approves or rejects them. These tests cover the URL classification and
the flag-application helper on ``BaseScraper`` plus the Skylark overrides.

This mirrors the style of ``test_out_of_stock_guard.py``: plain classes, no
network, and the ``MockPlainScraper`` pattern with a roaster name that is not in
the registry (so ``_validate_roaster_name`` is a no-op).
"""

import pytest

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper


class MockPlainScraper(BaseScraper):
    """Minimal concrete BaseScraper for testing the generic helpers."""

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


def _make_bean(url: str) -> CoffeeBean:
    return CoffeeBean(
        name="Test Bean",
        roaster="Proper Roaster",
        url=url,
        origins=[],
        price_options=[],
    )


@pytest.fixture
def scraper():
    return MockPlainScraper()


class TestIsTastingKitUrl:
    """is_tasting_kit_url() classifies curated sampler/taster URLs."""

    def test_true_for_kit_patterns(self, scraper):
        for url in (
            "https://proper-roaster.com/products/ethiopia-taster-pack",
            "https://proper-roaster.com/products/taster_pack-single-origin",
            "https://proper-roaster.com/products/colombia-sample-pack",
            "https://proper-roaster.com/products/brazil-sampler",
            "https://proper-roaster.com/products/kenya-tasting-kit",
            "https://proper-roaster.com/products/kenya-tasting-set",
        ):
            assert scraper.is_tasting_kit_url(url), f"expected kit True for {url}"

    def test_false_for_plain_bean_urls(self, scraper):
        assert not scraper.is_tasting_kit_url("https://proper-roaster.com/products/ethiopia-yirgacheffe")
        assert not scraper.is_tasting_kit_url("https://proper-roaster.com/products/colombia-huila")

    def test_false_for_equipment(self, scraper):
        assert not scraper.is_tasting_kit_url("https://proper-roaster.com/products/v60-dripper")
        assert not scraper.is_tasting_kit_url("https://proper-roaster.com/products/grinder")

    def test_false_for_empty(self, scraper):
        assert not scraper.is_tasting_kit_url("")
        assert not scraper.is_tasting_kit_url(None)


class TestApplyProductFlags:
    """_apply_product_flags() sets is_tasting_kit / requires_review correctly."""

    def test_kit_url_is_new_flags_both(self, scraper):
        bean = _make_bean("https://proper-roaster.com/products/ethiopia-taster-pack")
        scraper._apply_product_flags(bean, str(bean.url), is_new=True)
        assert bean.is_tasting_kit is True
        assert bean.requires_review is True

    def test_kit_url_not_new_keeps_review_false(self, scraper):
        bean = _make_bean("https://proper-roaster.com/products/ethiopia-taster-pack")
        scraper._apply_product_flags(bean, str(bean.url), is_new=False)
        assert bean.is_tasting_kit is True
        assert bean.requires_review is False

    def test_ai_detected_kit_kept_with_non_kit_url(self, scraper):
        # AI flagged is_tasting_kit=True even though the URL has no kit token.
        bean = _make_bean("https://proper-roaster.com/products/ethiopia-yirgacheffe")
        bean.is_tasting_kit = True
        scraper._apply_product_flags(bean, str(bean.url), is_new=True)
        assert bean.is_tasting_kit is True
        assert bean.requires_review is True

    def test_none_bean_noop(self, scraper):
        scraper._apply_product_flags(None, "https://proper-roaster.com/products/ethiopia-taster-pack")
        # No exception; nothing to assert on a None bean.


class TestIsCoffeeProductUrl:
    """is_coffee_product_url() now INCLUDES kit/sampler products (they are
    flagged for review instead of excluded), while equipment and services are
    still excluded."""

    def test_taster_pack_included(self, scraper):
        assert scraper.is_coffee_product_url("https://proper-roaster.com/products/ethiopia-taster-pack") is True

    def test_equipment_excluded(self, scraper):
        assert scraper.is_coffee_product_url("https://proper-roaster.com/products/v60-dripper") is False
        assert scraper.is_coffee_product_url("https://proper-roaster.com/products/grinder") is False

    def test_subscription_excluded(self, scraper):
        assert scraper.is_coffee_product_url("https://proper-roaster.com/products/subscription") is False

    def test_gift_card_excluded(self, scraper):
        assert scraper.is_coffee_product_url("https://proper-roaster.com/products/gift-card") is False


class TestSkylarkOverrides:
    """Skylark keeps base kit inclusion but still excludes its advent calendar."""

    @pytest.fixture
    def skylark(self, monkeypatch):
        from kissaten.scrapers import skylark_coffee

        # Avoid constructing a real AI extractor (needs an API key + Agent).
        monkeypatch.setattr(skylark_coffee, "CoffeeDataExtractor", lambda api_key=None: None)
        return skylark_coffee.SkylarkCoffeeScraper()

    def test_is_tasting_kit_url_true_for_fermentation_sample_pack(self, skylark):
        url = "https://skylark.coffee/collections/coffee/products/james-hoffmann-and-lucia-solis-fermentation-project-sample-pack"
        assert skylark.is_tasting_kit_url(url) is True

    def test_fermentation_pack_is_coffee_product(self, skylark):
        url = "https://skylark.coffee/collections/coffee/products/james-hoffmann-and-lucia-solis-fermentation-project-sample-pack"
        assert skylark.is_coffee_product_url(url) is True

    def test_four_pack_sampler_is_coffee_product(self, skylark):
        url = "https://skylark.coffee/products/four-pack-sampler-mixed"
        assert skylark.is_coffee_product_url(url) is True

    def test_12_days_of_christmas_excluded(self, skylark):
        url = "https://skylark.coffee/products/12-days-of-christmas-advent"
        assert skylark.is_coffee_product_url(url) is False
