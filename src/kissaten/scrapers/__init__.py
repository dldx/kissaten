"""Scrapers module for coffee roaster websites."""

from .base import BaseScraper
from .cartwheel_coffee import CartwheelCoffeeScraper
from .registry import ScraperRegistry, get_registry, register_scraper

__all__ = [
    "BaseScraper",
    "CartwheelCoffeeScraper",
    "ScraperRegistry",
    "get_registry",
    "register_scraper",
]
