import os
import pytest
from kissaten.scrapers.base import BaseScraper
from unittest.mock import MagicMock, patch

class TestBotScraper(BaseScraper):
    """Test scraper implementation for Web Bot Auth."""
    async def get_store_urls(self) -> list[str]:
        return []

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        return []

@pytest.mark.asyncio
async def test_no_web_bot_auth_when_keys_missing(monkeypatch):
    """Test that signing returns empty dict if keys are not set in environment."""
    monkeypatch.delenv("BOT_PRIVATE_KEY_PEM", raising=False)
    monkeypatch.delenv("BOT_KEY_ID", raising=False)

    async with TestBotScraper(roaster_name="test_roaster", base_url="https://example.com") as scraper:
        # Explicitly bypass local .env load for the test
        scraper.bot_private_key_pem = None
        scraper.bot_key_id = None
        
        headers = scraper.get_signed_headers("https://example.com/shop")
        assert headers == {}

@pytest.mark.asyncio
async def test_web_bot_auth_generation_and_headers(monkeypatch):
    """Test that Web Bot Auth generates correctly structured signed headers."""
    test_private_key = (
        "-----BEGIN PRIVATE KEY-----\n"
        "MC4CAQAwBQYDK2VwBCIEIBRXP08ztqfEhuKh+jDwRwD3AX4Nydv3V29DX2qrR93A\n"
        "-----END PRIVATE KEY-----"
    )
    test_key_id = "test-key-id-123"
    test_agent_url = "https://signature.test"

    monkeypatch.setenv("BOT_PRIVATE_KEY_PEM", test_private_key)
    monkeypatch.setenv("BOT_KEY_ID", test_key_id)
    monkeypatch.setenv("SIGNATURE_AGENT_URL", test_agent_url)

    async with TestBotScraper(roaster_name="test_roaster", base_url="https://example.com") as scraper:
        headers = scraper.get_signed_headers("https://example.com/shop")
        
        assert "Signature-Agent" in headers
        assert "Signature-Input" in headers
        assert "Signature" in headers

        assert headers["Signature-Agent"] == f'"{test_agent_url}"'
        assert f'keyid="{test_key_id}"' in headers["Signature-Input"]
        assert 'tag="web-bot-auth"' in headers["Signature-Input"]
        assert headers["Signature"].startswith("sig2=:")
        assert headers["Signature"].endswith(":")
