"""Scrapers module for coffee roaster websites."""

from .alchemy_coffee import AlchemyCoffeeScraper
from .amoc_coffee import AmocCoffeeScraper
from .base import BaseScraper
from .cartwheel_coffee import CartwheelCoffeeScraper
from .coborn_coffee import CobornCoffeeScraper
from .dak_coffee import DakCoffeeScraper
from .drop_coffee import DropCoffeeScraper
from .killbean import KillBeanScraper
from .nostos_coffee import NostosCoffeeScraper
from .people_possession import PeoplePossessionScraper
from .qima_coffee import QimaCoffeeScraper
from .registry import ScraperRegistry, get_registry, register_scraper
from .special_guests_coffee import SpecialGuestsCoffeeScraper
from .taith_coffee import TaithCoffeeScraper
from .tanat_coffee import TanatCoffeeScraper
from .uncle_ben_coffee import UncleBenCoffeeScraper

__all__ = [
    "AlchemyCoffeeScraper",
    "AmocCoffeeScraper",
    "BaseScraper",
    "CartwheelCoffeeScraper",
    "CobornCoffeeScraper",
    "DakCoffeeScraper",
    "DropCoffeeScraper",
    "KillBeanScraper",
    "NostosCoffeeScraper",
    "PeoplePossessionScraper",
    "QimaCoffeeScraper",
    "ScraperRegistry",
    "SpecialGuestsCoffeeScraper",
    "TaithCoffeeScraper",
    "TanatCoffeeScraper",
    "UncleBenCoffeeScraper",
    "get_registry",
    "register_scraper",
]
