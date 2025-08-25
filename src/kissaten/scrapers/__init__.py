"""Scrapers module for coffee roaster websites."""

from .amoc_coffee import AmocCoffeeScraper
from .base import BaseScraper
from .cartwheel_coffee import CartwheelCoffeeScraper
from .coborn_coffee import CobornCoffeeScraper
from .drop_coffee import DropCoffeeScraper
from .killbean import KillBeanScraper
from .people_possession import PeoplePossessionScraper
from .qima_coffee import QimaCoffeeScraper
from .registry import ScraperRegistry, get_registry, register_scraper

__all__ = [
    "AmocCoffeeScraper",
    "BaseScraper",
    "CartwheelCoffeeScraper",
    "CobornCoffeeScraper",
    "DropCoffeeScraper",
    "KillBeanScraper",
    "PeoplePossessionScraper",
    "QimaCoffeeScraper",
    "ScraperRegistry",
    "get_registry",
    "register_scraper",
]
