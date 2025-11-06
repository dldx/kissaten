"""Scrapers module for coffee roaster websites."""

from .aery_coffee import AeryCoffeeScraper
from .alchemy_coffee import AlchemyCoffeeScraper
from .amoc_coffee import AmocCoffeeScraper
from .apollons_gold import ApollonsGoldScraper
from .archers_coffee import ArchersCoffeeScraper
from .artisan_roast import ArtisanRoastScraper
from .assembly_coffee import AssemblyCoffeeScraper
from .atkinsons_coffee import AtkinsonsCoffeeScraper
from .atmans_coffee import AtmansCoffeeScraper
from .aviary import AviaryCoffeeScraper
from .base import BaseScraper
from .blue_bottle_coffee import BlueBottleCoffeeScraper
from .blue_tokai_coffee import BlueTokaiCoffeeScraper
from .bluebird_coffee import BluebirdCoffeeScraper
from .bob_coffee import BOBCoffeeScraper
from .bugan_coffee import BuganCoffeeScraper
from .cafe_amor_perfecto import CafeAmorPerfectoScraper
from .calendar_coffee import CalendarCoffeeScraper
from .caravan_coffee import CaravanCoffeeScraper
from .cartwheel_coffee import CartwheelCoffeeScraper
from .chunky_cherry_coffee import ChunkyCherryCoffeeScraper
from .coborn_coffee import CobornCoffeeScraper
from .coffee_collective import CoffeeCollectiveScraper
from .coffee_sakura import CoffeeSakuraScraper
from .coffee_wallas import CoffeeWallasScraper
from .coffeelab import CoffeeLabScraper
from .crankhouse_coffee import CrankhouseCoffeeScraper
from .curve_coffee import CurveCoffeeScraper
from .dak import DakCoffeeScraper
from .dark_arts_coffee import DarkArtsCoffeeScraper
from .decaf_before_death import DecafBeforeDeathScraper
from .ditta_artigianale import DittaArtigianaleScraper
from .doubleshot import DoubleshotScraper
from .drop_coffee import DropCoffeeScraper
from .dumbo_coffee import DumboCoffeeScraper
from .elsewhere_coffee import ElsewhereCoffeeScraper
from .extract_coffee import ExtractCoffeeScraper
from .five_elephant import FiveElephantScraper
from .fjord_coffee import FjordCoffeeScraper
from .fluir_coffee import FluirCoffeeScraper
from .formative_coffee import FormativeCoffeeScraper
from .friedhats import FriedhatsScraper
from .frukt import FruktCoffeeScraper
from .fuglen_coffee import FuglenCoffeeScraper
from .gardelli_coffee import GardelliCoffeeScraper
from .glass_coffee import GlassCoffeeScraper
from .glitch_coffee import GlitchCoffeeScraper
from .gout_co import GoutAndCoScraper
from .greysoul_coffee import GreySoulCoffeeScraper
from .hermanos_coffee_roasters import HermanosCoffeeRoastersScraper
from .hola_coffee import HolaCoffeeScraper
from .hydrangea_coffee import HydrangeaCoffeeScraper
from .intermission_coffee import IntermissionCoffeeScraper
from .jbc_coffee import JBCCoffeeScraper
from .kaffeelix import KaffeelixScraper
from .killbean import KillBeanScraper
from .koppi import KoppiScraper
from .leaves_coffee import LeavesCoffeeScraper
from .los_amigos_coffee import LosAmigosCoffeeScraper
from .mame_coffee import MameCoffeeScraper
from .market_lane_coffee import MarketLaneCoffeeScraper
from .mazelab import MazelabCoffeeScraper
from .mirra_coffee import MirraCoffeeScraper
from .modcup_coffee import ModcupCoffeeScraper
from .mokcoffee import MOKCoffeeScraper
from .momos_coffee import MomosCoffeeScraper
from .native_coffee_company import NativeCoffeeCompanyScraper
from .naughty_dog import NaughtyDogScraper
from .nokora import NokoraCoffeeScraper
from .nomad_coffee import NomadCoffeeScraper
from .nostos_coffee import NostosCoffeeScraper
from .nubra_coffee import NubraCoffeeScraper
from .nylon import NylonCoffeeScraper
from .obadiah_coffee import ObadiahCoffeeScraper
from .oma_coffee import OmaCoffeeScraper
from .ona_coffee import OnaCoffeeScraper
from .one_half_coffee import OneHalfCoffeeScraper
from .onyx_coffee import OnyxCoffeeScraper
from .outpost_coffee import OutpostCoffeeScraper
from .people_possession import PeoplePossessionScraper
from .perky_blenders import PerkyBlendersCoffeeScraper
from .phil_sebastian import PhilSebastianScraper
from .plot_roasting import PlotRoastingScraper
from .process_coffee import ProcessCoffeeScraper
from .prodigal_coffee import ProdigalCoffeeScraper
from .prolog_coffee import PrologCoffeeScraper
from .proud_mary_coffee import ProudMaryCoffeeScraper
from .qima_coffee import QimaCoffeeScraper
from .registry import ScraperRegistry, get_registry, register_scraper
from .rest_coffee import RestCoffeeScraper
from .revel_coffee import RevelCoffeeScraper
from .ripsnorter import RipsnorterScraper
from .rogue_wave_coffee import RogueWaveCoffeeScraper
from .roundhill_roastery import RoundhillRoasteryScraper
from .rounton_coffee import RountonCoffeeScraper
from .sango import SangoSpecialityCoffeeScraper
from .scenery_coffee import SceneryCoffeeScraper
from .september_coffee import SeptemberCoffeeScraper
from .sey_coffee import SeyCoffeeScraper
from .shokunin import ShokuninCoffeeRoastersScraper
from .simple_kaffa import SimpleKaffaCoffeeScraper
from .siolim_coffee import SiolimCoffeeScraper
from .skylark_coffee import SkylarkCoffeeScraper
from .slurp_coffee_roasters import SlurpCoffeeRoastersScraper
from .space_roastery import SpaceCoffeeRoasteryScraper
from .special_guests_coffee import SpecialGuestsCoffeeScraper
from .standout_coffee import StandoutCoffeeScraper
from .subko_coffee import SubkoCoffeeScraper
from .sw_roasting import SWRoastingScraper
from .sweven_coffee import SwevenCoffeeScraper
from .taith_coffee import TaithCoffeeScraper
from .taller_cafe import TallerCafeScraper
from .tanat_coffee import TanatCoffeeScraper
from .terarosa import TerarosaCoffeeScraper
from .terraform_coffee import TerraformCoffeeScraper
from .the_barn import TheBarnCoffeeScraper
from .three_marks_coffee import ThreeMarksCoffeeScraper
from .tim_wendelboe import TimWendelboeScraper
from .uncle_ben_coffee import UncleBenCoffeeScraper
from .vibe_with import VibeWithCoffeeRoasteryScraper
from .weekenders import WeekendersCoffeeScraper

__all__ = [
    "AeryCoffeeScraper",
    "AlchemyCoffeeScraper",
    "AmocCoffeeScraper",
    "ApollonsGoldScraper",
    "ArchersCoffeeScraper",
    "ArtisanRoastScraper",
    "AssemblyCoffeeScraper",
    "AtkinsonsCoffeeScraper",
    "AtmansCoffeeScraper",
    "AviaryCoffeeScraper",
    "BaseScraper",
    "BlueBottleCoffeeScraper",
    "BlueTokaiCoffeeScraper",
    "BluebirdCoffeeScraper",
    "BOBCoffeeScraper",
    "BuganCoffeeScraper",
    "CafeAmorPerfectoScraper",
    "CalendarCoffeeScraper",
    "CaravanCoffeeScraper",
    "CartwheelCoffeeScraper",
    "ChunkyCherryCoffeeScraper",
    "CobornCoffeeScraper",
    "CoffeeWallasScraper",
    "CoffeeLabScraper",
    "CoffeeCollectiveScraper",
    "CoffeeSakuraScraper",
    "CrankhouseCoffeeScraper",
    "CurveCoffeeScraper",
    "DakCoffeeScraper",
    "DarkArtsCoffeeScraper",
    "DecafBeforeDeathScraper",
    "DittaArtigianaleScraper",
    "DoubleshotScraper",
    "DropCoffeeScraper",
    "DumboCoffeeScraper",
    "ElsewhereCoffeeScraper",
    "ExtractCoffeeScraper",
    "FiveElephantScraper",
    "FjordCoffeeScraper",
    "FluirCoffeeScraper",
    "FormativeCoffeeScraper",
    "FriedhatsScraper",
    "FruktCoffeeScraper",
    "FuglenCoffeeScraper",
    "GardelliCoffeeScraper",
    "GlassCoffeeScraper",
    "GlitchCoffeeScraper",
    "GoutAndCoScraper",
    "GreySoulCoffeeScraper",
    "HermanosCoffeeRoastersScraper",
    "HolaCoffeeScraper",
    "HydrangeaCoffeeScraper",
    "IntermissionCoffeeScraper",
    "JBCCoffeeScraper",
    "KaffeelixScraper",
    "KillBeanScraper",
    "KoppiScraper",
    "LeavesCoffeeScraper",
    "LosAmigosCoffeeScraper",
    "MameCoffeeScraper",
    "MarketLaneCoffeeScraper",
    "MazelabCoffeeScraper",
    "MirraCoffeeScraper",
    "ModcupCoffeeScraper",
    "MOKCoffeeScraper",
    "MomosCoffeeScraper",
    "NativeCoffeeCompanyScraper",
    "NaughtyDogScraper",
    "NomadCoffeeScraper",
    "NokoraCoffeeScraper",
    "NostosCoffeeScraper",
    "NubraCoffeeScraper",
    "NylonCoffeeScraper",
    "ObadiahCoffeeScraper",
    "OmaCoffeeScraper",
    "OnaCoffeeScraper",
    "OneHalfCoffeeScraper",
    "OnyxCoffeeScraper",
    "OutpostCoffeeScraper",
    "PeoplePossessionScraper",
    "PerkyBlendersCoffeeScraper",
    "PhilSebastianScraper",
    "PlotRoastingScraper",
    "ProcessCoffeeScraper",
    "ProdigalCoffeeScraper",
    "PrologCoffeeScraper",
    "ProudMaryCoffeeScraper",
    "QimaCoffeeScraper",
    "RestCoffeeScraper",
    "RevelCoffeeScraper",
    "RipsnorterScraper",
    "RogueWaveCoffeeScraper",
    "RoundhillRoasteryScraper",
    "RountonCoffeeScraper",
    "SangoSpecialityCoffeeScraper",
    "SceneryCoffeeScraper",
    "ScraperRegistry",
    "SeptemberCoffeeScraper",
    "SeyCoffeeScraper",
    "ShokuninCoffeeRoastersScraper",
    "SimpleKaffaCoffeeScraper",
    "SkylarkCoffeeScraper",
    "SlurpCoffeeRoastersScraper",
    "SpaceCoffeeRoasteryScraper",
    "SpecialGuestsCoffeeScraper",
    "SiolimCoffeeScraper",
    "StandoutCoffeeScraper",
    "SubkoCoffeeScraper",
    "SwevenCoffeeScraper",
    "SWRoastingScraper",
    "TaithCoffeeScraper",
    "TallerCafeScraper",
    "TanatCoffeeScraper",
    "TerraformCoffeeScraper",
    "TerarosaCoffeeScraper",
    "TheBarnCoffeeScraper",
    "ThreeMarksCoffeeScraper",
    "TimWendelboeScraper",
    "UncleBenCoffeeScraper",
    "VibeWithCoffeeRoasteryScraper",
    "WeekendersCoffeeScraper",
    "get_registry",
    "register_scraper",
]
