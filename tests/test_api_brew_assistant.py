"""Tests for coffee brew assistant API endpoint."""

import base64
import hmac
import hashlib
import json
import os
import time
import pytest
from unittest.mock import AsyncMock, patch
from kissaten.api.brew_assistant import agent, BrewRecipeResponse, BrewParameterSummary, BrewStep, RecipeAdjustment


def generate_test_jwt(email="test@user.com", secret="kissaten_brewing_secret_signature_key_2026_change_me_in_prod", expired=False):
    """Utility to generate a signed JWT for testing."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    exp = now - 60 if expired else now + 3600
    payload = {
        "sub": "user_123",
        "email": email,
        "iat": now,
        "exp": exp
    }

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    hdr_b64 = b64url(json.dumps(header).encode("utf-8"))
    pay_b64 = b64url(json.dumps(payload).encode("utf-8"))

    signing_input = f"{hdr_b64}.{pay_b64}".encode("utf-8")
    sig_bytes = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = b64url(sig_bytes)

    return f"{hdr_b64}.{pay_b64}.{sig_b64}"


@pytest.mark.asyncio
async def test_brew_assistant_unauthorized_if_no_header(client):
    """POST /v1/brew-assistant/recipe should return 401 if Authorization header is missing."""
    payload = {
        "bean_name": "Pink Bourbon",
        "roaster_name": "Standout Coffee",
        "parameters": {
            "dose_g": 15.0,
            "water_to_coffee_ratio": 15.0,
            "brewer": "V60",
            "grinder": "Comandante C40"
        }
    }
    response = client.post("/v1/brew-assistant/recipe", json=payload)
    assert response.status_code == 401
    assert "Authorization header is required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_brew_assistant_unauthorized_if_invalid_token(client):
    """POST /v1/brew-assistant/recipe should return 401 if Token header signature is mismatched."""
    payload = {
        "bean_name": "Pink Bourbon",
        "roaster_name": "Standout Coffee"
    }
    headers = {"Authorization": "Bearer badtoken.notvalid.signature"}
    response = client.post("/v1/brew-assistant/recipe", json=payload, headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_brew_assistant_unauthorized_on_expired_token(client):
    """POST /v1/brew-assistant/recipe should return 401 for an expired token representation."""
    payload = {
        "bean_name": "Pink Bourbon",
        "roaster_name": "Standout Coffee"
    }
    expired_token = generate_test_jwt(expired=True)
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.post("/v1/brew-assistant/recipe", json=payload, headers=headers)
    assert response.status_code == 401
    assert "Access token has expired" in response.json()["detail"]


@pytest.mark.asyncio
async def test_brew_assistant_success_with_valid_token_and_mocked_llm(client):
    """POST /v1/brew-assistant/recipe returns 200 with valid JWT and mocked Gemini results."""
    valid_token = generate_test_jwt()
    headers = {"Authorization": f"Bearer {valid_token}"}
    payload = {
        "bean_name": "Pink Bourbon",
        "roaster_name": "Standout Coffee",
        "process": "Washed",
        "variety": "Pink Bourbon",
        "parameters": {
            "dose_g": 8.0,
            "water_to_coffee_ratio": 15.0,
            "brewer": "Baby Orea",
            "grinder": "Comandante C40"
        }
    }

    # Setup mocked recipe response
    mock_data = BrewRecipeResponse(
        introduction="Here is a recipe designed for the Baby Orea...",
        parameters=BrewParameterSummary(
            coffee_dose_g=8.0,
            water_ratio="1:15",
            total_water_g=120.0,
            grind_size_recommendation="21–23 clicks",
            water_temp_c="92°C–93°C",
            filter_paper="Flat-bottom wave paper"
        ),
        steps=[
            BrewStep(id=1, title="Prep", time_range="0:00", water_pour_g=None, accumulated_water_g=0.0, description="Rinse paper filter..."),
            BrewStep(id=2, title="First Bloom", time_range="0:00 - 0:30", water_pour_g=20.0, accumulated_water_g=20.0, description="Pour 20g quickly but gently.")
        ],
        adjustments=[
            RecipeAdjustment(condition="If tastes sour", action="Grind finer")
        ]
    )

    # Patch the agent.run method to return our structured model
    mock_run_result = AsyncMock()
    mock_run_result.data = mock_data

    with patch.object(agent, "run", new_callable=AsyncMock) as mock_run, \
         patch.dict(os.environ, {"GOOGLE_API_KEY": "fake_test_key_for_agent_validation"}):
        mock_run.return_value = mock_run_result

        response = client.post("/v1/brew-assistant/recipe", json=payload, headers=headers)

        mock_run.assert_called_once()
        assert response.status_code == 200

        res_json = response.json()
        assert res_json["introduction"] == "Here is a recipe designed for the Baby Orea..."
        assert res_json["parameters"]["grind_size_recommendation"] == "21–23 clicks"
        assert len(res_json["steps"]) == 2
        assert res_json["steps"][0]["title"] == "Prep"
