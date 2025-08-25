"""Scraper registry for managing all available scrapers."""

import logging
from dataclasses import dataclass

from .base import BaseScraper

logger = logging.getLogger(__name__)


@dataclass
class ScraperInfo:
    """Information about a registered scraper."""

    name: str
    display_name: str
    roaster_name: str
    website: str
    scraper_class: type[BaseScraper]
    description: str
    status: str = "available"
    requires_api_key: bool = False
    currency: str = "GBP"
    country: str = "UK"

    @property
    def directory_name(self) -> str:
        """Get the directory name for the scraper."""
        return self.roaster_name.lower().replace(" ", "_")


class ScraperRegistry:
    """Central registry for all coffee roaster scrapers."""

    def __init__(self):
        self._scrapers: dict[str, ScraperInfo] = {}

    def register(
        self,
        name: str,
        scraper_class: type[BaseScraper],
        display_name: str,
        roaster_name: str,
        website: str,
        description: str = "",
        requires_api_key: bool = False,
        currency: str = "GBP",
        country: str = "UK",
        status: str = "available",
    ) -> None:
        """Register a new scraper.

        Args:
            name: Internal name for the scraper (used in CLI)
            scraper_class: The scraper class
            display_name: Human-readable name
            roaster_name: Official roaster name
            website: Roaster website
            description: Brief description of the scraper
            requires_api_key: Whether the scraper requires API keys
            currency: Default currency for this roaster
            country: Country where roaster is based
            status: Status of the scraper (available, experimental, deprecated)
        """
        if name in self._scrapers:
            logger.warning(f"Scraper '{name}' is already registered, overwriting")

        self._scrapers[name] = ScraperInfo(
            name=name,
            display_name=display_name,
            roaster_name=roaster_name,
            website=website,
            scraper_class=scraper_class,
            description=description,
            status=status,
            requires_api_key=requires_api_key,
            currency=currency,
            country=country,
        )

        logger.debug(f"Registered scraper: {name} ({roaster_name})")

    def get_scraper_info(self, name: str) -> ScraperInfo | None:
        """Get information about a scraper.

        Args:
            name: Scraper name

        Returns:
            ScraperInfo object or None if not found
        """
        return self._scrapers.get(name.lower())

    def create_scraper(self, name: str, **kwargs) -> BaseScraper | None:
        """Create an instance of a scraper.

        Args:
            name: Scraper name
            **kwargs: Additional arguments to pass to scraper constructor

        Returns:
            Scraper instance or None if not found
        """
        info = self.get_scraper_info(name)
        if not info:
            return None

        try:
            return info.scraper_class(**kwargs)
        except Exception as e:
            logger.error(f"Failed to create scraper '{name}': {e}")
            return None

    def list_scrapers(self, status_filter: str | None = None) -> list[ScraperInfo]:
        """List all registered scrapers.

        Args:
            status_filter: Filter by status (available, experimental, deprecated)

        Returns:
            List of ScraperInfo objects
        """
        scrapers = list(self._scrapers.values())

        if status_filter:
            scrapers = [s for s in scrapers if s.status == status_filter]

        return sorted(scrapers, key=lambda x: x.name)

    def get_scraper_names(self, status_filter: str | None = None) -> list[str]:
        """Get list of scraper names.

        Args:
            status_filter: Filter by status

        Returns:
            List of scraper names
        """
        return [info.name for info in self.list_scrapers(status_filter)]

    def is_registered(self, name: str) -> bool:
        """Check if a scraper is registered.

        Args:
            name: Scraper name

        Returns:
            True if registered
        """
        return name.lower() in self._scrapers

    def unregister(self, name: str) -> bool:
        """Unregister a scraper.

        Args:
            name: Scraper name

        Returns:
            True if unregistered, False if not found
        """
        if name.lower() in self._scrapers:
            del self._scrapers[name.lower()]
            logger.debug(f"Unregistered scraper: {name}")
            return True
        return False


# Global registry instance
registry = ScraperRegistry()


def register_scraper(
    name: str,
    display_name: str,
    roaster_name: str,
    website: str,
    description: str = "",
    requires_api_key: bool = False,
    currency: str = "GBP",
    country: str = "UK",
    status: str = "available",
):
    """Decorator to register a scraper class.

    Args:
        name: Internal name for the scraper
        display_name: Human-readable name
        roaster_name: Official roaster name
        website: Roaster website
        description: Brief description
        requires_api_key: Whether scraper requires API keys
        currency: Default currency
        country: Country where roaster is based
        status: Scraper status

    Returns:
        Decorator function
    """

    def decorator(scraper_class: type[BaseScraper]):
        registry.register(
            name=name,
            scraper_class=scraper_class,
            display_name=display_name,
            roaster_name=roaster_name,
            website=website,
            description=description,
            requires_api_key=requires_api_key,
            currency=currency,
            country=country,
            status=status,
        )
        return scraper_class

    return decorator


def get_registry() -> ScraperRegistry:
    """Get the global scraper registry."""
    return registry
