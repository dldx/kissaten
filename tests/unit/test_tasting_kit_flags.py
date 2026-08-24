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


class TestIsCoffeeProductUrlEquipment:
    """The central equipment exclusions reject dripper/kettle/gooseneck/
    espresso-machine/brewer/canister/carafe/flask product URLs."""

    def test_dripper_excluded(self, scraper):
        assert scraper.is_coffee_product_url("https://proper-roaster.com/products/hario-dripper") is False

    def test_kettle_excluded(self, scraper):
        assert scraper.is_coffee_product_url("https://proper-roaster.com/products/kettle") is False
        assert scraper.is_coffee_product_url("https://proper-roaster.com/products/gooseneck-kettle") is False

    def test_espresso_machine_excluded(self, scraper):
        assert scraper.is_coffee_product_url("https://proper-roaster.com/products/espresso-machine") is False

    def test_brewer_excluded(self, scraper):
        assert scraper.is_coffee_product_url("https://proper-roaster.com/products/chemex-brewer") is False

    def test_canister_excluded(self, scraper):
        assert scraper.is_coffee_product_url("https://proper-roaster.com/products/coffee-canister") is False

    def test_carafe_excluded(self, scraper):
        assert scraper.is_coffee_product_url("https://proper-roaster.com/products/carafe") is False

    def test_flask_excluded(self, scraper):
        assert scraper.is_coffee_product_url("https://proper-roaster.com/products/flask") is False


class TestNameBasedReviewFlag:
    """_apply_product_flags() flags a bean as a tasting kit via its NAME even
    when the URL carries no kit token."""

    def test_sampler_gift_box_name_is_flagged(self, scraper):
        bean = _make_bean("https://proper-roaster.com/products/around-the-world")
        bean.name = "Around The World Coffee Sampler Gift Box"
        scraper._apply_product_flags(bean, str(bean.url), is_new=True)
        assert bean.is_tasting_kit is True
        assert bean.requires_review is True

    def test_plain_bean_name_not_flagged(self, scraper):
        bean = _make_bean("https://proper-roaster.com/products/ethiopia-yirgacheffe")
        bean.name = "Ethiopia Yirgacheffe"
        scraper._apply_product_flags(bean, str(bean.url), is_new=True)
        assert bean.is_tasting_kit is False
        assert bean.requires_review is False

    def test_bean_name_variants(self, scraper):
        for name in (
            "Single Origin Sampler",
            "Tasting Kit - 4 Origins",
            "Gift Box of Colombian Coffee",
            "Coffee Kit for Beginners",
            "Cupping Kit",
            "Sample Pack - Washed",
        ):
            bean = _make_bean("https://proper-roaster.com/products/plain-handle")
            bean.name = name
            scraper._apply_product_flags(bean, str(bean.url), is_new=True)
            assert bean.is_tasting_kit is True, f"expected kit True for name {name!r}"

    def test_missing_name_safe(self, scraper):
        # A bean with a missing/None name must not crash the flag logic.
        bean = _make_bean("https://proper-roaster.com/products/ethiopia-yirgacheffe")
        del bean.name
        scraper._apply_product_flags(bean, str(bean.url), is_new=True)
        assert bean.is_tasting_kit is False


class TestPostprocessReviewFlagsHook:
    """The default postprocess_review_flags() hook is a no-op."""

    def test_default_returns_bean_unchanged(self, scraper):
        bean = _make_bean("https://proper-roaster.com/products/ethiopia-yirgacheffe")
        bean.name = "Ethiopia Yirgacheffe"
        result = scraper.postprocess_review_flags(bean, str(bean.url))
        assert result is bean

    def test_hook_called_before_flags(self, scraper):
        # An override that forces is_tasting_kit is honored by _apply_product_flags.
        class ForcingScraper(MockPlainScraper):
            def postprocess_review_flags(self, bean, url):
                bean.is_tasting_kit = True
                return bean

        s = ForcingScraper()
        bean = _make_bean("https://proper-roaster.com/products/ethiopia-yirgacheffe")
        bean.name = "Ethiopia Yirgacheffe"
        s._apply_product_flags(bean, str(bean.url), is_new=True)
        assert bean.is_tasting_kit is True
        assert bean.requires_review is True


class TestKafferavenOverrides:
    """Kafferäven keeps "The Fermentation Project" as a reviewed tasting kit and
    excludes its gift card (presentkort)."""

    @pytest.fixture
    def kafferaven(self, monkeypatch):
        from kissaten import ai as ai_module
        from kissaten.scrapers import kafferaven

        # Avoid constructing a real AI extractor (needs an API key + Agent).
        monkeypatch.setattr(ai_module, "CoffeeDataExtractor", lambda api_key=None: None)
        return kafferaven.KafferavenScraper()

    def test_fermentation_project_is_tasting_kit(self, kafferaven):
        url = "https://www.kafferaven.se/collections/kaffebonor/products/the-fermentation-project-med-james-hoffmann"
        assert kafferaven.is_tasting_kit_url(url) is True

    def test_fermentation_project_is_coffee_product(self, kafferaven):
        url = "https://www.kafferaven.se/collections/kaffebonor/products/the-fermentation-project-med-james-hoffmann"
        assert kafferaven.is_coffee_product_url(url) is True

    def test_presentkort_gift_card_excluded(self, kafferaven):
        # "presentkort" is a roaster-specific slug, applied in the Shopify
        # extraction loop (exclude_slugs) rather than is_coffee_product_url.
        assert "presentkort" in kafferaven.exclude_slugs


class TestDearGreenExclusions:
    """Dear Green excludes equipment/merch/books/tours but extracts tasting kits."""

    @pytest.fixture
    def dear_green(self, monkeypatch):
        from kissaten import ai as ai_module
        from kissaten.scrapers import dear_green

        monkeypatch.setattr(ai_module, "CoffeeDataExtractor", lambda api_key=None: None)
        return dear_green.DearGreenScraper()

    def test_exclude_slugs_contains_equipment(self, dear_green):
        for slug in ("dripper", "kettle", "tour", "poster", "grinder", "book"):
            assert slug in dear_green.exclude_slugs, f"expected {slug!r} in exclude_slugs"

    def test_exclude_slugs_does_not_contain_kit(self, dear_green):
        # Tasting kits are extracted and review-flagged, not excluded.
        assert "kit" not in dear_green.exclude_slugs

    def test_equipment_handles_excluded(self, dear_green):
        # These hit the central equipment URL patterns.
        for url in (
            "https://deargreencoffee.com/products/aergrind-hand-grinder-made-by-knock",
            "https://deargreencoffee.com/products/hario-v60-dripper",
            "https://deargreencoffee.com/products/gooseneck-kettle",
            "https://deargreencoffee.com/products/espresso-machine",
            "https://deargreencoffee.com/products/chemex-brewer",
        ):
            assert dear_green.is_coffee_product_url(url) is False, f"expected excluded {url}"

    @pytest.mark.asyncio
    async def test_roaster_specific_slugs_skip_extraction(self, dear_green, monkeypatch):
        # book / tour / poster / print are Dear-Green-specific (exclude_slugs),
        # applied in the Shopify extraction loop.
        handles = ["dear-green-coffee-book", "roastery-tour", "poster", "risoprint"]
        products = [{"handle": h, "title": h, "variants": [{"available": True}]} for h in handles]

        async def fake_fetch(products_json_url):
            return products

        monkeypatch.setattr(dear_green, "_fetch_all_shopify_products", fake_fetch)
        urls = await dear_green._extract_product_urls_from_store(
            "https://deargreencoffee.com/collections/all/products.json"
        )
        assert urls == []

    @pytest.mark.asyncio
    async def test_tasting_kit_extracted_not_excluded(self, dear_green, monkeypatch):
        # A tasting-kit handle (no "cupping" token, which is a separate central
        # pattern) is no longer in exclude_slugs, so it is extracted and
        # review-flagged rather than dropped.
        products = [{"handle": "coffee-tasting-kit", "title": "Coffee Tasting Kit", "variants": [{"available": True}]}]

        async def fake_fetch(products_json_url):
            return products

        monkeypatch.setattr(dear_green, "_fetch_all_shopify_products", fake_fetch)
        urls = await dear_green._extract_product_urls_from_store(
            "https://deargreencoffee.com/collections/all/products.json"
        )
        # Dear Green does not override preprocess_product_url, so the handle
        # keeps the collection prefix, but the kit handle is no longer excluded.
        assert urls == ["https://deargreencoffee.com/collections/all/products/coffee-tasting-kit"]
        assert (
            dear_green.is_tasting_kit_url("https://deargreencoffee.com/collections/all/products/coffee-tasting-kit")
            is True
        )


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
