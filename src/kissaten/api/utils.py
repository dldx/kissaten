from pathlib import Path

import polars as pl

country_map = dict(pl.read_csv(Path(__file__).parent.parent / "database/countrycodes.csv").select(["name", "alpha-2"]).iter_rows())

def country_name_to_code(name: str) -> str | None:
    """Convert a country name to its ISO 3166-1 alpha-2 code.

    Args:
        name: Full country name (e.g., "France")

    Returns:
        ISO 3166-1 alpha-2 country code (e.g., "FR") or None if not found
    """

    return country_map.get(name, name)
