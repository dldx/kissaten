"""Scraper for The Naughty Dog Coffee Roasters (Czech Republic).

All coffee product data (country, process, tasting notes, etc.) lives on a
single landing page with per‑item Bootstrap modals embedded directly in the
HTML. We can therefore scrape everything in one request without AI / LLM.
"""

from __future__ import annotations

import asyncio
import csv
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from pydantic import HttpUrl

from kissaten.schemas.coffee_bean import Bean, CoffeeBean

from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


def _load_country_codes() -> dict[str, str]:
    """Load country name to code mapping from CSV file."""
    country_mapping = {}
    csv_path = Path(__file__).parent.parent / "database" / "countrycodes.csv"

    try:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                country_name = row["name"].strip().lower()
                country_code = row["alpha-2"].strip()
                country_mapping[country_name] = country_code
    except FileNotFoundError:
        logger.warning(f"Country codes CSV not found at {csv_path}")
    except Exception as e:
        logger.warning(f"Error loading country codes: {e}")

    return country_mapping


def map_country(name: str | None) -> str | None:
    if not name:
        return None
    key = name.strip().lower()
    country_codes = _load_country_codes()
    return country_codes.get(key, None)


@register_scraper(
    name="naughty-dog",
    display_name="The Naughty Dog",
    roaster_name="The Naughty Dog",
    website="https://www.thenaughtydog.cz",
    description="Single page scraper parsing embedded modals (no AI)",
    requires_api_key=False,
    currency="CZK",
    country="Czechia",
    status="available",
)
class NaughtyDogScraper(BaseScraper):
    """Scraper implementation for The Naughty Dog."""

    def __init__(self, output_dir: str | Path | None = None):
        super().__init__(
            roaster_name="The Naughty Dog",
            base_url="https://www.thenaughtydog.cz",
            rate_limit_delay=0.5,
            max_retries=2,
            timeout=30.0,
        )
        self.output_dir = Path(output_dir) if output_dir else Path("data")

    # BaseScraper requires these abstract methods
    async def get_store_urls(self) -> list[str]:  # pragma: no cover - simple
        return [self.base_url]

    async def scrape(
        self,
        *,
        force_full_update: bool = False,
    ) -> list[CoffeeBean]:
        """Scrape all coffee beans from the single landing page, supporting diffjson updates."""
        self.start_session()
        beans: list[CoffeeBean] = []

        try:
            html = await self._fetch_main()
            if not html:
                logger.error("Empty HTML fetched")
                self.end_session(False)
                return []

            soup = BeautifulSoup(html, "lxml")
            articles = soup.select("article.portfolio-item")
            logger.info(f"Found {len(articles)} potential products")

            # Efficient diffjson update logic
            if not force_full_update:
                beans = await self._scrape_new_products(soup, articles, force_full_update)
            else:
                for art in articles:
                    bean = self._parse_article(soup, art)
                    if bean:
                        beans.append(bean)
                        try:
                            await self.save_bean_with_image(bean, self.output_dir)
                        except Exception as e:
                            logger.warning(f"Failed to save bean {bean.name}: {e}")
                    await asyncio.sleep(self.rate_limit_delay)

            if self.session:
                self.session.beans_found = len(beans)
                self.session.beans_processed = len(beans)
            self.end_session(True)
            return beans
        except Exception as e:
            logger.exception("Scrape failed: %s", e)
            if self.session:
                self.session.add_error(str(e))
            self.end_session(False)
            return []

    async def _scrape_new_products(self, soup, articles, force_full_update):
        """Efficiently scrape new products and update diffjson stock."""
        # Load previous product URLs from historical sessions
        output_dir = self.output_dir
        self._load_existing_beans_from_all_sessions(output_dir)
        previous_urls = set(self._all_sessions_bean_files)

        beans: list[CoffeeBean] = []
        new_urls = set()
        url_to_bean = {}
        for art in articles:
            bean = self._parse_article(soup, art)
            if bean:
                # Use the product URL as the unique key
                url = bean.url if isinstance(bean.url, str) else str(bean.url)
                new_urls.add(url)
                url_to_bean[url] = bean
                if force_full_update or url not in previous_urls:
                    beans.append(bean)
                    try:
                        await self.save_bean_with_image(bean, output_dir)
                    except Exception as e:
                        logger.warning(f"Failed to save bean {bean.name}: {e}")
            await asyncio.sleep(self.rate_limit_delay)

        # Create diffjson stock updates for all products currently in stock
        in_stock_count, out_of_stock_count = await self.create_diffjson_stock_updates(
            list(new_urls), output_dir=output_dir, force_full_update=force_full_update
        )
        logger.info(f"Diffjson stock updates: {in_stock_count} in stock, {out_of_stock_count} out of stock")
        return beans

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    async def _fetch_main(self) -> str | None:
        for attempt in range(self.max_retries):
            try:
                resp = await self.client.get(self.base_url)
                resp.raise_for_status()
                return resp.text
            except httpx.HTTPError as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(2**attempt)
        return None

    def _parse_article(self, page_soup: BeautifulSoup, article) -> CoffeeBean | None:
        try:
            desc = article.find("div", class_="portfolio-desc")
            if not desc:
                return None

            name_el = desc.find("h3")
            if not name_el:
                return None
            name = name_el.get_text(strip=True).title()

            spans = [s.get_text(strip=True) for s in desc.find_all("span") if s.get_text(strip=True)]
            country_text = spans[0] if spans else ""
            process_text = spans[1] if len(spans) > 1 else ""

            img_el = article.find("img")
            image_url = urljoin(self.base_url, img_el["src"]) if img_el and img_el.get("src") else None

            # Modal lookup via data-bs-target on overlay div
            overlay = article.find("div", class_="bg-overlay")
            modal_class = None
            if overlay and overlay.get("data-bs-target"):
                modal_class = overlay["data-bs-target"].lstrip(".")

            modal = None
            if modal_class:
                # Use CSS selector for reliability
                modal = page_soup.select_one(f"div.modal.{modal_class}")

            details = self._extract_details_from_modal(modal) if modal else {}

            countries_raw = details.get("origin") or country_text
            countries = self._split_countries(countries_raw)

            process_full = " ".join((details.get("process") or process_text or "").strip().split()) or None
            usage = details.get("usage") or ""
            tasting_notes_text = details.get("taste profile") or ""
            region = details.get("region")
            farm = details.get("farm/er") or details.get("farm")
            variety_text = details.get("variety") or ""
            altitude_text = details.get("altitude") or ""
            harvest_text = details.get("harvest") or ""
            packaging = details.get("avalaible packaging") or details.get("available packaging") or ""

            weight = self._first_weight(packaging)

            origin_beans: list[Bean] = []
            if len(countries) == 1:
                elevation_val = self._elevation(altitude_text)
                origin_beans.append(
                    Bean(
                        country=map_country(countries[0]),
                        region=region or None,
                        producer=None,
                        farm=farm or None,
                        elevation_min=elevation_val,
                        elevation_max=elevation_val,
                        latitude=None,
                        longitude=None,
                        process=process_full,
                        variety=self._varieties(variety_text),
                        harvest_date=self._harvest(harvest_text),
                    )
                )
                is_single = True
            else:
                processes = [p.strip() for p in process_full.split(",")] if process_full else [None]
                farms = [f.strip() for f in farm.split(",")] if farm else [None]
                varieties = [v.strip() for v in variety_text.split(",")] if variety_text else [None]

                for i, c in enumerate(countries):
                    origin_beans.append(
                        Bean(
                            country=map_country(c),
                            region=None,
                            producer=None,
                            farm=farms[i] if len(farms) > i else farm or None,
                            elevation_min=0,
                            elevation_max=0,
                            latitude=None,
                            longitude=None,
                            process=processes[i] if len(processes) > i else process_full,
                            variety=varieties[i] if len(varieties) > i else self._varieties(variety_text),
                            harvest_date=None,
                        )
                    )
                is_single = False

            roast_profile = self._roast_profile(usage)

            notes = self._tasting_notes(tasting_notes_text)

            bean = CoffeeBean(
                name=name,
                roaster=self.roaster_name,
                url=cast(HttpUrl, self.base_url + "#" + name.replace(" ", "-").lower()),  # satisfy type checker
                image_url=cast(HttpUrl, image_url) if image_url else None,
                origins=origin_beans,
                is_single_origin=is_single,
                roast_level=None,
                roast_profile=cast(Literal["Espresso", "Filter", "Omni"], roast_profile) if roast_profile else None,
                weight=weight,
                price=None,
                currency="CZK",
                is_decaf="decaf" in name.lower(),
                tasting_notes=notes,
                description=None,
                in_stock=True,
                price_paid_for_green_coffee=None,
                currency_of_price_paid_for_green_coffee=None,
                cupping_score=None,
                scraper_version="1.0",
                raw_data=None,
            )
            return bean
        except Exception as e:  # pragma: no cover - defensive
            logger.debug(f"Failed to parse article: {e}")
            return None

    # Parsing helpers --------------------------------------------------
    def _split_countries(self, text: str) -> list[str]:
        if not text:
            return []
        parts = re.split(r"\s*&\s*|\s+and\s+", text, flags=re.IGNORECASE)
        return [p.strip() for p in parts if p.strip()]

    def _elevation(self, text: str) -> int:
        if not text:
            return 0
        nums = re.findall(r"[\d.]+", text)
        if not nums:
            return 0
        primary = nums[0].replace(".", "")
        try:
            return int(primary)
        except ValueError:
            return 0

    def _harvest(self, text: str) -> datetime | None:
        if not text:
            return None
        m = re.search(r"(20\d{2})", text)
        if not m:
            return None
        year = int(m.group(1))
        month_map = {
            m: i
            for i, m in enumerate(
                [
                    "january",
                    "february",
                    "march",
                    "april",
                    "may",
                    "june",
                    "july",
                    "august",
                    "september",
                    "october",
                    "november",
                    "december",
                ],
                start=1,
            )
        }
        tl = text.lower()
        for name, num in month_map.items():
            if name in tl:
                return datetime(year, num, 1, tzinfo=timezone.utc)
        return datetime(year, 1, 1, tzinfo=timezone.utc)

    def _varieties(self, text: str) -> str | None:
        if not text:
            return None
        parts = [p.strip() for p in text.split(",") if p.strip()]
        return ", ".join(parts) if parts else None

    def _tasting_notes(self, text: str) -> list[str | tuple[int, str]]:
        if not text:
            return []
        notes = [n.strip().title() for n in text.split(",") if n.strip()]
        seen = set()
        out: list[str] = []
        for n in notes:
            if n not in seen:
                seen.add(n)
                out.append(n)
        return out  # type: ignore[return-value]

    def _roast_profile(self, usage: str) -> Literal["Espresso", "Filter", "Omni"] | None:
        u = usage.lower()
        if "omni" in u:
            return "Omni"
        if "espresso" in u:
            return "Espresso"
        if "filter" in u:
            return "Filter"
        return None

    def _first_weight(self, packaging: str) -> int | None:
        if not packaging:
            return None
        m = re.search(r"(\d{2,4})\s*g", packaging.lower())
        if m:
            try:
                val = int(m.group(1))
                if 50 <= val <= 10000:
                    return val
            except ValueError:
                return None
        return None

    def _extract_details_from_modal(self, modal) -> dict[str, str]:
        data: dict[str, str] = {}
        if not modal:
            return data
        rows = modal.find_all("tr")
        for r in rows:
            tds = r.find_all("td")
            if len(tds) >= 2:
                key = tds[0].get_text(strip=True).lower()
                val = tds[1].get_text(separator=" ", strip=True)
                data[key] = val
        return data

    # Optional convenience
    async def save_all_beans(self, output_dir: Path | None = None) -> list[Path]:
        if output_dir is None:
            output_dir = Path("data")
        beans = await self.scrape()
        saved: list[Path] = []
        for b in beans:
            try:
                json_path, img_path = await self.save_bean_with_image(b, output_dir)
                saved.append(json_path)
            except Exception as e:  # pragma: no cover
                logger.debug(f"Failed saving bean {b.name}: {e}")
        return saved

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Not implemented for The Naughty Dog"""
        raise NotImplementedError("Not implemented for The Naughty Dog")
