"""FastAPI router and PydanticAI Agent for Coffee Brewing Assistant."""

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Literal

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModelSettings

logger = logging.getLogger(__name__)

# Define user request and config models
class DeviceParameters(BaseModel):
    """Device parameters for the brew recipe."""
    dose_g: float = Field(default=15.0, description="Target dry coffee grounds weight, in grams.")
    water_to_coffee_ratio: float | None = Field(default=None, description="Optional brew ratio. If omitted, the model will recommend the ideal one.")
    brewer: str = Field(default="V60", description="The brewer model used, e.g. 'Baby Orea', 'V60', 'Chemex', 'Aeropress'.")
    grinder: str = Field(default="Comandante C40", description="Grinder model name, e.g. 'Comandante C40', 'Fellow Ode Gen 2'.")

class BrewRecipeRequest(BaseModel):
    """Payload to request a personalized brew recipe."""
    bean_name: str = Field(..., description="The name of the coffee bean.")
    roaster_name: str = Field(..., description="The roaster of the coffee bean.")
    process: str | None = Field(None, description="The processing method, e.g., 'Natural', 'Washed', 'Anaerobic'.")
    variety: str | None = Field(None, description="The bean variety/varietal, e.g., 'Pink Bourbon', 'Geisha', 'Burbon'.")
    roast_level: str | None = Field(None, description="Roast level, e.g., 'Light', 'Medium-Light', 'Medium'.")
    roast_profile: str | None = Field(None, description="Filter / Espresso / Both.")
    description: str | None = Field(None, description="The commercial description or story of the bean.")
    tasting_notes: list[str] = Field(default_factory=list, description="Extracted flavor/tasting notes.")
    personal_notes: str | None = Field(None, description="The user's personal brewing/tasting notes/remarks stored in Dexie.")
    additional_guidance: str | None = Field(None, description="Additional custom guidance from the user, e.g. 'well rested', 'fresh', 'lots of fines'.")
    previous_brewing_notes: list[str] = Field(default_factory=list, description="Historical brewing notes from the user's past tasting sessions to understand their style.")
    parameters: DeviceParameters = Field(default_factory=DeviceParameters, description="Pre-configured brewer/grinder specs.")

# Define response models
class BrewParameterSummary(BaseModel):
    """Parameters of the generated coffee recipe."""
    coffee_dose_g: float = Field(..., description="The dry coffee grounds dose, in grams.")
    water_ratio: str = Field(..., description="The brew ratio in text format, e.g., '1:15' for filter, or '1:2.1 (38g beverage yield)' for espresso.")
    total_water_g: float = Field(..., description="Total water poured over the coffee, or total beverage yield for pump espresso machines, in grams.")
    grind_size_recommendation: str = Field(..., description="Tailored recommended grind size, including setting description or clicks (e.g. '21–23 clicks' or '1.3.5 setting').")
    water_temp_c: str = Field(..., description="Recommended water temperature or range, e.g. '92°C–93°C' or '96°C (boiling in kettle)'.")
    filter_paper: str = Field(..., description="The recommended filter paper type, e.g., 'Kalita 155', 'Cafelat Robot paper filter', or 'Standard Basket / None'.")

class BrewStep(BaseModel):
    """A step inside the hand-brewing or espresso protocol."""
    id: int = Field(..., description="The sequence index of the brewing step.")
    title: str = Field(..., description="Header of the step, e.g., 'First Bloom', 'Pre-Infusion', 'Main Extraction'.")
    time_range: str = Field(..., description="Relative time window, e.g., '0:00 - 0:30', '0:10 - 0:45'.")
    water_pour_g: float | None = Field(None, description="Amount of water to pour during this specific step. For pump espresso, set to None.")
    accumulated_water_g: float = Field(..., description="Target cumulative scale weight. Can represent water filled in a manual lever, beverage yield in cup, or total pour-over weight.")
    description: str = Field(..., description="Detailed text detailing the physical action for this step (e.g., pouring, ramping pressure, or turning on pump).")

class RecipeAdjustment(BaseModel):
    """Troubleshooting and diagnostic adjustment for flow and flavor balancing."""
    condition: str = Field(..., description="Observed flavor or extraction defect, e.g., 'If the pull is faster than 25s and tastes sour'.")
    action: str = Field(..., description="The corrected intervention required, e.g., 'Finetune your grind size 1-2 clicks finer'.")

class BrewRecipeResponse(BaseModel):
    """The structured brew recipe payload."""
    introduction: str = Field(..., description="Personalized opening detailing why this specific protocol was selected for this coffee and setup combination.")
    concise_brewing_summary: str = Field(..., description="A very short, one-line summary of the brewing parameters, e.g., 'V60, 15g, 250g, 3 pours. 26 clicks, 93C. 2:30 total.'")
    parameters: BrewParameterSummary = Field(..., description="Key technical parameters summary.")
    steps: list[BrewStep] = Field(..., description="Ordered list of visual recipe steps.")
    adjustments: list[RecipeAdjustment] = Field(..., description="Actionable troubleshooting tips.")

# Initialize fastapi router
router = APIRouter(prefix="/v1/brew-assistant", tags=["Brew Assistant"])

# Secure Zero-Dependency JWT verifier
def base64url_decode(segment: str) -> bytes:
    """Safely decode a base64url-encoded string, handling missing padding."""
    rem = len(segment) % 4
    if rem > 0:
        segment += "=" * (4 - rem)
    return base64.urlsafe_b64decode(segment)

def verify_token(authorization: str | None) -> dict:
    """Verify and decode a signed JWT token using standard libraries."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is required.")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token scheme. Must be Bearer token.")

    token = authorization.split(" ")[1]
    secret = os.getenv("BREW_JWT_SECRET") or "kissaten_brewing_secret_signature_key_2026_change_me_in_prod"

    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise HTTPException(status_code=401, detail="Malformed JWT token signature.")

        header_segment, payload_segment, signature_segment = parts

        # Recalculate HMAC-SHA256 signature
        signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
        expected_sig_bytes = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        expected_sig = base64.urlsafe_b64encode(expected_sig_bytes).decode("utf-8").rstrip("=")

        sig_segment_norm = signature_segment.rstrip("=")
        if not hmac.compare_digest(sig_segment_norm.encode("utf-8"), expected_sig.encode("utf-8")):
            raise HTTPException(status_code=401, detail="JWT signature mismatch or invalid secret.")

        # Parse payload
        payload = json.loads(base64url_decode(payload_segment).decode("utf-8"))

        # Validate expiration
        exp = payload.get("exp")
        if exp and exp < time.time():
            raise HTTPException(status_code=401, detail="Access token has expired.")

        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JWT verification error: {e}")
        raise HTTPException(status_code=401, detail="Unauthorized access token.")


def get_assistant_prompt() -> str:
    """Get the guidelines for generating a specialty coffee recipe."""
    return """
You are a World Barista Champion and master specialty coffee brewing consultant.
Your objective is to provide a customized recipe tailored precisely for the provided coffee bean profile and user hardware parameters.
You MUST dynamically detect if the user is making ESPRESSO or FILTER (Pour-over/Immersion) based on the `brewer` and `roast_profile` provided.

CRITICAL FORMATTING REQUIREMENTS:
Your responses MUST be extremely concise, brief, snappy, and clear. Avoid wordy explanations, historical trivia, and flowery barista buzzwords. Keep the tone completely professional, actionable, and straight-to-the-point for a busy barista working on bar.
- `introduction`: EXACTLY one paragraph, MAXIMUM 2 sentences (e.g., "A customized recipe optimized for a rich, high-extraction espresso to highlight the washed Red Bourbon's sweetness..."). Do NOT say "Welcome" or use storytelling.
- `concise_brewing_summary`: A VERY concise one-line summary. If `previous_brewing_notes` are provided, mimic their style. Otherwise, use the format: "Device, Dose, Total Water, Pour count/structure. Grind, Temp. Total time." (e.g., "Baby O, 12g, 190g, 3 pours. 26 clicks, 93C. 2:30 total.").
- `description` (in steps): MAXIMUM 1-2 sentences, under 18 words. State ONLY the concrete physical actions (e.g., "Ramp to 6-8 bars of pressure, slowly declining to 4 bars to yield 38g.").
- `condition` & `action` (in adjustments): Highly concise, MAXIMUM 1 short sentence each.
- If no specific coffee bean is provided, default to a balanced profile suitable for general brewing with no mention of specific origins, varieties, or processes.

SPECIALTY COFFEE EXTRACTION THEORY (YOU MAY FOLLOW THESE GUIDELINES OR DEVIATE IF THE COFFEE PARAMETERS STRONGLY SUGGEST A DIFFERENT APPROACH):

1. COFFEE BEAN PROCESSING & SOLUBILITY:
   * Washed: Dense and structurally intact. Flow cleanly in filter, handle high pressures in espresso. Recommend higher temperatures (93°C-96°C for light roasts) to extract clarity and florals.
   * Natural & Honey: Brittle, producing MORE fines. For filter, they stall. For espresso, they can channel easily. Recommend slightly coarser grinds, lower temps (90°C-93°C), and gentle pre-infusion.
   * Anaerobic / Carbonic Maceration / Thermal Shock: Cellular structure is highly degraded, making the coffee EXTREMELY soluble. Drop water temps significantly (88°C-91°C) and pull faster/coarser ratios. High temps extract harsh, boozy, or drying astringent flavors.
   * Decaf: Extracts incredibly easily. Grind much finer to slow flow, but use lower temperatures (88°C-90°C) to avoid pulling bitter/roasty notes.

2. VARIETIES, DENSITIES & RATIOS (FILTER vs ESPRESSO):
   * Geisha / Pink Bourbon / Ethiopian Heirloom (Dense/Floral):
     - Filter: Wider ratios (1:16 to 1:17) to separate delicate flavors.
     - Espresso: Longer yields/Turbo shots (1:2.5 to 1:3 ratio) to extract dense floral notes without overwhelming sourness.
   * Standard (Bourbon / Catuai / Typica) / Heavy Naturals:
     - Filter: Standard (1:15 to 1:16).
     - Espresso: Traditional tight ratios (1:1.8 to 1:2.2) to maximize body and sweetness.

3. BREWER / MACHINE DYNAMICS:
   * Pump Espresso Machines (Linea Micra, Bambino, Decent):
     - Focus steps on Puck Prep (WDT, Tamp), Pump Pre-infusion (if available), and Yield target.
     - `total_water_g` in the summary should represent the target beverage yield in the cup.
   * Manual Lever Espresso (Cafelat Robot, Flair):
     - Steps must include filling the chamber with boiling water, manual pre-infusion (e.g., 2 bars), and extraction ramp (e.g., 6-8 bars declining).
     - `total_water_g` can represent water added to the basket (e.g., 65g), while `water_ratio` states the liquid yield (e.g., "1:2.1 (38g beverage yield)").
   * Flat-bottom Filter (Orea, Kalita): Fast vertical flow. Avoid swirling to prevent fines clogging.
   * Cone-shaped Filter (V60): Prone to side bypass. Moderate agitation (center circles) is good.

4. TARGET GRINDER RECOMMENDATIONS:
   * Tailor grind sizes exactly to the specified model.
   * Comandante C40: specify clicks (e.g., '21-23 clicks' for filter, '8-12 clicks' for espresso/Red Clix).
   * 1Zpresso JX-Pro / K-Ultra: specify numeric format (e.g., '1.3.5 setting' or '4.5-5.0').
   * Niche Zero / DF64: specify dial setting (e.g., '12-15' on Niche for espresso, '45-50' for filter).
   * Fellow Ode: specify settings (e.g., '5.0-5.2' - Note: Ode is NOT an espresso grinder, warn gently if they try to use it for espresso).

5. DIAGNOSTIC ADJUSTMENTS:
   * Espresso:
     - Fast/Sour/Thin -> Grind finer, yield slightly more.
     - Slow/Bitter/Harsh/Choking -> Grind coarser, lower temp, reduce peak pressure/yield.
   * Filter:
     - Fast/Sour -> Grind finer, pour slower.
     - Slow/Bitter/Muddy -> Grind coarser, agitate less.

Your response MUST fit the structured output format exactly. Generate a logical, step-by-step recipe that a barista can instantly read and execute while standing at the brew bar or espresso machine."""

# Establish PydanticAI Agent
agent = Agent(
    "google-gla:gemini-3.5-flash",
    output_type=BrewRecipeResponse,
    system_prompt=get_assistant_prompt(),
    model_settings=GeminiModelSettings(gemini_thinking_config={"thinking_budget": 0}),
)

@router.post("/recipe", response_model=BrewRecipeResponse)
async def generate_brew_recipe(
    request_data: BrewRecipeRequest,
    authorization: str | None = Header(None)
):
    """Generate a specialty coffee hand-brew recipe guided by LLM insights."""
    # Enforce authorization
    verify_token(authorization)

    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise HTTPException(
            status_code=503,
            detail="Google Gemini API is not configured on the server. Set GOOGLE_API_KEY.",
        )

    # Format bean info to text prompt
    history_notes_str = "No other historical brewing style notes logged."
    if request_data.previous_brewing_notes:
        history_notes_str = "\n".join(f"- {note}" for note in request_data.previous_brewing_notes)

    prompt = f"""
    Please generate a custom brewing recipe for:
    BEAN: {request_data.bean_name}
    ROASTER: {request_data.roaster_name}
    VARIETY: {request_data.variety or 'Not Specified'}
    PROCESS: {request_data.process or 'Not Specified'}
    ROAST LEVEL: {request_data.roast_level or 'Not Specified'}
    ROAST PROFILE: {request_data.roast_profile or 'Not Specified'}
    COMMERCIAL DESCRIPTION/STORY: {request_data.description or 'No Commercial Description'}
    TASTING NOTES: {', '.join(request_data.tasting_notes) if request_data.tasting_notes else 'None listed'}

    BREWING GEAR AND PARAMETERS:
    DRY DOSE: {request_data.parameters.dose_g}g
    BREW WATER RATIO: {f"1:{request_data.parameters.water_to_coffee_ratio}" if request_data.parameters.water_to_coffee_ratio else "Decide the optimal ratio based on the coffee parameters (normally between 1:15 and 1:17)"}
    BREWER MODEL: {request_data.parameters.brewer}
    GRINDER MODEL: {request_data.parameters.grinder}

    PREVIOUS BARISTA PERSONAL EXPERIENCE / TASTING NOTES:
    {request_data.personal_notes or 'No previous personal notes logged for this coffee.'}

    IMMEDIATE ADDITIONAL GUIDANCE / BATCH STATUS FOR THIS SPECIFIC BREW:
    {request_data.additional_guidance or 'None specified.'}

    HISTORICAL USER BREWING STYLE AND EXPERIENCE (FROM OTHER SESSIONS):
    {history_notes_str}
    """

    try:
        # PydanticAI execution
        result = await agent.run(prompt)
        return result.output
    except Exception as e:
        logger.error(f"Failed to generate brew recipe with Gemini: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate brewing recipe with LLM: {str(e)}",
        )
