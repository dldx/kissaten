"""Scrapers module for coffee roaster websites."""

from .base import BaseScraper
from .cartwheel_coffee import CartwheelCoffeeScraper
from .coborn_coffee import CobornCoffeeScraper
from .registry import ScraperRegistry, get_registry, register_scraper

__all__ = [
    "BaseScraper",
    "CartwheelCoffeeScraper",
    "CobornCoffeeScraper",
    "ScraperRegistry",
    "get_registry",
    "register_scraper",
]
