"""Terarosa Coffee scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="terarosa",
    display_name="Terarosa",
    roaster_name="Terarosa",
    website="https://www.terarosa.com",
    description="Speciality coffee roastery based in South Korea.",
    requires_api_key=True,
    currency="KRW",
    country="South Korea",
    status="available",
)
class TerarosaCoffeeScraper(BaseScraper):
    """Scraper for Terarosa Coffee (terarosa.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Terarosa Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Terarosa",  # Must match registry roaster_name
            base_url="https://www.terarosa.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Discovers the current coffee sub-categories from the ``ol`` inside
        ``div.category.pd_category`` on the listing page, instead of relying
        on a hardcoded list of Korean category names. ``전체보기`` (View All)
        is skipped because it points back at the parent page we just fetched.

        Returns:
            List of category listing URLs.
        """
        homepage = await self.fetch_page(
            "https://www.terarosa.com/product/list/?category=12", use_playwright=True
        )
        if not homepage:
            logger.error("Failed to fetch Terarosa homepage for store URLs")
            return []

        store_urls = []
        for el in homepage.select("div.category.pd_category ol li a"):
            if el.text.strip() == "전체보기":
                continue
            store_urls.append(self.base_url + str(el["href"]))
        return store_urls

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

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
            use_playwright=True,
            use_optimized_mode=True,
            translate_to_english=True,  # Translate Korean content to English
        )

    async def _extract_bean_with_ai(
        self,
        ai_extractor,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> CoffeeBean | None:
        """Run the shared AI extraction on a soup limited to the product card.

        The shared flow serializes ``str(soup)`` and sends it to the model, so
        we prune Terarosa's detail page before delegating (see
        :meth:`preprocess_product_soup`). The full-page screenshot is taken by
        the base flow on the live page and is unaffected by HTML pruning.
        """
        soup = self.preprocess_product_soup(soup)
        return await super()._extract_bean_with_ai(
            ai_extractor,
            soup,
            product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=translate_to_english,
        )

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Limit the Terarosa product page soup to the product card.

        Terarosa detail pages are server-rendered with a fixed wrapper:
        ``div.cont_wrap.product_view_wrap > div.product_view >
        div.product_view_box``. The bean facts (Korean/English title, tasting
        tagline, price, weight/grind options) live in
        ``div.product_view_box > div.cont``, which also carries the
        product-photo carousel. The origin spec sheet (country, region,
        producer, altitude, process, variety) is delivered *as product photos*
        rather than text, which is why extraction relies on the full-page
        screenshot in optimized mode - those photos are unaffected by pruning.

        Everything else on the page repeats verbatim on every product or adds
        no facts: the header nav, the purchase/shipping guide
        (``div.product_view_cont_reivew``), the empty AJAX detail container
        (``div.product_view_cont``), the review widgets, the recommended
        carousels, inline chat/social scripts and the footer. Those are dropped
        here; :meth:`_prune_soup_for_ai` strips the remaining markup. If the
        theme changes and no product container is found we fall back to the
        full page so extraction never silently loses data.
        """
        box = soup.select_one("div.product_view_box")
        if box is None:
            box = soup.select_one("div.product_view") or soup.select_one(
                "div.product_view_wrap"
            )
        if box is None:
            logger.debug("No Terarosa product container found; sending full page soup.")
            return soup

        for sel in (
            "div.product_view_cont_reivew",  # purchase/shipping/review boilerplate
            "div.product_view_cont_tab",     # review/inquiry tab labels
            "div.product_view_cont",         # empty AJAX detail container
            "div.product_view_navi",         # breadcrumb
            "div.pagination",                # review pagination
        ):
            for el in box.select(sel):
                el.decompose()

        limited = BeautifulSoup("<html><body></body></html>", "lxml")
        limited.body.append(box)
        self._prune_soup_for_ai(limited)
        logger.debug(
            f"Sending Terarosa product soup limited to {len(str(limited))} chars "
            "for AI extraction."
        )
        return limited

    def _prune_soup_for_ai(self, soup: BeautifulSoup) -> None:
        """Remove markup that adds size but no bean facts.

        Terarosa ships long ``class``/``data-*`` attribute strings, inline
        scripts and SVG icons; the model only needs text + nesting. Attributes
        are stripped, hidden containers, form inputs and empty wrappers are
        dropped. The product photos are KEPT (as ``<img>`` with only ``src``
        kept) because the origin spec sheet is image-based and is read via the
        screenshot; variation ``<select>``/``<option>`` texts are kept too
        (they carry the weight/grind facts).
        """
        # 1) Pull <img> out of <picture> (lxml nests <img> inside <source>),
        #    then drop picture/source markup and non-visual elements.
        for pic in soup.find_all("picture"):
            img = pic.find("img")
            if img is not None:
                img.extract()
                pic.insert_before(img)
            pic.decompose()
        for name in (
            "script",
            "style",
            "noscript",
            "template",
            "link",
            "meta",
            "svg",
            "path",
            "circle",
            "iframe",
        ):
            for tag in soup.find_all(name):
                tag.decompose()

        # 2) Hidden containers (JS mirror / popup chrome).
        for tag in soup.find_all(True):
            style = tag.get("style") or ""
            if "display:none" in style.replace(" ", ""):
                tag.decompose()

        # 3) Form inputs carry no text facts (quantity, CSRF, reach inputs).
        for tag in soup.find_all("input"):
            tag.decompose()

        # 4) Keep images (they encode the spec sheet); keep only src (and alt).
        for img in soup.find_all("img"):
            src = img.get("src") or ""
            alt = img.get("alt") or ""
            img.attrs.clear()
            if src:
                img["src"] = src
            if alt:
                img["alt"] = alt

        # 5) Attribute noise: the model needs text + nesting only.
        for tag in soup.find_all(True):
            if tag.name != "img":
                tag.attrs.clear()

        # 6) Collapse now-empty wrappers.
        changed = True
        while changed:
            changed = False
            for tag in soup.find_all(True):
                if tag.name in (
                    "html",
                    "head",
                    "body",
                    "div",
                    "span",
                    "p",
                    "ul",
                    "li",
                    "a",
                    "table",
                    "tbody",
                    "tr",
                    "td",
                    "th",
                    "form",
                    "select",
                    "option",
                    "label",
                    "h1",
                    "h2",
                    "h3",
                    "h4",
                    "h5",
                    "h6",
                    "em",
                    "strong",
                    "picture",
                ):
                    if not tag.get_text("", strip=True) and not tag.find("img"):
                        tag.decompose()
                        changed = True

    def _is_non_coffee_accessory(self, name: str) -> bool:
        """Return True for a grid item name that is *not* a coffee product.

        The category grids are injected with non-coffee accessories (a
        shopping bag appears on every category page, an Oxford collectible
        block, etc.). Those items extract fine but carry no origin info, so
        the base flow rejects them (no country/process/variety) and, because
        they are never saved, re-scrapes them on every run, every overlapping
        category - burning a flash+screenshot call each time.

        The rule is conservative: an item is dropped only when it has an
        accessory keyword AND no coffee keyword. So a drip-bag set whose name
        also mentions "옥스포드 블록" (:ref:`100315` style) is kept, while the
        pure shopping bag / collectible block is dropped.
        """
        if not name:
            return False
        n = name.lower()
        coffee_hint = any(
            k in n
            for k in (
                "드립백", "커피", "원두", "블렌드",
                "coffee", "bean", "blend", "drip", "espresso",
            )
        )
        if coffee_hint:
            return False
        accessory_hint = any(
            k in n
            for k in (
                "쇼핑백", "선물", "포장", "상자", "틴케이스", "아이스크림", "블록",
                "bag", "gift", "wrap", "box", "block", "oxford", "ice cream", "tin",
            )
        )
        return accessory_hint

    async def take_screenshot(self, url: str, full_page: bool = True) -> bytes | None:
        """Take a full-page screenshot after triggering lazy-loaded assets.

        The base method screenshots after a short wait without scrolling, so
        everything below the fold (Terarosa ships its product/detail photos
        with ``loading="lazy"``) is blank or truncated in the capture - the
        origin spec sheet ends up cut off. Before capturing we scroll through
        the page to force the browser to load every image, then scroll back to
        the top (same fix as ``pala_kaffebrenneri``).
        """
        browser = await self._get_browser()
        page = await browser.new_page()

        try:
            signed_headers = self.get_signed_headers(url)
            headers_to_set = {**self.headers, **signed_headers}
            await page.set_extra_http_headers(headers_to_set)

            response = await page.goto(
                url, timeout=self.timeout * 1000, wait_until="domcontentloaded"
            )
            if not response or not response.ok:
                raise Exception(
                    f"Failed to load page: {response.status if response else 'No response'}"
                )

            # A small initial pause for dynamic content, then walk the page
            # (top -> bottom in intermediate steps) so every lazy image is
            # fetched, then wait for all images to finish decoding.
            await page.wait_for_timeout(1500)
            await page.evaluate(
                "async () => {"
                " for (let y = 0; y <= document.body.scrollHeight; y += 700) {"
                "  window.scrollTo(0, y);"
                "  await new Promise(r => setTimeout(r, 80));"
                " }"
                " window.scrollTo(0, 0);"
                "}"
            )
            try:
                await page.wait_for_function(
                    "() => Array.from(document.images).every(i => i.complete)",
                    timeout=15000,
                )
            except Exception:
                logger.debug("Timed out waiting for all images to load; continuing.")
            await page.wait_for_timeout(500)

            return await page.screenshot(full_page=full_page, type="png")

        except Exception as e:
            logger.error(f"Failed to take screenshot of {url}: {e}")
            return None

        finally:
            await page.close()

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page, skipping non-coffee items.

        Args:
            store_url: URL of the store page

        Returns:
            List of coffee product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=True)
        if not soup:
            return []

        # The product grid is <ul id="itemList" class="productBox">; each
        # product <li> carries a wishlist <a data-key="ItemCode">. Using
        # data-key (rather than the old goView onclick) avoids duplicates
        # (the image and the info card each render their own onclick). The
        # item name lives in the sibling info card (.cont_title.text_row2 /
        # .cont_title_en.text_row1) and is used to drop non-coffee accessories
        # (shopping bag, collectible block) before they reach the AI extractor.
        product_urls = []
        for a in soup.select("#itemList a[data-key]"):
            code = a.get("data-key")
            if not code:
                continue
            name = ""
            li = a.find_parent("li")
            if li is not None:
                name_el = li.select_one(
                    ".cont_title.text_row2, .cont_title_en.text_row1"
                )
                if name_el is not None:
                    name = name_el.get_text(" ", strip=True)
            if self._is_non_coffee_accessory(name):
                logger.info(f"Skipping non-coffee accessory ItemCode={code}: {name}")
                continue
            product_urls.append(
                f"https://www.terarosa.com/product/detail/?ItemCode={code}"
            )

        logger.info(f"Found {len(product_urls)} coffee product URLs from {store_url}")
        return product_urls
