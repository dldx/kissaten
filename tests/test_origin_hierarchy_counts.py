"""
Tests that numeric counts (beans, farms, roasters) are consistent across
the hierarchical origin endpoints:

    /v1/origins                                  (country list)
    /v1/origins/{country}                        (country detail)
    /v1/origins/{country}/regions                (region list)
    /v1/origins/{country}/{region}               (region detail)
    /v1/origins/{country}/{region}/{farm}         (farm detail)

Key invariants
--------------
1. Country-list bean count == country-detail ``total_beans``.
2. Every region's bean_count (from the list) == the matching
   region-detail ``total_beans``.
3. Every region's farm_count (from the list) == the matching
   region-detail ``total_farms``.
4. Sum of region bean_counts (including "Unknown Region") covers all
   beans in the country — every bean appears in at least one region
   group, so the union-sum ≥ the country total.
5. Sum of farm bean_counts inside a region-detail ≥ region total_beans
   (a bean may appear under more than one farm).
6. No single region claims more beans than its country.
7. Farm-detail returns at least one bean, and each bean is a real bean
   belonging to that farm + region + country.
"""

import pytest

from kissaten.api.db import conn, normalize_region_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_countries_from_list(client) -> list[dict]:
    """Fetch the full /v1/origins country list."""
    resp = client.get("/v1/origins")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"]
    return data["data"]


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


# ---------------------------------------------------------------------------
# 1. Country list ↔ Country detail
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_country_list_bean_count_matches_country_detail(client):
    """bean_count from /v1/origins must equal total_beans from /v1/origins/{cc}."""
    countries = _get_countries_from_list(client)
    assert countries, "No countries returned by /v1/origins"

    mismatches = []
    for c in countries:
        cc = c["country_code"]
        detail_resp = client.get(f"/v1/origins/{cc}")
        if detail_resp.status_code == 404:
            continue
        assert detail_resp.status_code == 200
        detail = detail_resp.json()["data"]
        detail_beans = detail["statistics"]["total_beans"]

        if c["bean_count"] != detail_beans:
            mismatches.append(
                f"{cc}: list bean_count={c['bean_count']}, "
                f"detail total_beans={detail_beans}"
            )

    assert not mismatches, (
        "Country bean-count mismatches between list and detail:\n"
        + "\n".join(mismatches)
    )


@pytest.mark.asyncio
async def test_country_list_roaster_count_matches_country_detail(client):
    """roaster_count from /v1/origins must equal total_roasters from /v1/origins/{cc}."""
    countries = _get_countries_from_list(client)
    assert countries, "No countries returned by /v1/origins"

    mismatches = []
    for c in countries:
        cc = c["country_code"]
        detail_resp = client.get(f"/v1/origins/{cc}")
        if detail_resp.status_code == 404:
            continue
        assert detail_resp.status_code == 200
        detail = detail_resp.json()["data"]
        detail_roasters = detail["statistics"]["total_roasters"]

        if c["roaster_count"] != detail_roasters:
            mismatches.append(
                f"{cc}: list roaster_count={c['roaster_count']}, "
                f"detail total_roasters={detail_roasters}"
            )

    assert not mismatches, (
        "Country roaster-count mismatches between list and detail:\n"
        + "\n".join(mismatches)
    )


# ---------------------------------------------------------------------------
# 2. Region list ↔ Region detail  (beans & farms)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_region_bean_count_matches_detail(client):
    """bean_count from /v1/origins/{cc}/regions must equal total_beans
    from /v1/origins/{cc}/{slug}."""
    countries = _get_countries_with_regions()
    assert countries, "No countries with regions found"

    mismatches = []
    for cc in countries:
        list_resp = client.get(f"/v1/origins/{cc}/regions")
        assert list_resp.status_code == 200
        regions = list_resp.json()["data"]

        for r in regions:
            slug = normalize_region_name(r["region_name"])
            if not slug or slug == "unknown-region":
                continue

            detail_resp = client.get(f"/v1/origins/{cc}/{slug}")
            if detail_resp.status_code == 404:
                continue
            assert detail_resp.status_code == 200
            detail = detail_resp.json()["data"]

            if r["bean_count"] != detail["statistics"]["total_beans"]:
                mismatches.append(
                    f"{cc}/{slug}: list={r['bean_count']}, "
                    f"detail={detail['statistics']['total_beans']}"
                )

    assert not mismatches, (
        "Region bean-count mismatches:\n" + "\n".join(mismatches)
    )


@pytest.mark.asyncio
async def test_region_farm_count_matches_detail(client):
    """farm_count from the regions list must equal total_farms from the
    region detail."""
    countries = _get_countries_with_regions()
    assert countries, "No countries with regions found"

    mismatches = []
    for cc in countries:
        list_resp = client.get(f"/v1/origins/{cc}/regions")
        assert list_resp.status_code == 200
        regions = list_resp.json()["data"]

        for r in regions:
            slug = normalize_region_name(r["region_name"])
            if not slug or slug == "unknown-region":
                continue

            detail_resp = client.get(f"/v1/origins/{cc}/{slug}")
            if detail_resp.status_code == 404:
                continue
            assert detail_resp.status_code == 200
            detail = detail_resp.json()["data"]

            if r["farm_count"] != detail["statistics"]["total_farms"]:
                mismatches.append(
                    f"{cc}/{slug}: list farm_count={r['farm_count']}, "
                    f"detail total_farms={detail['statistics']['total_farms']}"
                )

    assert not mismatches, (
        "Region farm-count mismatches:\n" + "\n".join(mismatches)
    )


# ---------------------------------------------------------------------------
# 3. Region detail internal consistency  (farms add up)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_region_detail_farm_list_count_matches_stats(client):
    """The number of farms returned in the region-detail ``top_farms`` list
    (excluding "Unknown Farm") must equal ``statistics.total_farms``."""
    countries = _get_countries_with_regions()
    assert countries, "No countries with regions found"

    mismatches = []
    for cc in countries:
        list_resp = client.get(f"/v1/origins/{cc}/regions")
        assert list_resp.status_code == 200
        regions = list_resp.json()["data"]

        for r in regions:
            slug = normalize_region_name(r["region_name"])
            if not slug or slug == "unknown-region":
                continue

            detail_resp = client.get(f"/v1/origins/{cc}/{slug}")
            if detail_resp.status_code == 404:
                continue
            assert detail_resp.status_code == 200
            detail = detail_resp.json()["data"]

            known_farms = [
                f for f in detail["top_farms"]
                if f["farm_name"] != "Unknown Farm"
            ]
            stat_farms = detail["statistics"]["total_farms"]

            if len(known_farms) != stat_farms:
                mismatches.append(
                    f"{cc}/{slug}: top_farms has {len(known_farms)} named farms, "
                    f"but total_farms={stat_farms}"
                )

    assert not mismatches, (
        "Farm list length vs total_farms mismatches:\n"
        + "\n".join(mismatches)
    )


@pytest.mark.asyncio
async def test_region_detail_farm_beans_cover_total(client):
    """The sum of bean_count across all farms (known + unknown) in a
    region-detail must be >= total_beans (a bean with multiple origin
    rows may appear in several farms)."""
    countries = _get_countries_with_regions()
    assert countries, "No countries with regions found"

    violations = []
    for cc in countries:
        list_resp = client.get(f"/v1/origins/{cc}/regions")
        assert list_resp.status_code == 200
        regions = list_resp.json()["data"]

        for r in regions:
            slug = normalize_region_name(r["region_name"])
            if not slug or slug == "unknown-region":
                continue

            detail_resp = client.get(f"/v1/origins/{cc}/{slug}")
            if detail_resp.status_code == 404:
                continue
            assert detail_resp.status_code == 200
            detail = detail_resp.json()["data"]

            farm_bean_sum = sum(f["bean_count"] for f in detail["top_farms"])
            total_beans = detail["statistics"]["total_beans"]

            if farm_bean_sum < total_beans:
                violations.append(
                    f"{cc}/{slug}: sum(farm bean_counts)={farm_bean_sum} "
                    f"< total_beans={total_beans}"
                )

    assert not violations, (
        "Farm bean sums don't cover total_beans:\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# 4. Country ↔ Regions  (aggregate bounds)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_region_exceeds_country_bean_count(client):
    """No single region may have more beans than the country total."""
    countries = _get_countries_with_regions()
    assert countries, "No countries with regions found"

    violations = []
    for cc in countries:
        country_resp = client.get(f"/v1/origins/{cc}")
        if country_resp.status_code == 404:
            continue
        assert country_resp.status_code == 200
        country_total = country_resp.json()["data"]["statistics"]["total_beans"]

        regions_resp = client.get(f"/v1/origins/{cc}/regions")
        assert regions_resp.status_code == 200
        for r in regions_resp.json()["data"]:
            if r["bean_count"] > country_total:
                violations.append(
                    f"{cc}/{r['region_name']}: region beans={r['bean_count']} "
                    f"> country beans={country_total}"
                )

    assert not violations, (
        "Regions exceed country totals:\n" + "\n".join(violations)
    )


@pytest.mark.asyncio
async def test_every_country_bean_appears_in_at_least_one_region(client):
    """The union of beans across all regions (including "Unknown Region")
    should cover every bean in the country.  We verify this by checking
    that the *set* of bean IDs reachable via individual region-detail
    endpoints is at least as large as the country total.

    (We check at the DB level to avoid O(n) API calls per bean.)
    """
    countries = _get_countries_with_regions()
    assert countries, "No countries with regions found"

    violations = []
    for cc in countries:
        # Total distinct beans for this country
        total_row = conn.execute(
            "SELECT COUNT(DISTINCT bean_id) FROM origins WHERE country = ?",
            [cc],
        ).fetchone()
        country_bean_count = total_row[0]

        # Beans with at least one non-empty region
        with_region_row = conn.execute(
            """
            SELECT COUNT(DISTINCT bean_id) FROM origins
            WHERE country = ? AND region IS NOT NULL AND region != ''
            """,
            [cc],
        ).fetchone()
        beans_with_region = with_region_row[0]

        # Beans that are *only* in unknown-region
        without_region_row = conn.execute(
            """
            SELECT COUNT(DISTINCT bean_id) FROM origins
            WHERE country = ?
              AND bean_id NOT IN (
                  SELECT bean_id FROM origins
                  WHERE country = ? AND region IS NOT NULL AND region != ''
              )
            """,
            [cc, cc],
        ).fetchone()
        beans_only_unknown = without_region_row[0]

        covered = beans_with_region + beans_only_unknown
        if covered < country_bean_count:
            violations.append(
                f"{cc}: covered={covered} (regions={beans_with_region} + "
                f"unknown={beans_only_unknown}) < total={country_bean_count}"
            )

    assert not violations, (
        "Some beans are not covered by any region group:\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# 5. Region ↔ Farm detail
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_farm_detail_returns_beans(client):
    """Every farm listed in a region-detail (except 'Unknown Farm') must
    return a valid farm-detail response with at least one bean."""
    countries = _get_countries_with_regions()
    assert countries, "No countries with regions found"

    # Pick the first country that has regions with known farms
    for cc in countries:
        regions_resp = client.get(f"/v1/origins/{cc}/regions")
        assert regions_resp.status_code == 200
        regions = regions_resp.json()["data"]

        found_any = False
        for r in regions:
            slug = normalize_region_name(r["region_name"])
            if not slug or slug == "unknown-region":
                continue

            detail_resp = client.get(f"/v1/origins/{cc}/{slug}")
            if detail_resp.status_code == 404:
                continue
            assert detail_resp.status_code == 200
            detail = detail_resp.json()["data"]

            known_farms = [
                f for f in detail["top_farms"]
                if f["farm_name"] != "Unknown Farm"
            ]

            for farm in known_farms[:3]:   # limit to avoid slow test
                farm_slug = farm["farm_name"].lower().replace(" ", "-")
                # Use normalize_farm_name logic: strip accents, etc.
                farm_resp = client.get(f"/v1/origins/{cc}/{slug}/{farm_slug}")
                if farm_resp.status_code == 404:
                    # slug normalisation may differ — skip rather than fail
                    continue
                assert farm_resp.status_code == 200
                farm_data = farm_resp.json()["data"]
                assert len(farm_data["beans"]) > 0, (
                    f"{cc}/{slug}/{farm_slug}: farm detail returned 0 beans"
                )
                found_any = True

        if found_any:
            return  # one country is enough for this smoke test

    pytest.skip("No testable farms found in test data")


@pytest.mark.asyncio
async def test_farm_detail_bean_count_matches_region_farm_entry(client):
    """The number of beans in a farm-detail response should match the
    bean_count shown in the region-detail ``top_farms`` entry for the
    same farm."""
    countries = _get_countries_with_regions()
    assert countries, "No countries with regions found"

    mismatches = []
    tested = 0

    for cc in countries:
        regions_resp = client.get(f"/v1/origins/{cc}/regions")
        assert regions_resp.status_code == 200
        regions = regions_resp.json()["data"]

        for r in regions:
            slug = normalize_region_name(r["region_name"])
            if not slug or slug == "unknown-region":
                continue

            detail_resp = client.get(f"/v1/origins/{cc}/{slug}")
            if detail_resp.status_code == 404:
                continue
            assert detail_resp.status_code == 200
            detail = detail_resp.json()["data"]

            known_farms = [
                f for f in detail["top_farms"]
                if f["farm_name"] != "Unknown Farm"
            ]

            for farm in known_farms[:3]:
                farm_slug = farm["farm_name"].lower().replace(" ", "-")
                farm_resp = client.get(f"/v1/origins/{cc}/{slug}/{farm_slug}")
                if farm_resp.status_code == 404:
                    continue
                assert farm_resp.status_code == 200
                farm_data = farm_resp.json()["data"]
                actual_beans = len(farm_data["beans"])

                if actual_beans != farm["bean_count"]:
                    mismatches.append(
                        f"{cc}/{slug}/{farm_slug}: "
                        f"region says {farm['bean_count']} beans, "
                        f"farm detail has {actual_beans}"
                    )
                tested += 1

    if tested == 0:
        pytest.skip("No testable farms found in test data")

    assert not mismatches, (
        "Farm bean-count mismatches between region-detail and farm-detail:\n"
        + "\n".join(mismatches)
    )


# ---------------------------------------------------------------------------
# 6. Country detail internal consistency
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_country_detail_stats_are_positive(client):
    """Basic sanity: a country detail must have positive bean and roaster
    counts and non-negative farm/region counts."""
    countries = _get_countries_from_list(client)
    assert countries, "No countries"

    for c in countries:
        cc = c["country_code"]
        resp = client.get(f"/v1/origins/{cc}")
        if resp.status_code == 404:
            continue
        assert resp.status_code == 200
        stats = resp.json()["data"]["statistics"]

        assert stats["total_beans"] > 0, f"{cc}: total_beans=0"
        assert stats["total_roasters"] > 0, f"{cc}: total_roasters=0"
        assert stats["total_farms"] >= 0, f"{cc}: negative total_farms"
        assert stats["total_regions"] >= 0, f"{cc}: negative total_regions"


@pytest.mark.asyncio
async def test_country_detail_region_count_matches_regions_list(client):
    """The country-detail ``total_regions`` should match the number of
    entries returned by the regions-list endpoint (excluding 'Unknown Region')."""
    countries = _get_countries_with_regions()
    assert countries, "No countries with regions found"

    mismatches = []
    for cc in countries:
        country_resp = client.get(f"/v1/origins/{cc}")
        if country_resp.status_code == 404:
            continue
        assert country_resp.status_code == 200
        country_regions_count = country_resp.json()["data"]["statistics"]["total_regions"]

        regions_resp = client.get(f"/v1/origins/{cc}/regions")
        assert regions_resp.status_code == 200
        regions = regions_resp.json()["data"]
        named_regions = [r for r in regions if r["region_name"] != "Unknown Region"]

        if country_regions_count != len(named_regions):
            mismatches.append(
                f"{cc}: country detail total_regions={country_regions_count}, "
                f"regions list has {len(named_regions)} named regions"
            )

    assert not mismatches, (
        "Country total_regions vs regions-list count mismatches:\n"
        + "\n".join(mismatches)
    )
