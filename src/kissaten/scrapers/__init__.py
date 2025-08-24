"""Scrapers module for coffee roaster websites."""

from .amoc_coffee import AmocCoffeeScraper
from .base import BaseScraper
from .cartwheel_coffee import CartwheelCoffeeScraper
from .coborn_coffee import CobornCoffeeScraper
from .registry import ScraperRegistry, get_registry, register_scraper

__all__ = [
    "AmocCoffeeScraper",
    "BaseScraper",
    "CartwheelCoffeeScraper",
    "CobornCoffeeScraper",
    "ScraperRegistry",
    "get_registry",
    "register_scraper",
]
