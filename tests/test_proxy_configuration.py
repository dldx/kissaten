"""Test proxy configuration in BaseScraper."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kissaten.scrapers.base import BaseScraper


class TestProxyScraper(BaseScraper):
    """Test scraper implementation for proxy testing."""

    async def get_store_urls(self) -> list[str]:
        """Dummy implementation."""
        return []

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Dummy implementation."""
        return []


@pytest.fixture
def mock_registry():
    """Mock the scraper registry to avoid validation errors."""
    with patch("kissaten.scrapers.registry.get_registry") as mock_get_registry:
        mock_registry = MagicMock()
        mock_registry.list_scrapers.return_value = [
            MagicMock(roaster_name="test_roaster", scraper_class=TestProxyScraper)
        ]
        mock_get_registry.return_value = mock_registry
        yield mock_registry


@pytest.mark.asyncio
async def test_proxy_configuration_from_env(mock_registry, monkeypatch, tmp_path):
    """Test that proxy settings are loaded from the SCRAPER_* environment variables."""
    # Create a temporary .env file
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SCRAPER_HTTP_PROXY=http://proxy.example.com:8080\nSCRAPER_HTTPS_PROXY=https://proxy.example.com:8443\n"
    )

    # Change to temp directory to load the .env file
    original_dir = Path.cwd()
    os.chdir(tmp_path)

    try:
        # Set environment variables
        monkeypatch.setenv("SCRAPER_HTTP_PROXY", "http://proxy.example.com:8080")
        monkeypatch.setenv("SCRAPER_HTTPS_PROXY", "https://proxy.example.com:8443")
        monkeypatch.delenv("HTTP_PROXY", raising=False)
        monkeypatch.delenv("HTTPS_PROXY", raising=False)

        # Initialize scraper
        async with TestProxyScraper(roaster_name="test_roaster", base_url="https://example.com") as scraper:
            # Check that proxy settings were loaded
            assert scraper.http_proxy == "http://proxy.example.com:8080"
            assert scraper.https_proxy == "https://proxy.example.com:8443"

            # Check that httpx client has proxy configuration
            assert scraper.client is not None
            # Note: httpx client proxies are set but not easily accessible for testing
            # In real usage, the proxies would be used for requests

    finally:
        os.chdir(original_dir)


@pytest.mark.asyncio
async def test_proxy_configuration_httpx(mock_registry, monkeypatch):
    """Test that httpx client is configured with proxies."""
    monkeypatch.setenv("SCRAPER_HTTP_PROXY", "http://proxy.example.com:8080")
    monkeypatch.setenv("SCRAPER_HTTPS_PROXY", "https://proxy.example.com:8443")

    async with TestProxyScraper(roaster_name="test_roaster", base_url="https://example.com") as scraper:
        # Verify proxy URLs are stored
        assert scraper.http_proxy == "http://proxy.example.com:8080"
        assert scraper.https_proxy == "https://proxy.example.com:8443"

        # Verify httpx client was created (proxies are internal)
        assert scraper.client is not None


@pytest.mark.asyncio
async def test_no_proxy_configuration(mock_registry, monkeypatch):
    """Test that scraper works without proxy configuration."""
    # Ensure no proxy environment variables are set
    monkeypatch.delenv("SCRAPER_HTTP_PROXY", raising=False)
    monkeypatch.delenv("SCRAPER_HTTPS_PROXY", raising=False)
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)

    async with TestProxyScraper(roaster_name="test_roaster", base_url="https://example.com") as scraper:
        # Verify no proxy URLs are set
        assert scraper.http_proxy is None
        assert scraper.https_proxy is None

        # Verify httpx client was still created
        assert scraper.client is not None


@pytest.mark.asyncio
async def test_playwright_proxy_configuration(mock_registry, monkeypatch):
    """Test that Playwright browser is configured with proxy."""
    monkeypatch.delenv("SCRAPER_HTTP_PROXY", raising=False)
    monkeypatch.setenv("SCRAPER_HTTPS_PROXY", "https://proxy.example.com:8443")

    async with TestProxyScraper(roaster_name="test_roaster", base_url="https://example.com") as scraper:
        # Verify proxy URL is stored
        assert scraper.https_proxy == "https://proxy.example.com:8443"

        # Note: We don't actually launch the browser in tests as it's expensive
        # In real usage, the browser would be configured with the proxy
        # The proxy configuration happens in _get_browser() method


@pytest.mark.asyncio
async def test_legacy_proxy_names_fallback(mock_registry, monkeypatch):
    """Legacy HTTP_PROXY/HTTPS_PROXY are honoured when SCRAPER_* names are absent."""
    monkeypatch.delenv("SCRAPER_HTTP_PROXY", raising=False)
    monkeypatch.delenv("SCRAPER_HTTPS_PROXY", raising=False)
    monkeypatch.setenv("HTTP_PROXY", "http://legacy.example.com:8080")
    monkeypatch.setenv("HTTPS_PROXY", "https://legacy.example.com:8443")

    async with TestProxyScraper(roaster_name="test_roaster", base_url="https://example.com") as scraper:
        assert scraper.http_proxy == "http://legacy.example.com:8080"
        assert scraper.https_proxy == "https://legacy.example.com:8443"
        assert scraper.client is not None


@pytest.mark.asyncio
async def test_scraper_proxy_names_take_precedence(mock_registry, monkeypatch):
    """SCRAPER_* variables win over the legacy generic names."""
    monkeypatch.setenv("SCRAPER_HTTP_PROXY", "http://scraper.example.com:8080")
    monkeypatch.setenv("SCRAPER_HTTPS_PROXY", "https://scraper.example.com:8443")
    monkeypatch.setenv("HTTP_PROXY", "http://legacy.example.com:8080")
    monkeypatch.setenv("HTTPS_PROXY", "https://legacy.example.com:8443")

    async with TestProxyScraper(roaster_name="test_roaster", base_url="https://example.com") as scraper:
        assert scraper.http_proxy == "http://scraper.example.com:8080"
        assert scraper.https_proxy == "https://scraper.example.com:8443"
