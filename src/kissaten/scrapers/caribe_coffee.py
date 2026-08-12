"""Caribe Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="caribe",
    display_name="Caribe",
    roaster_name="Caribe",
    website="https://caribecoffee.co.uk",
    description="Specialty coffee roaster based in the United Kingdom offering "
    "single-origin coffees from Latin America",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CaribeCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Caribe Coffee (caribecoffee.co.uk) scraped JSON-only.

    The store is scraped from Shopify's products.json only, without fetching
    individual product pages. The products.json ``body_html`` already carries
    the full bean detail for every coffee (SCA/cupping score, certifications,
    origin, altitude, varietals, process, and tasting notes), and the rendered
    product pages add no unique coffee info beyond echoing that ``body_html``
    along with live price/availability and a Judge.me reviews widget. Fetching
    product pages would therefore yield no extra bean information while wasting
    tokens, so they are skipped.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Caribe Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Caribe",
            base_url="https://caribecoffee.co.uk",
            products_json_urls=["https://caribecoffee.co.uk/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, gift cards, equipment, etc.)
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
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
            # Caribe-specific non-coffee products
            "coffee-van",  # Coffee Van Event hire and the physical coffee vans
            "cookie",  # Specially cookies (baked goods)
            "water-filter",  # Professional water filter and adapter cable
            "blender",  # Buffalo Digital Bar Blender
            "key-ring",  # Apple Air Tag Key Rings
            "coffee-machine",  # Fracino espresso machine
            "knock-box",  # Commercial knock box
            "microfiber",  # Microfiber cloth
            "pitcher",  # Milk frothing pitcher
            "tamper",  # Coffee tamper
            "compostable",  # Compostable coffee cups and lids
            "grinder",  # Cordless coffee grinder
            "measuring-cup",  # Glass measuring cup with wood handle
            "coffee-cup",  # Double wall glass and ceramic coffee cups
            "spoon",  # Coffee spoon and sealing clip
            "cafetiere",  # Cafetiere
            "boiler",  # Marco water boiler
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
