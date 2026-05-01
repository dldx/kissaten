"""Skinny Dip Coffee scraper implementation using Playwright."""

import logging
import re
from pathlib import Path

from pydantic import HttpUrl

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="skinnydip",
    display_name="Skinny Dip Coffee",
    roaster_name="Skinny Dip Coffee",
    website="https://www.skinnydipcoffee.co.uk",
    description="Specialty coffee roaster based in Margate, UK",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SkinnyDipCoffeeScraper(BaseScraper):
    """Scraper for Skinny Dip Coffee using Playwright to handle Subbly CMS."""

    def __init__(self, api_key: str | None = None):
        """Initialize Skinny Dip Coffee scraper.

        Args:
            api_key: AI service API key for extraction.
        """
        super().__init__(
            roaster_name="Skinny Dip Coffee",
            base_url="https://www.skinnydipcoffee.co.uk",
        )
        self.buy_url = "https://www.skinnydipcoffee.co.uk/buy-coffee"

        from ..ai.extractor import CoffeeDataExtractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def scrape(self, output_dir: str | Path | None = None, force_full_update: bool = False, create_diffjson_updates: bool = True) -> list[CoffeeBean]:
        """Scrape Skinny Dip Coffee beans."""
        self.start_session()
        beans = []

        if output_dir is None:
            output_dir = Path("data")
        else:
            output_dir = Path(output_dir)

        # Load existing beans to avoid re-scraping the same products in the same session
        self._load_existing_beans_for_session(output_dir)

        try:
            # Load historical beans to check for existing ones
            self._load_existing_beans_from_all_sessions(output_dir)

            # Use BaseScraper's Playwright integration
            soup = await self.fetch_page(self.buy_url, use_playwright=True)

            if not soup:
                logger.error(f"Failed to fetch {self.buy_url}")
                self.end_session(success=False)
                return []

            # Extract product rows
            product_rows = soup.select(".uc-row-wrapper")

            for row in product_rows:
                # Check for title
                title_el = row.select_one("h3")
                if not title_el:
                    continue

                name = title_el.get_text().strip()

                # Exclude non-coffee items
                if name.upper() in ["USUAL", "CURIOUS", "IMPOSSIBLE", "VISIT US"]:
                    continue

                # Build unique URL from raw title BEFORE AI extraction
                slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
                unique_url = f"{self.buy_url}#{slug}"

                # Exclude specific slugs
                excluded_slugs = ["test-roast"]
                if any(excluded in slug for excluded in excluded_slugs):
                    logger.debug(f"Skipping excluded slug: {slug}")
                    continue

                # Check if already scraped in this session
                if self._is_bean_already_scraped_in_session(unique_url):
                    logger.info(f"Skipping already scraped bean: {name}")
                    continue

                # If not forcing full update, skip existing products
                if not force_full_update and create_diffjson_updates:
                    if self._is_bean_already_scraped_historically(unique_url):
                        logger.debug(f"Skipping existing product: {name}")
                        continue

                # Use AI extractor for each bean if available
                row_html = str(row)
                bean = await self.ai_extractor.extract_coffee_data(
                    html_content=row_html,
                    product_url=self.buy_url,
                    default_currency="GBP",
                    use_one_shot_mode=True
                )

                if bean:
                    # Enrich/fix roaster and URL with slug to differentiate products on same page
                    bean.roaster = self.roaster_name
                    bean.url = HttpUrl(unique_url)

                    # Select "middle image" if multiple images exist in this row
                    imgs = row.select("img")
                    if len(imgs) >= 3:
                        # Middle of 3 is index 1
                        middle_idx = len(imgs) // 2
                        image_url = imgs[middle_idx].get("src")
                        if image_url:
                            # Handle relative URLs just in case
                            if image_url.startswith("//"):
                                image_url = f"https:{image_url}"
                            elif image_url.startswith("/"):
                                image_url = f"{self.base_url}{image_url}"
                            bean.image_url = HttpUrl(image_url)

                    # Download and save image like BaseScraper.save_bean_with_image
                    await self.save_bean_with_image(bean, output_dir)
                    self._mark_bean_as_scraped(unique_url)
                    beans.append(bean)

            # Mark session as successful if we found beans
            if beans:
                self.end_session(success=True)
            else:
                self.end_session(success=False)
            return beans
        except Exception as e:
            logger.exception(f"Scrape failed: {e}")
            self.end_session(success=False)
            return []
    async def get_store_urls(self) -> list[str]:
        """Get list of store URLs to scrape. Not used since we override scrape."""
        return [self.buy_url]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs. Not used since we override scrape."""
        return []