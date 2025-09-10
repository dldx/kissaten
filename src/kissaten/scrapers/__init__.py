"""Scrapers module for coffee roaster websites."""

from .alchemy_coffee import AlchemyCoffeeScraper
from .amoc_coffee import AmocCoffeeScraper
from .apollons_gold import ApollonsGoldScraper
from .archers_coffee import ArchersCoffeeScraper
from .artisan_roast import ArtisanRoastScraper
from .assembly_coffee import AssemblyCoffeeScraper
from .atkinsons_coffee import AtkinsonsCoffeeScraper
from .atmans_coffee import AtmansCoffeeScraper
from .base import BaseScraper
from .blue_bottle_coffee import BlueBottleCoffeeScraper
from .blue_tokai_coffee import BlueTokaiCoffeeScraper
from .bluebird_coffee import BluebirdCoffeeScraper
from .bugan_coffee import BuganCoffeeScraper
from .cartwheel_coffee import CartwheelCoffeeScraper
from .coborn_coffee import CobornCoffeeScraper
from .coffee_wallas import CoffeeWallasScraper
from .coffeelab import CoffeeLabScraper
from .crankhouse_coffee import CrankhouseCoffeeScraper
from .curve_coffee import CurveCoffeeScraper
from .dak_coffee import DakCoffeeScraper
from .dark_arts_coffee import DarkArtsCoffeeScraper
from .decaf_before_death import DecafBeforeDeathScraper
from .drop_coffee import DropCoffeeScraper
from .dumbo_coffee import DumboCoffeeScraper
from .extract_coffee import ExtractCoffeeScraper
from .fjord_coffee import FjordCoffeeScraper
from .formative_coffee import FormativeCoffeeScraper
from .friedhats import FriedhatsScraper
from .glitch_coffee import GlitchCoffeeScraper
from .hola_coffee import HolaCoffeeScraper
from .hydrangea_coffee import HydrangeaCoffeeScraper
from .jbc_coffee import JBCCoffeeScraper
from .killbean import KillBeanScraper
from .koppi import KoppiScraper
from .leaves_coffee import LeavesCoffeeScraper
from .los_amigos_coffee import LosAmigosCoffeeScraper
from .mame_coffee import MameCoffeeScraper
from .mirra_coffee import MirraCoffeeScraper
from .modcup_coffee import ModcupCoffeeScraper
from .momos_coffee import MomosCoffeeScraper
from .naughty_dog import NaughtyDogScraper
from .nomad_coffee import NomadCoffeeScraper
from .nostos_coffee import NostosCoffeeScraper
from .nubra_coffee import NubraCoffeeScraper
from .obadiah_coffee import ObadiahCoffeeScraper
from .oma_coffee import OmaCoffeeScraper
from .ona_coffee import OnaCoffeeScraper
from .one_half_coffee import OneHalfCoffeeScraper
from .onyx_coffee import OnyxCoffeeScraper
from .outpost_coffee import OutpostCoffeeScraper
from .people_possession import PeoplePossessionScraper
from .phil_sebastian import PhilSebastianScraper
from .plot_roasting import PlotRoastingScraper
from .prodigal_coffee import ProdigalCoffeeScraper
from .proud_mary_coffee import ProudMaryCoffeeScraper
from .qima_coffee import QimaCoffeeScraper
from .registry import ScraperRegistry, get_registry, register_scraper
from .revel_coffee import RevelCoffeeScraper
from .ripsnorter import RipsnorterScraper
from .rogue_wave_coffee import RogueWaveCoffeeScraper
from .roundhill_roastery import RoundhillRoasteryScraper
from .rounton_coffee import RountonCoffeeScraper
from .scenery_coffee import SceneryCoffeeScraper
from .september_coffee import SeptemberCoffeeScraper
from .sey_coffee import SeyCoffeeScraper
from .skylark_coffee import SkylarkCoffeeScraper
from .special_guests_coffee import SpecialGuestsCoffeeScraper
from .standout_coffee import StandoutCoffeeScraper
from .sw_roasting import SWRoastingScraper
from .sweven_coffee import SwevenCoffeeScraper
from .taith_coffee import TaithCoffeeScraper
from .taller_cafe import TallerCafeScraper
from .tanat_coffee import TanatCoffeeScraper
from .three_marks_coffee import ThreeMarksCoffeeScraper
from .tim_wendelboe import TimWendelboeScraper
from .uncle_ben_coffee import UncleBenCoffeeScraper

__all__ = [
    "AlchemyCoffeeScraper",
    "AmocCoffeeScraper",
    "ApollonsGoldScraper",
    "ArchersCoffeeScraper",
    "ArtisanRoastScraper",
    "AssemblyCoffeeScraper",
    "AtkinsonsCoffeeScraper",
    "AtmansCoffeeScraper",
    "BaseScraper",
    "BlueBottleCoffeeScraper",
    "BlueTokaiCoffeeScraper",
    "BluebirdCoffeeScraper",
    "BuganCoffeeScraper",
    "CartwheelCoffeeScraper",
    "CobornCoffeeScraper",
    "CoffeeWallasScraper",
    "CoffeeLabScraper",
    "CrankhouseCoffeeScraper",
    "CurveCoffeeScraper",
    "DakCoffeeScraper",
    "DarkArtsCoffeeScraper",
    "DecafBeforeDeathScraper",
    "DropCoffeeScraper",
    "DumboCoffeeScraper",
    "ExtractCoffeeScraper",
    "FjordCoffeeScraper",
    "FormativeCoffeeScraper",
    "FriedhatsScraper",
    "GlitchCoffeeScraper",
    "HolaCoffeeScraper",
    "HydrangeaCoffeeScraper",
    "JBCCoffeeScraper",
    "KillBeanScraper",
    "KoppiScraper",
    "LeavesCoffeeScraper",
    "LosAmigosCoffeeScraper",
    "MameCoffeeScraper",
    "MirraCoffeeScraper",
    "ModcupCoffeeScraper",
    "MomosCoffeeScraper",
    "NaughtyDogScraper",
    "NomadCoffeeScraper",
    "NostosCoffeeScraper",
    "NubraCoffeeScraper",
    "ObadiahCoffeeScraper",
    "OmaCoffeeScraper",
    "OnaCoffeeScraper",
    "OneHalfCoffeeScraper",
    "OnyxCoffeeScraper",
    "OutpostCoffeeScraper",
    "PeoplePossessionScraper",
    "PhilSebastianScraper",
    "PlotRoastingScraper",
    "ProdigalCoffeeScraper",
    "ProudMaryCoffeeScraper",
    "QimaCoffeeScraper",
    "RevelCoffeeScraper",
    "RipsnorterScraper",
    "RogueWaveCoffeeScraper",
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
    "SWRoastingScraper",
    "TaithCoffeeScraper",
    "TallerCafeScraper",
    "TanatCoffeeScraper",
    "ThreeMarksCoffeeScraper",
    "TimWendelboeScraper",
    "UncleBenCoffeeScraper",
    "get_registry",
    "register_scraper",
]
