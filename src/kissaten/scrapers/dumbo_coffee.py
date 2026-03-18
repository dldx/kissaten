"""Dumbo Coffee scraper implementation with AI-powered extraction."""

import hashlib
import logging
import re

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="dumbo",
    display_name="Dumbo Coffee",
    roaster_name="Coffee Dumbo",
    website="https://www.coffeedumbo.tw",
    description="Taiwan-based specialty coffee roaster with Chinese and English options",
    requires_api_key=True,
    currency="GBP",  # They use GBP on their site
    country="Taiwan",
    status="available",
)
class DumboCoffeeScraper(BaseScraper):
    """Scraper for Dumbo Coffee (coffeedumbo.tw) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Dumbo Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coffee Dumbo",
            base_url="https://www.coffeedumbo.tw",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URL for coffee beans
        """
        return ["https://www.coffeedumbo.tw/categories/%E5%92%96%E5%95%A1%E8%B1%86?limit=72"]

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction with optimized mode.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """

        # Create a function that returns the product URLs for the AI extraction
        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=True,  # Use Playwright for screenshot support
            use_optimized_mode=True,  # Use optimized mode for complex layouts
            translate_to_english=False,  # Enable translation for Taiwan-based content
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page, filtering out sold-out products.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs (excluding sold-out products)
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls = []

        # Find all product containers in Shopline
        # Usually each product is in a div with a class like "product-item"
        # We search for the <a> links inside them
        product_links = soup.select('a[href*="/products/"]')

        for link in product_links:
            href = link.get("href")
            if not href:
                continue

            # Skip duplicate links for the same product in the same card
            full_url = self.resolve_url(href).split("?")[0]

            # Extract name and image from the product card for disambiguation
            # This logic should match the cleanup script hash generation
            product_card = link.find_parent(
                class_=lambda x: x and any(k in str(x).lower() for k in ["product", "item", "card"])
            )

            product_name = ""
            image_url = ""

            if product_card:
                # Name is usually in a div with "title" or "name" or in the link text
                name_el = product_card.select_one('[class*="title"], [class*="name"]')
                if name_el:
                    product_name = name_el.get_text(strip=True)
                else:
                    product_name = link.get_text(strip=True)

                # Image
                img_el = product_card.find("img")
                if img_el:
                    image_url = img_el.get("src") or img_el.get("data-src", "")

            # If we couldn't find a name/image in the card, fallback to link content
            if not product_name:
                product_name = link.get_text(strip=True)

            # Generate version hash
            version_id = self._generate_version_hash(product_name, image_url)
            full_url_with_hash = f"{full_url}#{version_id}"

            # Check if this product is sold out
            is_sold_out = self._check_if_sold_out(link)

            if is_sold_out:
                logger.debug(f"Skipping sold-out product: {full_url_with_hash}")
                continue

            # Apply standard coffee product filtering
            if self.is_coffee_product_url(full_url, ["/products/"]):
                product_urls.append(full_url_with_hash)

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} in-stock product URLs from {store_url}")
        return unique_urls

    def _generate_version_hash(self, name: str, image_url: str) -> str:
        """Generate a version hash for a bean based on its name and image ID."""

        def normalize_name(n):
            if not n:
                return ""
            n = n.lower().strip()
            n = re.sub(r"[^\w\s]", "", n)
            return " ".join(n.split())

        def normalize_img(u):
            if not u:
                return ""
            ids = re.findall(r"([a-f0-9]{24})", u)
            return ids[-1] if ids else ""

        norm_name = normalize_name(name)
        image_id = normalize_img(image_url)
        combined = f"{norm_name}:{image_id}"
        return hashlib.sha256(combined.encode()).hexdigest()[:8]

    def _check_if_sold_out(self, link_element) -> bool:
        """Check if a product link represents a sold-out product.

        Args:
            link_element: BeautifulSoup element representing the product link

        Returns:
            True if the product is sold out, False otherwise
        """
        try:
            # Navigate two children below the <a> tag to find the div with "out-of-stock" class
            # This could be implemented in multiple ways depending on the exact HTML structure

            # Method 1: Check if the link's parent or siblings contain out-of-stock indicators
            parent = link_element.parent
            if parent:
                # Look for out-of-stock class in the parent container
                if parent.find(class_="out-of-stock"):
                    return True

                # Look for out-of-stock class in siblings
                for sibling in parent.find_all():
                    if "out-of-stock" in sibling.get("class", []):
                        return True

            # Method 2: Look for out-of-stock class in children/descendants of the link's container
            # Find the container that holds the product info
            product_container = link_element.find_parent(
                class_=lambda x: x and any(keyword in str(x).lower() for keyword in ["product", "item", "card"])
            )

            if product_container:
                # Look for out-of-stock indicators in the product container
                out_of_stock_element = product_container.find(class_="out-of-stock")
                if out_of_stock_element:
                    return True

            # Method 3: Check specific structure - div two children below the <a>
            # This assumes a specific HTML structure that may need adjustment
            if link_element.parent and link_element.parent.parent:
                grandparent = link_element.parent.parent
                for div in grandparent.find_all("div", class_="out-of-stock"):
                    return True

            return False

        except Exception as e:
            logger.debug(f"Error checking sold-out status: {e}")
            # If we can't determine the status, assume it's in stock to avoid missing products
            return False
