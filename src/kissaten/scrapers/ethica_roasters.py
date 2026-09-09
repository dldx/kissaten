"""Ethica Coffee Roasters scraper implementation with AI-powered extraction.

Ethica Coffee Roasters is a Toronto, ON roaster whose storefront is a
**headless Shopify** build: a Next.js (React Server Components) front-end
backed by Shopify (product images on cdn.shopify.com), deployed on Vercel.
The classic Shopify `products.json` endpoints are **not** exposed (they
return the 404 page), so this scraper follows the non-Shopify shape:

- Product discovery from the server-rendered `/shop` listing.
- Product detail extraction via AI on Playwright-rendered pages (the RSC
  payload only becomes visible DOM after client hydration; plain httpx
  returns the content inside React streaming placeholders).

Coffee listing: https://www.ethicaroasters.com/shop
"""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="ethica-roasters",
    display_name="Ethica Coffee Roasters",
    roaster_name="Ethica Coffee Roasters",
    website="https://ethicaroasters.com",
    description="Toronto-based specialty coffee roaster named after Spinoza's Ethica; "
    "single-origin espressos and filters plus a rotating SPECTRUM series, "
    "roasted at their Sterling Rd roastery-cafe",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class EthicaRoastersScraper(BaseScraper):
    """Scraper for Ethica Coffee Roasters (ethicaroasters.com).

    Headless Shopify (Next.js/RSC) storefront: no products.json endpoint, so
    product URLs come from the /shop listing and details are extracted by AI
    from Playwright-rendered product pages.
    """

    # Non-coffee products sold on the /shop listing (equipment, merch,
    # subscriptions). Substring match against the product handle.
    # Curated sampler/tasting-kit products are NOT excluded — they flow
    # through with is_tasting_kit/requires_review flags for admin review.
    excluded_slugs = [
        "subscription",  # espresso/filter/mixed/gift subscriptions
        "aergrind",  # hand grinder
        "aeropress",  # brewer
        "hario",  # V60 drippers, filters, scales
        "v60",  # dripper + filters
        "fellow",  # Ode/Opus grinders
        "acaia",  # Pearl scale
        "loveramics",  # mug
        "mug",  # drinkware
        "third-wave-water",  # water additives
    ]

    def __init__(self, api_key: str | None = None):
        """Initialize the Ethica Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Ethica Coffee Roasters",
            base_url="https://www.ethicaroasters.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the all-products shop URL
        """
        return ["https://www.ethicaroasters.com/shop"]

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to the product content.

        The rendered product pages still carry React Server Components script
        payload (~300KB) plus footer and "Related Products" sections that the
        AI extractor doesn't need. Stripping scripts/styles and removing the
        footer + related-products section cuts the soup to just the product
        hero (name, price, size variants), description, spec list, and brew
        recipe before it reaches the AI extractor.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object (narrowed for product pages) or None if fetch failed.
        """
        soup = await super().fetch_page(*args, **kwargs)
        url = kwargs.get("url")
        if not url and len(args) > 0:
            url = args[0]

        # Only narrow product detail pages, leave the /shop listing untouched.
        if not url or "/product/" not in url or soup is None:
            return soup

        for tag in soup.find_all(["script", "style", "template", "noscript"]):
            tag.decompose()

        footer = soup.find("footer")
        if footer is not None:
            footer.decompose()

        # Drop the "You Might Also Like / Related Products" section.
        for heading in soup.find_all(["h2", "h3"]):
            if heading.get_text(strip=True).lower() == "related products":
                section = heading.find_parent("section")
                if section is not None:
                    section.decompose()
                break

        # Strip responsive srcset blobs from remaining images (product shot).
        for img in soup.find_all("img"):
            for attr in ("srcset", "sizes"):
                if img.get(attr):
                    del img[attr]

        return soup

    # Sold-out detection: text detection on the product card container.
    # Sold-out products stay listed on /shop with a "Sold Out" badge inside
    # their card div (classes include "group relative bg-ethica-milk"), so we
    # check the card's text before coffee-URL filtering so excluded products
    # don't leak past the stock check.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock coffee bean URLs from the /shop listing.

        Args:
            store_url: URL of the shop listing page

        Returns:
            List of in-stock coffee product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=True)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        for link in soup.select('a[href*="/product/"]'):
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            full_url = self.resolve_url(href.split("?")[0].split("#")[0])

            # Skip sold-out products before URL filtering. Match the exact
            # "group" class — the quick-add hover wrapper carries
            # "group-hover:*" classes that a substring check would match.
            card = link.parent
            while card is not None:
                classes = card.get("class") or []
                if getattr(card, "name", None) == "div" and "group" in classes:
                    break
                card = card.parent
            if card is not None:
                card_text = card.get_text(" ", strip=True).lower()
                if "sold out" in card_text:
                    logger.debug(f"Skipping sold-out product: {full_url}")
                    continue

            # Exclude non-coffee products (equipment, merch, subscriptions).
            handle = full_url.rstrip("/").rsplit("/", 1)[-1].lower()
            if any(slug in handle for slug in self.excluded_slugs):
                logger.debug(f"Excluding non-coffee product: {full_url}")
                continue

            if not self.is_coffee_product_url(full_url, required_path_patterns=["/product/"]):
                continue

            if full_url not in seen:
                seen.add(full_url)
                product_urls.append(full_url)

        logger.info(f"Found {len(product_urls)} in-stock coffee product URLs from {store_url}")
        return product_urls

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using AI extraction on Playwright-rendered pages.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=True,  # RSC storefront: content only in DOM after hydration
            use_optimized_mode=False,
            translate_to_english=False,  # site is English
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin the bean currency to CAD.

        The headless storefront never exposes Shopify.currency in its HTML, and
        BaseScraper's default-currency lookup is keyed by registry name (not
        roaster name), which can silently fall back to GBP — so we pin CAD as a
        final guard.

        Args:
            bean: Extracted CoffeeBean object

        Returns:
            Postprocessed CoffeeBean object
        """
        bean.currency = "CAD"
        return super().postprocess_extracted_bean(bean)
