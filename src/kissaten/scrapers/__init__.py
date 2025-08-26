"""Scrapers module for coffee roaster websites."""

from .alchemy_coffee import AlchemyCoffeeScraper
from .amoc_coffee import AmocCoffeeScraper
from .base import BaseScraper
from .cartwheel_coffee import CartwheelCoffeeScraper
from .coborn_coffee import CobornCoffeeScraper
from .coffeelab import CoffeeLabScraper
from .dak_coffee import DakCoffeeScraper
from .drop_coffee import DropCoffeeScraper
from .dumbo_coffee import DumboCoffeeScraper
from .fjord_coffee import FjordCoffeeScraper
from .friedhats import FriedhatsScraper
from .killbean import KillBeanScraper
from .nostos_coffee import NostosCoffeeScraper
from .people_possession import PeoplePossessionScraper
from .plot_roasting import PlotRoastingScraper
from .qima_coffee import QimaCoffeeScraper
from .registry import ScraperRegistry, get_registry, register_scraper
from .special_guests_coffee import SpecialGuestsCoffeeScraper
from .standout_coffee import StandoutCoffeeScraper
from .taith_coffee import TaithCoffeeScraper
from .tanat_coffee import TanatCoffeeScraper
from .uncle_ben_coffee import UncleBenCoffeeScraper

__all__ = [
    "AlchemyCoffeeScraper",
    "AmocCoffeeScraper",
    "BaseScraper",
    "CartwheelCoffeeScraper",
    "CobornCoffeeScraper",
    "CoffeeLabScraper",
    "DakCoffeeScraper",
    "DropCoffeeScraper",
    "DumboCoffeeScraper",
    "FjordCoffeeScraper",
    "FriedhatsScraper",
    "KillBeanScraper",
    "NostosCoffeeScraper",
    "PeoplePossessionScraper",
    "PlotRoastingScraper",
    "QimaCoffeeScraper",
    "ScraperRegistry",
    "SpecialGuestsCoffeeScraper",
    "StandoutCoffeeScraper",
    "TaithCoffeeScraper",
    "TanatCoffeeScraper",
    "UncleBenCoffeeScraper",
    "get_registry",
    "register_scraper",
]
