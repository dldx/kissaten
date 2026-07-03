import re
from pathlib import Path

import polars as pl

country_map = dict(pl.read_csv(Path(__file__).parent.parent / "database/countrycodes.csv").select(["name", "alpha-2"]).iter_rows())

def country_name_to_code(name: str) -> str | None:
    """Convert a country name to its ISO 3166-1 alpha-2 code.

    Args:
        name: Full country name (e.g., "France")

    Returns:
        ISO 3166-1 alpha-2 code (e.g., "FR") or None if not found
    """

    return country_map.get(name, name)


# Allowed character set for canonical roaster slugs. MUST stay in sync with
# the regex in frontend/src/lib/api.ts:slugifyRoaster. The test in
# tests/test_slugify_sync.py pins the equality.
_ROASTER_SLUG_ALLOWED = r"a-z0-9&_\-éūëöáíóúñûē'"


def slugify_roaster(roaster_name: str) -> str:
    """Canonical roaster slug.

    This is the single source of truth for the Python side. It must stay
    in sync with ``slugifyRoaster`` in ``frontend/src/lib/api.ts`` — see
    ``tests/test_slugify_sync.py`` for the equality test.

    Examples
    --------
    >>> slugify_roaster("Kaffa (SK)")
    'kaffa__sk_'
    >>> slugify_roaster("Cartwheel Coffee")
    'cartwheel_coffee'
    """
    name = roaster_name.lower().replace(" ", "_")
    return re.sub(rf"[^{_ROASTER_SLUG_ALLOWED}]", "_", name)
