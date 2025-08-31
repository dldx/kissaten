"""Scrapers module for coffee roaster websites."""

from .alchemy_coffee import AlchemyCoffeeScraper
from .amoc_coffee import AmocCoffeeScraper
from .assembly_coffee import AssemblyCoffeeScraper
from .atmans_coffee import AtmansCoffeeScraper
from .base import BaseScraper
from .bugan_coffee import BuganCoffeeScraper
from .cartwheel_coffee import CartwheelCoffeeScraper
from .coborn_coffee import CobornCoffeeScraper
from .coffeelab import CoffeeLabScraper
from .crankhouse_coffee import CrankhouseCoffeeScraper
from .curve_coffee import CurveCoffeeScraper
from .dak_coffee import DakCoffeeScraper
from .dark_arts_coffee import DarkArtsCoffeeScraper
from .drop_coffee import DropCoffeeScraper
from .dumbo_coffee import DumboCoffeeScraper
from .extract_coffee import ExtractCoffeeScraper
from .fjord_coffee import FjordCoffeeScraper
from .formative_coffee import FormativeCoffeeScraper
from .friedhats import FriedhatsScraper
from .hola_coffee import HolaCoffeeScraper
from .killbean import KillBeanScraper
from .nomad_coffee import NomadCoffeeScraper
from .nostos_coffee import NostosCoffeeScraper
from .nubra_coffee import NubraCoffeeScraper
from .obadiah_coffee import ObadiahCoffeeScraper
from .oma_coffee import OmaCoffeeScraper
from .onyx_coffee import OnyxCoffeeScraper
from .outpost_coffee import OutpostCoffeeScraper
from .people_possession import PeoplePossessionScraper
from .plot_roasting import PlotRoastingScraper
from .qima_coffee import QimaCoffeeScraper
from .registry import ScraperRegistry, get_registry, register_scraper
from .roundhill_roastery import RoundhillRoasteryScraper
from .rounton_coffee import RountonCoffeeScraper
from .scenery_coffee import SceneryCoffeeScraper
from .september_coffee import SeptemberCoffeeScraper
from .sey_coffee import SeyCoffeeScraper
from .skylark_coffee import SkylarkCoffeeScraper
from .special_guests_coffee import SpecialGuestsCoffeeScraper
from .standout_coffee import StandoutCoffeeScraper
from .sweven_coffee import SwevenCoffeeScraper
from .taith_coffee import TaithCoffeeScraper
from .tanat_coffee import TanatCoffeeScraper
from .three_marks_coffee import ThreeMarksCoffeeScraper
from .uncle_ben_coffee import UncleBenCoffeeScraper

__all__ = [
    "AlchemyCoffeeScraper",
    "AmocCoffeeScraper",
    "AssemblyCoffeeScraper",
    "AtmansCoffeeScraper",
    "BaseScraper",
    "BuganCoffeeScraper",
    "CartwheelCoffeeScraper",
    "CobornCoffeeScraper",
    "CoffeeLabScraper",
    "CrankhouseCoffeeScraper",
    "CurveCoffeeScraper",
    "DakCoffeeScraper",
    "DarkArtsCoffeeScraper",
    "DropCoffeeScraper",
    "DumboCoffeeScraper",
    "ExtractCoffeeScraper",
    "FjordCoffeeScraper",
    "FormativeCoffeeScraper",
    "FriedhatsScraper",
    "HolaCoffeeScraper",
    "KillBeanScraper",
    "NomadCoffeeScraper",
    "NostosCoffeeScraper",
    "NubraCoffeeScraper",
    "ObadiahCoffeeScraper",
    "OmaCoffeeScraper",
    "OnyxCoffeeScraper",
    "OutpostCoffeeScraper",
    "PeoplePossessionScraper",
    "PlotRoastingScraper",
    "QimaCoffeeScraper",
    "RoundhillRoasteryScraper",
    "RountonCoffeeScraper",
    "SceneryCoffeeScraper",
    "ScraperRegistry",
    "SeptemberCoffeeScraper",
    "SeyCoffeeScraper",
    "SkylarkCoffeeScraper",
    "SpecialGuestsCoffeeScraper",
    "StandoutCoffeeScraper",
    "SwevenCoffeeScraper",
    "TaithCoffeeScraper",
    "TanatCoffeeScraper",
    "ThreeMarksCoffeeScraper",
    "UncleBenCoffeeScraper",
    "get_registry",
    "register_scraper",
]
