"""
Tests for canonical slug grouping — ensuring the COALESCE-based region filter
works correctly across all origin endpoints.

Background
----------
When a region has been geocoded, its ``state_canonical`` may differ from the
raw ``region`` string.  For example:

    region='Boquete'  → region_normalized='boquete'  → state_canonical='Chiriquí'
    region='Volcán'   → region_normalized='volcan'    → state_canonical='Chiriquí'

Both rows should be grouped under the canonical slug ``chiriqui``, NOT under
their raw slugs.  The key expression used everywhere is:

    COALESCE(normalize_region_name(o.state_canonical), o.region_normalized)

These tests verify that:
1. Raw slugs that have been subsumed into a canonical group are not reachable.
2. The canonical slug returns the correct (merged) data.
3. No "slug leak" occurs — querying a raw slug does not silently return
   data from the canonical group or vice-versa.
"""

import pytest

from kissaten.api.db import conn, normalize_region_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_divergent_regions() -> list[dict]:
    """Return rows where raw ``region_normalized`` differs from the canonical
    slug computed via ``COALESCE(normalize_region_name(state_canonical), region_normalized)``.

    Each dict has keys: country, raw_region, raw_slug, canonical, canonical_slug.
    """
    rows = conn.execute(
        """
        SELECT DISTINCT
            o.country,
            o.region                                                AS raw_region,
            o.region_normalized                                     AS raw_slug,
            o.state_canonical                                       AS canonical,
            normalize_region_name(o.state_canonical)                AS canonical_slug,
            COALESCE(normalize_region_name(o.state_canonical),
                     o.region_normalized)                           AS effective_slug
        FROM origins o
        WHERE o.state_canonical IS NOT NULL
          AND normalize_region_name(o.state_canonical) != o.region_normalized
        ORDER BY o.country, o.region_normalized
        """
    ).fetchall()
    return [
        {
            "country": r[0],
            "raw_region": r[1],
            "raw_slug": r[2],
            "canonical": r[3],
            "canonical_slug": r[4],
            "effective_slug": r[5],
        }
        for r in rows
    ]


def _get_canonical_groups() -> list[dict]:
    """Return canonical slugs that merge more than one raw region_normalized value.

    Each dict has keys: country, canonical_slug, canonical_name, raw_slugs, bean_count.
    """
    rows = conn.execute(
        """
        SELECT
            o.country,
            COALESCE(normalize_region_name(o.state_canonical),
                     o.region_normalized)                              AS canonical_slug,
            MODE(o.state_canonical)
                FILTER (WHERE o.state_canonical IS NOT NULL
                          AND o.state_canonical != '')                 AS canonical_name,
            LIST(DISTINCT o.region_normalized ORDER BY o.region_normalized) AS raw_slugs,
            COUNT(DISTINCT o.bean_id)                                  AS bean_count
        FROM origins o
        WHERE o.region IS NOT NULL AND o.region != ''
        GROUP BY o.country, canonical_slug
        HAVING COUNT(DISTINCT o.region_normalized) > 1
        ORDER BY o.country, canonical_slug
        """
    ).fetchall()
    return [
        {
            "country": r[0],
            "canonical_slug": r[1],
            "canonical_name": r[2],
            "raw_slugs": r[3],
            "bean_count": r[4],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# 1. Raw slugs that are subsumed should NOT be independently accessible
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_raw_slug_not_in_regions_list(client):
    """A raw slug that has been subsumed into a canonical group must NOT
    appear as its own entry in the regions-list endpoint."""
    divergent = _get_divergent_regions()
    if not divergent:
        pytest.skip("No divergent (raw ≠ canonical) slugs in test data")

    for d in divergent:
        resp = client.get(f"/v1/origins/{d['country']}/regions")
        assert resp.status_code == 200
        slugs_in_list = [
            normalize_region_name(r["region_name"])
            for r in resp.json()["data"]
        ]
        assert d["raw_slug"] not in slugs_in_list, (
            f"Raw slug {d['raw_slug']!r} should be merged into "
            f"{d['canonical_slug']!r} but still appears in {d['country']} "
            f"regions list: {slugs_in_list}"
        )


@pytest.mark.asyncio
async def test_raw_slug_detail_returns_404_or_different_group(client):
    """Fetching a region-detail by a raw slug that has been merged into a
    canonical group should either return 404 (the slug isn't used any more)
    or return data for a *different* group if the raw slug coincidentally
    matches another group's canonical slug.

    It must NOT return data for the canonical group (that would be a leak)."""
    divergent = _get_divergent_regions()
    if not divergent:
        pytest.skip("No divergent slugs in test data")

    for d in divergent:
        resp = client.get(f"/v1/origins/{d['country']}/{d['raw_slug']}")
        if resp.status_code == 404:
            # Expected — the raw slug has no matching canonical group
            continue

        # If it does return 200, the data must NOT be from the canonical group
        # that subsumed this raw slug.
        data = resp.json()["data"]
        slug_used = normalize_region_name(data["region_name"])
        assert slug_used == d["raw_slug"], (
            f"Raw slug {d['raw_slug']!r} for {d['country']} returned data "
            f"for region {data['region_name']!r} (slug={slug_used!r}), "
            f"which differs from the requested slug. This indicates a slug leak."
        )


# ---------------------------------------------------------------------------
# 2. Canonical slug returns merged data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_canonical_slug_returns_all_merged_beans(client):
    """When multiple raw regions map to the same canonical slug, the
    canonical slug's region-detail must contain all beans from every
    constituent raw region."""
    groups = _get_canonical_groups()
    if not groups:
        pytest.skip("No merged canonical groups in test data")

    for g in groups:
        # Expected bean count from the DB-level grouping
        expected_beans = g["bean_count"]

        resp = client.get(f"/v1/origins/{g['country']}/{g['canonical_slug']}")
        if resp.status_code == 404:
            pytest.fail(
                f"Canonical slug {g['canonical_slug']!r} for {g['country']} "
                f"returned 404 but should return {expected_beans} beans "
                f"(merged from raw slugs: {g['raw_slugs']})"
            )

        assert resp.status_code == 200
        detail = resp.json()["data"]
        actual_beans = detail["statistics"]["total_beans"]

        assert actual_beans == expected_beans, (
            f"{g['country']}/{g['canonical_slug']}: expected {expected_beans} "
            f"beans (merged from {g['raw_slugs']}), got {actual_beans}"
        )


@pytest.mark.asyncio
async def test_canonical_slug_display_name_is_canonical(client):
    """The region-detail for a canonical slug should display the canonical
    name (from ``state_canonical``), not an arbitrary raw region string."""
    groups = _get_canonical_groups()
    if not groups:
        pytest.skip("No merged canonical groups in test data")

    for g in groups:
        resp = client.get(f"/v1/origins/{g['country']}/{g['canonical_slug']}")
        if resp.status_code == 404:
            continue

        assert resp.status_code == 200
        detail = resp.json()["data"]
        display_name = detail["region_name"]

        assert display_name == g["canonical_name"], (
            f"{g['country']}/{g['canonical_slug']}: expected display name "
            f"{g['canonical_name']!r}, got {display_name!r}"
        )


# ---------------------------------------------------------------------------
# 3. No slug leak — querying raw slug must not silently return canonical data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_bean_count_inflation_via_raw_slug(client):
    """If a raw slug (e.g. 'boquete') somehow resolves, its bean count
    must not exceed the number of beans whose raw ``region_normalized``
    matches that slug.  If it does, that means beans from the wider
    canonical group leaked through."""
    divergent = _get_divergent_regions()
    if not divergent:
        pytest.skip("No divergent slugs in test data")

    for d in divergent:
        # How many beans the raw slug should have (raw match only)
        raw_count_row = conn.execute(
            """
            SELECT COUNT(DISTINCT bean_id) FROM origins
            WHERE country = ? AND region_normalized = ?
            """,
            [d["country"], d["raw_slug"]],
        ).fetchone()
        max_raw_beans = raw_count_row[0]

        resp = client.get(f"/v1/origins/{d['country']}/{d['raw_slug']}")
        if resp.status_code == 404:
            continue

        assert resp.status_code == 200
        actual_beans = resp.json()["data"]["statistics"]["total_beans"]

        # If this slug happens to match its own canonical group, the count
        # may be larger.  Check if the raw slug IS a canonical slug.
        is_also_canonical = conn.execute(
            """
            SELECT COUNT(*) FROM origins
            WHERE country = ?
              AND COALESCE(normalize_region_name(state_canonical),
                           region_normalized) = ?
              AND region_normalized != ?
            """,
            [d["country"], d["raw_slug"], d["raw_slug"]],
        ).fetchone()[0]

        if is_also_canonical == 0:
            # The raw slug is not a canonical slug for any other group, so
            # the bean count should not exceed raw match count.
            assert actual_beans <= max_raw_beans, (
                f"{d['country']}/{d['raw_slug']}: returned {actual_beans} beans "
                f"but only {max_raw_beans} beans have region_normalized="
                f"{d['raw_slug']!r}. The extra beans leaked from the canonical "
                f"group {d['canonical_slug']!r}."
            )


# ---------------------------------------------------------------------------
# 4. Farm-detail respects canonical grouping
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_farm_detail_uses_canonical_region_filter(client):
    """When fetching a farm under a canonical region slug, the farm-detail
    must only contain beans that belong to that canonical region group."""
    groups = _get_canonical_groups()
    if not groups:
        pytest.skip("No merged canonical groups in test data")

    tested = 0
    for g in groups:
        resp = client.get(f"/v1/origins/{g['country']}/{g['canonical_slug']}")
        if resp.status_code == 404:
            continue
        assert resp.status_code == 200
        detail = resp.json()["data"]

        known_farms = [
            f for f in detail["top_farms"]
            if f["farm_name"] != "Unknown Farm"
        ]

        for farm in known_farms[:3]:
            farm_slug = farm["farm_name"].lower().replace(" ", "-")
            farm_resp = client.get(
                f"/v1/origins/{g['country']}/{g['canonical_slug']}/{farm_slug}"
            )
            if farm_resp.status_code == 404:
                continue
            assert farm_resp.status_code == 200
            farm_data = farm_resp.json()["data"]

            # Every bean returned must be in the canonical region group
            for bean in farm_data["beans"]:
                bean_id_row = conn.execute(
                    "SELECT id FROM coffee_beans WHERE name = ? LIMIT 1",
                    [bean["name"]],
                ).fetchone()
                if not bean_id_row:
                    continue

                in_group = conn.execute(
                    """
                    SELECT COUNT(*) FROM origins
                    WHERE bean_id = ?
                      AND country = ?
                      AND COALESCE(normalize_region_name(state_canonical),
                                   region_normalized) = ?
                    """,
                    [bean_id_row[0], g["country"], g["canonical_slug"]],
                ).fetchone()[0]

                assert in_group > 0, (
                    f"Bean {bean['name']!r} returned by farm-detail "
                    f"{g['country']}/{g['canonical_slug']}/{farm_slug} "
                    f"does not belong to the canonical region group "
                    f"{g['canonical_slug']!r}"
                )
            tested += 1

    if tested == 0:
        pytest.skip("No testable farms in merged canonical groups")


# ---------------------------------------------------------------------------
# 5. End-to-end round-trip: list slug → detail → back to list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_regions_list_slug_round_trips_to_detail(client):
    """Every region_name in the regions-list, when converted to a slug
    via ``normalize_region_name()``, must successfully resolve via the
    region-detail endpoint and return the same region_name."""
    countries = conn.execute(
        """
        SELECT DISTINCT country FROM origins
        WHERE region IS NOT NULL AND region != ''
        ORDER BY country
        """
    ).fetchall()

    failures = []
    for (cc,) in countries:
        list_resp = client.get(f"/v1/origins/{cc}/regions")
        assert list_resp.status_code == 200
        regions = list_resp.json()["data"]

        for r in regions:
            name = r["region_name"]
            slug = normalize_region_name(name)
            if not slug or slug == "unknown-region":
                continue

            detail_resp = client.get(f"/v1/origins/{cc}/{slug}")
            if detail_resp.status_code == 404:
                failures.append(
                    f"{cc}/{slug}: listed as {name!r} but detail returns 404"
                )
                continue

            assert detail_resp.status_code == 200
            detail_name = detail_resp.json()["data"]["region_name"]
            if detail_name != name:
                failures.append(
                    f"{cc}/{slug}: list name={name!r}, "
                    f"detail name={detail_name!r}"
                )

    assert not failures, (
        "Region slug round-trip failures:\n" + "\n".join(failures)
    )
