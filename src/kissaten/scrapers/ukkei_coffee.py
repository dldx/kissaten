"""Ukkei Coffee scraper implementation with AI-powered extraction (BigCommerce)."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean, CoffeeBeanDiffUpdate
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="ukkei-coffee",
    display_name="Ukkei",
    roaster_name="Ukkei",
    website="https://ukkei.co.uk",
    description="Specialty coffee roaster based in London, with a focus on connection and community. Ukkei means home in Cantonese.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class UkkeiCoffeeScraper(BaseScraper):
    """Scraper for Ukkei (ukkei.co.uk) with AI-powered extraction.

    Ukkei is a BigCommerce storefront that moves sold-out beans to a separate
    ``/shop/archive/`` page. We crawl both the main shop listing and the archive
    pages so that past beans are added to the database on the first run. Archive
    beans are marked ``in_stock=False`` — both in the initial AI extraction (via
    ``postprocess_extracted_bean``) and in subsequent-run diffjson updates (via
    the ``_create_stock_updates`` override).
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Ukkei scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Ukkei",
            base_url="https://ukkei.co.uk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # Track which product URLs came from the archive pages. Populated in
        # _extract_product_urls_from_store and consumed in postprocess_extracted_bean
        # and _create_stock_updates to force in_stock=False for sold-out beans.
        self._archive_urls: set[str] = set()

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Ukkei moves sold-out beans to ``/shop/archive/`` (paginated, 2 pages).
        We crawl both the main shop listing and the archive so that past beans
        are added to the database. On subsequent runs, archive beans are already
        scraped and receive ``in_stock=False`` diffjson updates (not re-extracted).

        Returns:
            List containing the in-stock shop URL and both archive page URLs.
        """
        return [
            "https://ukkei.co.uk/shop/",
            "https://ukkei.co.uk/shop/archive/?page=1",
            "https://ukkei.co.uk/shop/archive/?page=2",
        ]

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

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
            use_playwright=False,
            use_optimized_mode=False,
            translate_to_english=False,
        )

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to the BigCommerce product container.

        BigCommerce (Stencil theme) product detail pages wrap all useful content
        (title, price, description, image, variants) inside ``div.productView``.
        Narrowing the soup to that container strips nav, footer, related-product
        carousels and JSON blobs before the HTML is sent to the AI extractor,
        reducing token cost with zero information loss (~88KB -> ~30KB).

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object (narrowed for product detail pages) or None if fetch failed.
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]
            if soup is None:
                return None
            # Only narrow on actual product detail pages — leave listing/category
            # pages untouched so _extract_product_urls_from_store still sees the cards.
            if url and "/shop" in url:
                return soup
            product_el = soup.select("div.productView")
            if len(product_el) == 1:
                logger.debug(f"Narrowed soup to div.productView for {url}")
                return product_el[0]
            logger.debug(f"No single div.productView for {url} (found {len(product_el)}); returning full soup")
            return soup
        except Exception as e:
            logger.error(f"Error fetching page: {e}")
            return None

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Force in_stock=False for beans extracted from the archive pages.

        The AI extractor's prompt checks for "out of stock" text, but Ukkei's
        product pages show "Sold Out" instead. The AI may miss this, so we
        explicitly force in_stock=False for any bean whose URL was extracted
        from an archive page.

        Args:
            bean: Extracted CoffeeBean object

        Returns:
            CoffeeBean with in_stock=False if from archive, otherwise unchanged
        """
        bean_url = str(bean.url) if bean.url else ""
        if bean_url in self._archive_urls:
            bean.in_stock = False
            logger.debug(f"Marked archive bean as out of stock: {bean.name}")
        return bean

    # Sold-out detection: site-level separation + _create_stock_updates override.
    # Ukkei moves sold-out beans to /shop/archive/ (separate listing). We crawl
    # both listings but track which URLs came from the archive so that:
    # 1. _extract_product_urls_from_store skips the sold-out filter for archive
    #    pages (we WANT the sold-out beans to pass through).
    # 2. postprocess_extracted_bean forces in_stock=False on first-run extraction.
    # 3. _create_stock_updates creates in_stock=False diffjson on subsequent runs.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from a BigCommerce shop or archive listing page.

        For the main shop listing (``/shop/``), sold-out cards are skipped. For
        archive pages (``/shop/archive/``), sold-out cards are included and their
        URLs are recorded in ``self._archive_urls`` for downstream stock-status
        handling.

        Ukkei's BigCommerce theme lists products as ``article.card`` elements
        whose links point to root-level slugs (``https://ukkei.co.uk/<slug>/``).
        Because product URLs lack a ``/product/`` or ``/products/`` path segment,
        ``is_coffee_product_url``'s default path patterns would reject every URL;
        we therefore rely on the ``article.card`` selector itself as the product
        signal and apply ``is_coffee_product_name`` to the card title to filter
        out non-coffee items (equipment, bundles, merch, etc.).

        Args:
            store_url: URL of the shop or archive listing page

        Returns:
            List of product URLs (in-stock from /shop/, sold-out from /shop/archive/)
        """
        is_archive = "/shop/archive/" in store_url

        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        for card in soup.select("article.card"):
            link = card.find("a", href=True)
            if not link:
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            full_url = self.resolve_url(href.split("?")[0].split("#")[0])

            # Filter non-coffee items by card title (equipment, bundles, subscriptions)
            name_el = card.select_one(".card-title, .card-found-title, h2, h3, h4")
            if name_el:
                card_name = name_el.get_text(strip=True)
                # Strip "(Sold Out)" suffix for name filtering so the coffee check sees the real name
                clean_name = card_name.replace("(Sold Out)", "").strip()
                if not self.is_coffee_product_name(clean_name):
                    logger.debug(f"Skipping non-coffee card: {card_name!r}")
                    continue
                # Extra exclusion: bundles aren't coffee beans
                if "bundle" in card_name.lower():
                    logger.debug(f"Skipping bundle card: {card_name!r}")
                    continue

            if not is_archive:
                # Main shop listing: skip sold-out products (defense-in-depth)
                card_text = card.get_text(" ", strip=True)
                if "Sold Out" in card_text or "Sold out" in card_text or "sold-out" in full_url.lower():
                    logger.debug(f"Skipping sold-out product on shop listing: {full_url}")
                    continue

            # Archive listing: include sold-out beans and track them
            if is_archive:
                self._archive_urls.add(full_url)

            if full_url not in seen:
                seen.add(full_url)
                product_urls.append(full_url)

        logger.info(
            f"Found {len(product_urls)} product URLs from {store_url} "
            f"({'archive' if is_archive else 'in-stock listing'})"
        )
        return product_urls

    async def _create_stock_updates(self, product_urls: list[str], output_dir: Path) -> None:
        """Create diffjson stock updates, marking archive beans as out of stock.

        Overrides the base class method to set ``in_stock=False`` for any URL
        that was extracted from an archive page (tracked in
        ``self._archive_urls``). This ensures that on subsequent runs, already-
        scraped archive beans receive correct out-of-stock diffjson instead of
        the default in_stock=True.

        Args:
            product_urls: List of product URLs to create stock updates for
            output_dir: Base output directory
        """
        if not product_urls:
            return

        logger.info(f"Creating stock updates for {len(product_urls)} existing products")

        session_datetime = self.session_datetime or datetime.now().strftime("%Y%m%d")
        bean_dir = output_dir / "roasters" / self._get_roaster_dir_name() / session_datetime
        bean_dir.mkdir(parents=True, exist_ok=True)

        for url in product_urls:
            try:
                is_archive = url in self._archive_urls
                update_data = {
                    "url": str(url),
                    "in_stock": not is_archive,  # False for archive (sold out) beans
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "scraper_version": "2.0",
                }

                # Validate using Pydantic schema
                CoffeeBeanDiffUpdate.model_validate(update_data)

                # Generate filename based on URL
                filename = self._generate_diffjson_filename(str(url))
                output_path = bean_dir / f"{filename}.diffjson"

                # Save diffjson file
                with open(output_path, "w") as f:
                    json.dump(update_data, f, indent=2)

                logger.debug(f"Created stock update: {output_path} (in_stock={not is_archive})")

            except Exception as e:
                logger.error(f"Failed to create stock update for {url}: {e}")
