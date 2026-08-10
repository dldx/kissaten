"""Origin Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="origin-coffee",
    display_name="Origin Coffee Roasters",
    roaster_name="Origin Coffee Roasters",
    website="https://www.origincoffee.co.uk",
    description="Leading UK speciality coffee roaster based in Cornwall (roastery in "
    "Porthleven), proudly B Corp certified with a focus on sustainability, "
    "direct trade and releasing a new coffee every week.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class OriginCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Origin Coffee Roasters (origincoffee.co.uk) using Shopify products.json.

    Origin publishes the same coffee across several overlapping collections
    (``coffee``, ``single-origin-coffee-beans``, ``coffee-blends``,
    ``espresso-coffee``, ``filter-coffee``, ``decaf-coffee-beans``). Including
    them all means a product is discovered even if Origin reorganises one
    collection; ``preprocess_product_url`` canonicalises every collection URL to
    ``https://www.origincoffee.co.uk/products/<handle>`` (the exact form used on
    the live site), so duplicate listings across collections collapse to one
    URL and are never scraped twice.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Origin Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Origin Coffee Roasters",
            base_url="https://www.origincoffee.co.uk",
            products_json_urls=[
                "https://www.origincoffee.co.uk/collections/coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products. NOTE: "mug" is intentionally absent —
        # the single-origin bean "mugaga-kagumoini" contains it as a substring
        # and would be wrongly dropped by the substring match.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "sampler",
            "taster-pack",
            "apparel",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "cold-brew",
            "ready-to-drink",
            "coffee-cup",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_soup(self, soup: any) -> any:
        """Limit AI extraction to the product information accordion.

        Origin's product pages put all the coffee details — Story, Provenance
        (country, region, elevation, producer, variety), Transparency (cup
        score, FOB price) and Brewing recipe — inside a single
        ``ul.info__fields`` accordion. Returning only that fragment keeps the
        soup sent to the AI focused and small, while the full-page screenshot
        (taken in optimized mode) still supplies the visual context.
        """
        fields = soup.select_one("ul.info__fields")
        if fields:
            logger.debug("Limiting extraction to ul.info__fields")
            return fields
        return soup

    def is_coffee_product_name(self, name: str) -> bool:
        """Treat promotion-suffixed coffee titles as coffee.

        Origin appends competition-entry copy to some coffee titles, e.g.
        "Resolute + Fellow Series One Competition Entry". The base-class name
        filter excludes the word "fellow" (as a Fellow-brand equipment guard)
        and would wrongly drop these coffees, so strip the promotional tail
        before delegating.
        """
        stripped = re.sub(r" \+ Fellow Series [A-Za-z]+ Competition Entry", "", name or "")
        return super().is_coffee_product_name(stripped)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalise product URLs to ``<base_url>/products/<handle>``.

        The products.json endpoints live under ``/collections/<slug>``, so the
        default URL construction yields ``/collections/<slug>/products/<handle>``.
        The live site uses the canonical ``/products/<handle>`` form (and
        redirects the bare domain to www), so we strip the collection segment
        here and normalise the host to www. Overlapping collections therefore
        merge onto a single URL and are never duplicated.
        """
        url = re.sub(r"/collections/[^/]+(?=/products/)", "", url)
        url = re.sub(r"^https://origincoffee\.co\.uk", "https://www.origincoffee.co.uk", url)
        return url
