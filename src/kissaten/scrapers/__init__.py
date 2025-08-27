"""Scrapers module for coffee roaster websites."""

from .alchemy_coffee import AlchemyCoffeeScraper
from .amoc_coffee import AmocCoffeeScraper
from .atmans_coffee import AtmansCoffeeScraper
from .base import BaseScraper
from .cartwheel_coffee import CartwheelCoffeeScraper
from .coborn_coffee import CobornCoffeeScraper
from .coffeelab import CoffeeLabScraper
from .crankhouse_coffee import CrankhouseCoffeeScraper
from .curve_coffee import CurveCoffeeScraper
from .dak_coffee import DakCoffeeScraper
from .drop_coffee import DropCoffeeScraper
from .dumbo_coffee import DumboCoffeeScraper
from .fjord_coffee import FjordCoffeeScraper
from .friedhats import FriedhatsScraper
from .hola_coffee import HolaCoffeeScraper
from .killbean import KillBeanScraper
from .nomad_coffee import NomadCoffeeScraper
from .nostos_coffee import NostosCoffeeScraper
from .nubra_coffee import NubraCoffeeScraper
from .onyx_coffee import OnyxCoffeeScraper
from .people_possession import PeoplePossessionScraper
from .plot_roasting import PlotRoastingScraper
from .qima_coffee import QimaCoffeeScraper
from .registry import ScraperRegistry, get_registry, register_scraper
from .roundhill_roastery import RoundhillRoasteryScraper
from .scenery_coffee import SceneryCoffeeScraper
from .sey_coffee import SeyCoffeeScraper
from .skylark_coffee import SkylarkCoffeeScraper
from .special_guests_coffee import SpecialGuestsCoffeeScraper
from .standout_coffee import StandoutCoffeeScraper
from .taith_coffee import TaithCoffeeScraper
from .tanat_coffee import TanatCoffeeScraper
from .three_marks_coffee import ThreeMarksCoffeeScraper
from .uncle_ben_coffee import UncleBenCoffeeScraper

__all__ = [
    "AlchemyCoffeeScraper",
    "AmocCoffeeScraper",
    "AtmansCoffeeScraper",
    "BaseScraper",
    "CartwheelCoffeeScraper",
    "CobornCoffeeScraper",
    "CoffeeLabScraper",
    "CrankhouseCoffeeScraper",
    "CurveCoffeeScraper",
    "DakCoffeeScraper",
    "DropCoffeeScraper",
    "DumboCoffeeScraper",
    "FjordCoffeeScraper",
    "FriedhatsScraper",
    "HolaCoffeeScraper",
    "KillBeanScraper",
    "NomadCoffeeScraper",
    "NostosCoffeeScraper",
    "NubraCoffeeScraper",
    "OnyxCoffeeScraper",
    "PeoplePossessionScraper",
    "PlotRoastingScraper",
    "QimaCoffeeScraper",
    "RoundhillRoasteryScraper",
    "SceneryCoffeeScraper",
    "ScraperRegistry",
    "SeyCoffeeScraper",
    "SkylarkCoffeeScraper",
    "SpecialGuestsCoffeeScraper",
    "StandoutCoffeeScraper",
    "TaithCoffeeScraper",
    "TanatCoffeeScraper",
    "ThreeMarksCoffeeScraper",
    "UncleBenCoffeeScraper",
    "get_registry",
    "register_scraper",
]
