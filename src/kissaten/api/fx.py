import os
from datetime import datetime, timezone

import dotenv
import httpx
from aiocache import SimpleMemoryCache, cached
from fastapi import APIRouter, HTTPException, Query

from kissaten.api.db import conn
from kissaten.schemas import APIResponse

dotenv.load_dotenv()

# Create router for currency/FX endpoints
router = APIRouter(prefix="/v1", tags=["Currency"])


def create_fx_router() -> APIRouter:
    """Create FX/currency router."""

    @router.get("/currencies", response_model=APIResponse[list[dict]])
    @cached(ttl=600, cache=SimpleMemoryCache)
    async def get_available_currencies():
        """Get all available currencies with their latest rates."""
        try:
            query = """
            SELECT DISTINCT target_currency, rate
            FROM currency_rates
            WHERE fetched_at = (
                SELECT MAX(fetched_at) FROM currency_rates
                WHERE base_currency = 'USD'
            )
            AND base_currency = 'USD'
            ORDER BY target_currency
            """

            results = conn.execute(query).fetchall()

            currencies = []
            for row in results:
                currencies.append(
                    {
                        "code": row[0],
                        "rate_to_usd": row[1],
                        "name": row[0],  # You could add a mapping here for full currency names
                    }
                )

            metadata = {
                "base_currency": "USD",
                "total_currencies": len(currencies),
                "last_updated": "Recent",  # You could get the actual timestamp
            }

            return APIResponse.success_response(data=currencies, metadata=metadata)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    @router.get("/convert", response_model=APIResponse[dict])
    @cached(ttl=600, cache=SimpleMemoryCache)
    async def convert_currency(
        amount: float = Query(..., description="Amount to convert"),
        from_currency: str = Query(..., description="Source currency code"),
        to_currency: str = Query(..., description="Target currency code"),
    ):
        """Convert an amount from one currency to another."""
        try:
            converted_amount = convert_price(amount, from_currency.upper(), to_currency.upper())

            if converted_amount is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot convert from {from_currency} to {to_currency}. Currency rates not available.",
                )

            conversion_data = {
                "original_amount": amount,
                "from_currency": from_currency.upper(),
                "to_currency": to_currency.upper(),
                "converted_amount": round(converted_amount, 2),
                "rate_used": round(converted_amount / amount, 6) if amount != 0 else None,
            }

            return APIResponse.success_response(data=conversion_data)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Conversion error: {str(e)}")

    @router.post("/currencies/update", response_model=APIResponse[dict])
    async def force_update_currencies():
        """Force update of currency exchange rates (admin endpoint)."""
        try:
            await update_currency_rates(conn, force=True)

            # Get count of updated rates
            count_result = conn.execute("""
                SELECT COUNT(*) FROM currency_rates
                WHERE DATE(fetched_at) = CURRENT_DATE
            """).fetchone()

            rates_count = count_result[0] if count_result else 0

            update_info = {
                "message": "Currency rates updated successfully",
                "rates_updated": rates_count,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            return APIResponse.success_response(data=update_info)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Update error: {str(e)}")

    @router.post("/currencies/refresh", response_model=APIResponse[dict])
    async def refresh_currencies():
        """Refresh currency exchange rates only if they're older than 23 hours."""
        try:
            # Check if rates are recent before attempting update
            recent_check = conn.execute("""
                SELECT COUNT(*), MAX(fetched_at) FROM currency_rates
                WHERE fetched_at > NOW() - INTERVAL '23 hours'
                AND base_currency = 'USD'
            """).fetchone()

            if recent_check and recent_check[0] > 0:
                update_info = {
                    "message": "Currency rates are already up to date",
                    "rates_updated": 0,
                    "last_updated": str(recent_check[1]),
                    "skipped": True,
                }
                return APIResponse.success_response(data=update_info)

            await update_currency_rates(conn, force=False)

            # Get count of updated rates
            count_result = conn.execute("""
                SELECT COUNT(*) FROM currency_rates
                WHERE DATE(fetched_at) = CURRENT_DATE
            """).fetchone()

            rates_count = count_result[0] if count_result else 0

            update_info = {
                "message": "Currency rates refreshed successfully",
                "rates_updated": rates_count,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "skipped": False,
            }

            return APIResponse.success_response(data=update_info)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Refresh error: {str(e)}")

    return router

async def fetch_exchange_rates() -> dict | None:
    """
    Fetch current exchange rates from OpenExchangeRates API.

    Returns:
        Dictionary with rates or None if fetch fails
    """
    api_url = (
        f"https://openexchangerates.org/api/latest.json?app_id={os.getenv('OPENEXCHANGERATES_APP_ID', '')}&base=USD"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Error fetching exchange rates: {e}")
        return None


async def update_currency_rates(conn, force: bool = False):
    """
    Update currency rates in database if they're older than 1 day or don't exist.

    Args:
        force: If True, bypass the recent update check and force a new fetch
    """
    # Check if we have recent rates (within last 23 hours to account for timing)
    if not force:
        recent_check = conn.execute("""
            SELECT COUNT(*), MAX(fetched_at) FROM currency_rates
            WHERE fetched_at > NOW() - INTERVAL '23 hours'
            AND base_currency = 'USD'
        """).fetchone()

        if recent_check and recent_check[0] > 0:
            print(f"Exchange rates are up to date (last updated: {recent_check[1]})")
            return

    print("Fetching new exchange rates...")
    rates_data = await fetch_exchange_rates()

    if not rates_data or "rates" not in rates_data:
        print("Failed to fetch exchange rates")
        return

    # Clear old rates (keep only last 7 days)
    conn.execute("""
        DELETE FROM currency_rates
        WHERE fetched_at < CURRENT_DATE - INTERVAL '7 days'
    """)

    # Delete today's rates to replace them (only if we're actually updating)
    conn.execute("""
        DELETE FROM currency_rates
        WHERE DATE(fetched_at) = CURRENT_DATE
    """)

    # Insert new rates
    base_currency = rates_data.get("base", "USD")
    rates = rates_data["rates"]
    data_timestamp = rates_data.get("timestamp")

    # Use a single timestamp for all currencies in this batch (rounded to seconds)
    fetch_timestamp = datetime.now(timezone.utc).replace(microsecond=0)

    # Add the base currency to rates with rate 1.0
    rates[base_currency] = 1.0

    for target_currency, rate in rates.items():
        try:
            conn.execute(
                """
                INSERT INTO currency_rates
                (base_currency, target_currency, rate, fetched_at, data_timestamp)
                VALUES (?, ?, ?, ?, ?)
            """,
                [base_currency, target_currency, float(rate), fetch_timestamp, data_timestamp],
            )
        except Exception as e:
            print(f"Error inserting rate for {target_currency}: {e}")

    print(f"Updated {len(rates)} exchange rates")


def convert_price(amount: float, from_currency: str, to_currency: str) -> float | None:
    """
    Convert price from one currency to another using cached exchange rates.

    Args:
        amount: Amount to convert
        from_currency: Source currency code
        to_currency: Target currency code

    Returns:
        Converted amount or None if conversion not possible
    """
    if not amount or from_currency == to_currency:
        return amount

    try:
        # Get the most recent rates
        if from_currency == "USD":
            # Direct conversion from USD
            rate_result = conn.execute(
                """
                SELECT rate FROM currency_rates
                WHERE base_currency = 'USD' AND target_currency = ?
                ORDER BY fetched_at DESC LIMIT 1
            """,
                [to_currency],
            ).fetchone()

            if rate_result:
                return amount * rate_result[0]

        elif to_currency == "USD":
            # Direct conversion to USD
            rate_result = conn.execute(
                """
                SELECT rate FROM currency_rates
                WHERE base_currency = 'USD' AND target_currency = ?
                ORDER BY fetched_at DESC LIMIT 1
            """,
                [from_currency],
            ).fetchone()

            if rate_result and rate_result[0] != 0:
                return amount / rate_result[0]

        else:
            # Convert via USD (from -> USD -> to)
            from_rate_result = conn.execute(
                """
                SELECT rate FROM currency_rates
                WHERE base_currency = 'USD' AND target_currency = ?
                ORDER BY fetched_at DESC LIMIT 1
            """,
                [from_currency],
            ).fetchone()

            to_rate_result = conn.execute(
                """
                SELECT rate FROM currency_rates
                WHERE base_currency = 'USD' AND target_currency = ?
                ORDER BY fetched_at DESC LIMIT 1
            """,
                [to_currency],
            ).fetchone()

            if from_rate_result and to_rate_result and from_rate_result[0] != 0:
                # Convert to USD first, then to target currency
                usd_amount = amount / from_rate_result[0]
                return usd_amount * to_rate_result[0]

        return None

    except Exception as e:
        print(f"Error converting {amount} from {from_currency} to {to_currency}: {e}")
        return None
