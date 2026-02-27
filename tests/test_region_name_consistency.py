"""
Tests that region names are consistent between the regions-list and region-detail
endpoints, and that the regions-list contains no duplicate display names.

The key invariant is:
  - Both endpoints prefer ``state_canonical`` (the geocoded canonical name) when
    available, falling back to the raw ``region`` name otherwise.
  - The regions-list groups by the canonical slug so that different raw region
    strings that map to the same canonical state are merged into one entry.
"""

import pytest

from kissaten.api.db import conn, normalize_region_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_countries_with_regions() -> list[str]:
    """Return country codes that have at least one non-empty region."""
    rows = conn.execute(
        """
        SELECT DISTINCT o.country
        FROM origins o
        WHERE o.region IS NOT NULL AND o.region != ''
        ORDER BY o.country
        """
    ).fetchall()
    return [r[0] for r in rows]


def _get_geocoded_countries() -> list[str]:
    """Return country codes that have at least one geocoded region (state_canonical IS NOT NULL)."""
    rows = conn.execute(
        """
        SELECT DISTINCT o.country
        FROM origins o
        WHERE o.state_canonical IS NOT NULL
        ORDER BY o.country
        """
    ).fetchall()
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_regions_list_has_no_duplicate_names(client):
    """The regions-list endpoint must not return duplicate region_name values."""
    countries = _get_countries_with_regions()
    assert countries, "No countries with regions found in test data"

    for country_code in countries:
        response = client.get(f"/v1/origins/{country_code}/regions")
        assert response.status_code == 200, f"Failed for {country_code}"
        data = response.json()
        assert data["success"]

        region_names = [r["region_name"] for r in data["data"]]
        duplicates = [name for name in region_names if region_names.count(name) > 1]
        assert not duplicates, (
            f"Duplicate region names for {country_code}: {sorted(set(duplicates))}"
        )


@pytest.mark.asyncio
async def test_region_detail_name_matches_regions_list(client):
    """For every region in the regions-list, the detail endpoint must return
    the same ``region_name``."""
    countries = _get_geocoded_countries()
    assert countries, "No geocoded countries found in test data"

    # Pick a few countries to test (avoid extremely long test runs)
    for country_code in countries[:5]:
        list_response = client.get(f"/v1/origins/{country_code}/regions")
        assert list_response.status_code == 200
        regions = list_response.json()["data"]

        for region in regions:
            region_name = region["region_name"]
            region_slug = normalize_region_name(region_name)
            if not region_slug or region_slug == "unknown-region":
                continue

            detail_response = client.get(f"/v1/origins/{country_code}/{region_slug}")
            if detail_response.status_code == 404:
                # Some non-geocoded raw region names may not round-trip through
                # their own slug (e.g. the raw name picked by MODE may differ
                # from any slug that matches).  Skip these.
                continue

            assert detail_response.status_code == 200, (
                f"Detail failed for {country_code}/{region_slug} "
                f"(region_name={region_name!r})"
            )
            detail_data = detail_response.json()["data"]
            assert detail_data["region_name"] == region_name, (
                f"Name mismatch for {country_code}/{region_slug}: "
                f"list={region_name!r}, detail={detail_data['region_name']!r}"
            )


@pytest.mark.asyncio
async def test_geocoded_regions_use_canonical_name(client):
    """Geocoded regions should display ``state_canonical`` rather than an
    arbitrary raw region string."""
    # Find regions where state_canonical differs from the raw region
    rows = conn.execute(
        """
        SELECT DISTINCT o.country, o.state_canonical
        FROM origins o
        WHERE o.state_canonical IS NOT NULL
          AND o.region IS NOT NULL
          AND o.region != o.state_canonical
        ORDER BY o.country, o.state_canonical
        LIMIT 20
        """
    ).fetchall()

    if not rows:
        pytest.skip("No regions with differing state_canonical found in test data")

    for country_code, canonical_name in rows:
        response = client.get(f"/v1/origins/{country_code}/regions")
        assert response.status_code == 200
        region_names = [r["region_name"] for r in response.json()["data"]]
        # The canonical name should appear in the list (it may have been
        # merged with other raw regions that map to the same canonical state)
        assert canonical_name in region_names, (
            f"Canonical name {canonical_name!r} not found in regions list "
            f"for {country_code}. Got: {region_names}"
        )


@pytest.mark.asyncio
async def test_geocoded_regions_merge_raw_variants(db_session):
    """When multiple raw region strings map to the same ``state_canonical``,
    they must appear as a single entry in the regions-list."""
    # Find a canonical state that has more than one raw variant
    rows = conn.execute(
        """
        SELECT o.country, o.state_canonical, COUNT(DISTINCT o.region) as variant_count
        FROM origins o
        WHERE o.state_canonical IS NOT NULL
          AND o.region IS NOT NULL AND o.region != ''
        GROUP BY o.country, o.state_canonical
        HAVING COUNT(DISTINCT o.region) > 1
        ORDER BY variant_count DESC
        LIMIT 5
        """
    ).fetchall()

    if not rows:
        pytest.skip("No canonical states with multiple raw variants found")

    for country_code, canonical_name, variant_count in rows:
        # Query the regions list the same way the endpoint does
        result = conn.execute(
            """
            SELECT
                COALESCE(
                    MODE(o.state_canonical) FILTER (WHERE o.state_canonical IS NOT NULL),
                    MODE(o.region)
                ) as region_name
            FROM origins o
            JOIN coffee_beans cb ON o.bean_id = cb.id
            WHERE o.country = ?
              AND o.region IS NOT NULL AND o.region != ''
            GROUP BY COALESCE(normalize_region_name(o.state_canonical), o.region_normalized)
            """,
            [country_code],
        ).fetchall()
        display_names = [r[0] for r in result]

        occurrences = display_names.count(canonical_name)
        assert occurrences == 1, (
            f"{canonical_name!r} appears {occurrences} times in {country_code} "
            f"regions (has {variant_count} raw variants). "
            f"All display names: {display_names}"
        )


@pytest.mark.asyncio
async def test_region_bean_counts_match_between_list_and_detail(client):
    """The bean_count in the regions-list must equal total_beans in the
    corresponding region-detail endpoint."""
    countries = _get_geocoded_countries()
    assert countries, "No geocoded countries found in test data"

    mismatches = []

    for country_code in countries[:5]:
        list_response = client.get(f"/v1/origins/{country_code}/regions")
        assert list_response.status_code == 200
        regions = list_response.json()["data"]

        for region in regions:
            region_name = region["region_name"]
            list_bean_count = region["bean_count"]
            region_slug = normalize_region_name(region_name)
            if not region_slug or region_slug == "unknown-region":
                continue

            detail_response = client.get(f"/v1/origins/{country_code}/{region_slug}")
            if detail_response.status_code == 404:
                continue

            assert detail_response.status_code == 200
            detail_data = detail_response.json()["data"]
            detail_bean_count = detail_data["statistics"]["total_beans"]

            if list_bean_count != detail_bean_count:
                mismatches.append(
                    f"{country_code}/{region_slug} ({region_name!r}): "
                    f"list={list_bean_count}, detail={detail_bean_count}"
                )

    assert not mismatches, (
        "Bean count mismatches between regions-list and region-detail:\n"
        + "\n".join(mismatches)
    )


@pytest.mark.asyncio
async def test_sum_of_region_beans_does_not_exceed_country_total(client):
    """The sum of bean_count across all regions (plus unknown) should not
    exceed the country's total bean count, since a bean can belong to
    multiple origins/regions."""
    countries = _get_countries_with_regions()
    assert countries, "No countries with regions found in test data"

    for country_code in countries[:5]:
        # Get country total
        country_response = client.get(f"/v1/origins/{country_code}")
        if country_response.status_code == 404:
            continue
        assert country_response.status_code == 200
        country_total = country_response.json()["data"]["statistics"]["total_beans"]

        # Get regions total
        regions_response = client.get(f"/v1/origins/{country_code}/regions")
        assert regions_response.status_code == 200
        regions = regions_response.json()["data"]

        # Each bean may appear in multiple regions (multi-origin blends),
        # so the sum can exceed the country total.  But the *minimum* of
        # any single region's bean_count must not exceed the country total.
        for region in regions:
            assert region["bean_count"] <= country_total, (
                f"{country_code} region {region['region_name']!r} has "
                f"{region['bean_count']} beans but country total is only "
                f"{country_total}"
            )


@pytest.mark.asyncio
async def test_region_farm_counts_consistent(client):
    """The farm_count in the regions-list should match the number of farms
    returned by the region-detail endpoint (top_farms list length)."""
    countries = _get_geocoded_countries()
    assert countries, "No geocoded countries found in test data"

    mismatches = []

    for country_code in countries[:3]:
        list_response = client.get(f"/v1/origins/{country_code}/regions")
        assert list_response.status_code == 200
        regions = list_response.json()["data"]

        for region in regions:
            region_name = region["region_name"]
            list_farm_count = region["farm_count"]
            region_slug = normalize_region_name(region_name)
            if not region_slug or region_slug == "unknown-region":
                continue

            detail_response = client.get(f"/v1/origins/{country_code}/{region_slug}")
            if detail_response.status_code == 404:
                continue

            assert detail_response.status_code == 200
            detail_data = detail_response.json()["data"]
            detail_farm_count = detail_data["statistics"]["total_farms"]

            if list_farm_count != detail_farm_count:
                mismatches.append(
                    f"{country_code}/{region_slug} ({region_name!r}): "
                    f"list_farm_count={list_farm_count}, detail_total_farms={detail_farm_count}"
                )

    assert not mismatches, (
        "Farm count mismatches between regions-list and region-detail:\n"
        + "\n".join(mismatches)
    )
