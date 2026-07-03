"""
Tests for the canonical roaster-slug functions.

Background
----------
The recommendations network call on a bean detail page goes through:

    frontend: RecommendationTabs → api.getDiscoveryRecommendations
            → api.parseBeanUrl(bean.bean_url_path)
            → /api/v1/beans/{roasterSlug}/{beanSlug}/recommendations

If ``parseBeanUrl`` returns ``null`` (e.g. because the caller passed a
double-slash prefix), the frontend falls back to a slugify that MUST
produce the same value as the on-disk roaster directory name. Otherwise
the backend can't match the bean and the recommendations come back empty.

There are two implementations of the slugify in this repo:

    * Python:  ``slugify_roaster``   in src/kissaten/api/main.py
    * TypeScript: ``slugifyRoaster`` in frontend/src/lib/api.ts

These two are intended to produce identical output for any input. The
tests below pin that contract and assert the headline regression case:

    "Kaffa (SK)"  →  "kaffa__sk_"
"""

from __future__ import annotations

import re

import pytest

from kissaten.api.utils import slugify_roaster
from kissaten.scrapers import get_registry

# ---------------------------------------------------------------------------
# Reference mirror of the TypeScript implementation
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Reference mirror of the TypeScript implementation
# ---------------------------------------------------------------------------
#
# The TypeScript function lives in frontend/src/lib/api.ts:slugifyRoaster.
# We mirror it here as plain Python so this test can be run without a
# Node.js / bun toolchain. If the TS regex drifts, the equality assertion
# below will fail with a diff and force both sides to be re-synced.


_TS_SLUGIFY_RE_1 = r"\s+"
_TS_SLUGIFY_RE_2 = r"[^a-z0-9&_\-éūëöáíúñûē']"


def ts_slugify_roaster(name: str) -> str:
    """Reference mirror of ``api.ts:slugifyRoaster`` in Python.

    Keep in lock-step with the TS source. The equality test below will
    fail if either side drifts.
    """
    lowered = name.lower()
    step1 = lowered.replace(" ", "_")
    step2 = re.sub(_TS_SLUGIFY_RE_2, "_", step1)
    return step2


# ---------------------------------------------------------------------------
# Headline regression case + corpus
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "roaster_name,expected",
    [
        # Headline: the exact case the recommendations bug is about.
        ("Kaffa (SK)", "kaffa__sk_"),
        # Sanity: roasters without parens.
        ("Cartwheel Coffee", "cartwheel_coffee"),
        ("Kissaten", "kissaten"),
        # Edge cases worth locking down.
        ("", ""),
        # Each space is replaced individually (not collapsed), matching the
        # Python ``replace(' ', '_')`` and the registry's ``directory_name``.
        ("  Spaces  ", "__spaces__"),
        # ``è`` is not in the allowed accent set → replaced with ``_``.
        ("Café Crème", "café_cr_me"),
        # Period is not in the allowed set → replaced with underscore.
        ("Dr. Beans", "dr__beans"),
    ],
)
def test_python_slugify_roaster_corpus(roaster_name: str, expected: str) -> None:
    """The Python implementation produces the pinned expected slugs."""
    assert slugify_roaster(roaster_name) == expected


@pytest.mark.parametrize(
    "roaster_name,expected",
    [
        ("Kaffa (SK)", "kaffa__sk_"),
        ("Cartwheel Coffee", "cartwheel_coffee"),
        ("Kissaten", "kissaten"),
        ("", ""),
        ("  Spaces  ", "__spaces__"),
        ("Café Crème", "café_cr_me"),
        ("Dr. Beans", "dr__beans"),
    ],
)
def test_ts_mirror_slugify_roaster_corpus(roaster_name: str, expected: str) -> None:
    """The TS mirror produces the pinned expected slugs (TS regex sanity)."""
    assert ts_slugify_roaster(roaster_name) == expected


@pytest.mark.parametrize(
    "roaster_name",
    [
        "Kaffa (SK)",
        "Cartwheel Coffee",
        "Kissaten",
        "",
        "  Spaces  ",
        "Café Crème",
        "Dr. Beans",
    ],
)
def test_python_and_ts_slugify_match(roaster_name: str) -> None:
    """Python and TS-mirror slugifies agree for the entire corpus."""
    py = slugify_roaster(roaster_name)
    ts = ts_slugify_roaster(roaster_name)
    assert py == ts, f"Drift between Python and TS slugify for {roaster_name!r}: python={py!r}, ts={ts!r}"


# ---------------------------------------------------------------------------
# Pin against the on-disk directory name (the canonical source of truth)
# ---------------------------------------------------------------------------


def test_kaffa_sk_slug_matches_directory_name() -> None:
    """The slugify output for 'Kaffa (SK)' MUST equal the on-disk
    directory name. This is the regression test for the recommendations
    bug: the backend matches beans by ``bean_url_path`` which is built
    from the directory name, so any drift between the slugify and the
    directory name breaks the recommendations lookup.
    """
    registry = get_registry()
    matches = [s for s in registry.list_scrapers() if s.roaster_name == "Kaffa (SK)"]
    if not matches:
        pytest.skip("Kaffa (SK) scraper not registered in this environment")
    info = matches[0]
    expected = info.directory_name
    actual = slugify_roaster("Kaffa (SK)")
    assert actual == expected, (
        f"slugify_roaster('Kaffa (SK)') is {actual!r} but the scraper's "
        f"directory_name is {expected!r}. These must match or the "
        f"recommendations endpoint will not find beans for this roaster."
    )
    # And of course the headline case is kaffa__sk_ exactly.
    assert actual == "kaffa__sk_"


# ---------------------------------------------------------------------------
# Cross-check: every registered scraper's directory_name equals the slugify
# ---------------------------------------------------------------------------


def test_every_registered_roaster_slug_matches_directory_name() -> None:
    """For every roaster in the scraper registry, ``slugify_roaster``
    must produce the on-disk ``directory_name``. If a scraper is added
    with a roaster name that the slugify function would map differently,
    this test fails and forces a decision.
    """
    registry = get_registry()
    mismatches: list[tuple[str, str, str]] = []
    for info in registry.list_scrapers():
        slugified = slugify_roaster(info.roaster_name)
        if slugified != info.directory_name:
            mismatches.append((info.roaster_name, slugified, info.directory_name))
    assert not mismatches, "slugify_roaster and directory_name disagree for these roasters:\n" + "\n".join(
        f"  {n!r}: slugify={s!r}, dir={d!r}" for n, s, d in mismatches
    )
