"""
Shared storage and database access logic for farm deduplication.
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from kissaten.api.db import conn
from kissaten.dedup import normalizer

# Calculate paths relative to project root
# We assume this file is in src/kissaten/dedup/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
MAPPING_FILE = PROJECT_ROOT / "src" / "kissaten" / "database" / "farm_mappings.json"


def generate_mapping_file(all_clusters: list[dict]) -> None:
    """
    Generate the farm mapping file in the database directory.

    Output format:
    [
        {
            "country": "CO",
            "region": "huila",  # This is the canonical region slug
            "canonical_farm_name": "Quebraditas",
            "normalized_farm_names": ["quebraditas", "quebraditas-coffee-farm"]
        },
        ...
    ]
    """
    output_data = []

    for cluster in all_clusters:
        # Export all confirmed clusters (including singletons) to ensure consistent canonicalization
        # This makes farm_mappings.json the source of truth for all known farms
        country = cluster.get("country_code")
        region = cluster.get("region_slug")
        canonical = cluster["canonical_name"]

        # Get all normalized names found in this cluster
        normalized_names = sorted(list({e["farm_normalized"] for e in cluster["entries"]}))

        output_data.append(
            {
                "country": country,
                "region": region,
                "canonical_farm_name": canonical,
                "normalized_farm_names": normalized_names,
            }
        )

    # Sort for deterministic output
    output_data.sort(key=lambda x: (x["country"], x["region"], x["canonical_farm_name"]))

    MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(MAPPING_FILE, "w") as f:
        json.dump(output_data, f, indent=2)


def save_mappings(all_clusters: list[dict]) -> None:
    """
    Save clusters to farm_mappings.json.
    This is the main function to persist cluster state.

    Args:
        all_clusters: List of cluster dictionaries to save
    """
    generate_mapping_file(all_clusters)


def get_processed_regions(country_code: str | None = None) -> list[str]:
    """
    Determine which regions have been processed by checking farm_mappings.json.

    Args:
        country_code: Optional filter by country code

    Returns:
        List of region keys in format "COUNTRY:region_slug"
    """
    mappings = load_mappings(country_code)

    # Extract unique (country, region) pairs
    regions = set()
    for m in mappings:
        country = m.get("country")
        region = m.get("region", "")
        if country:
            regions.add(f"{country}:{region}")

    return sorted(list(regions))


def load_all_clusters_from_mappings(country_code: str | None = None) -> list[dict]:
    """
    Load all existing clusters from farm_mappings.json.

    This is used when rerunning the script to preserve existing mappings
    from regions that aren't being reprocessed.

    Args:
        country_code: Optional filter by country code

    Returns:
        List of cluster dictionaries
    """
    mappings = load_mappings(country_code)

    clusters = []
    for m in mappings:
        # Convert each mapping back to cluster format
        clusters.append(
            {
                "canonical_name": m["canonical_farm_name"],
                "entries": [{"farm_normalized": norm} for norm in m["normalized_farm_names"]],
                "total_bean_count": 0,  # Not critical for mapping file
                "confidence": 1.0,
                "country_code": m.get("country"),
                "region_slug": m.get("region"),
                "region_name": "",
            }
        )

    return clusters


def update_region_clusters(country_code: str, region_slug: str, clusters: list[dict]) -> None:
    """
    Update mappings for a specific region while preserving other regions.

    Args:
        country_code: ISO country code
        region_slug: Region slug being updated
        clusters: New cluster list for this region
    """
    # Load all existing mappings
    all_mappings = load_mappings()

    # Remove existing mappings for this specific region
    filtered_mappings = [
        m for m in all_mappings if not (m.get("country") == country_code and m.get("region") == region_slug)
    ]

    # Convert current mappings back to cluster format for merging
    # Group by country/region to get existing clusters from other regions
    existing_clusters = []
    region_groups = {}
    for m in filtered_mappings:
        key = (m.get("country"), m.get("region"))
        if key not in region_groups:
            region_groups[key] = []
        region_groups[key].append(m)

    # Convert mapping groups back to cluster format
    for (country, region), mappings in region_groups.items():
        for m in mappings:
            # Create a minimal cluster entry
            existing_clusters.append(
                {
                    "canonical_name": m["canonical_farm_name"],
                    "entries": [{"farm_normalized": norm} for norm in m["normalized_farm_names"]],
                    "total_bean_count": 0,  # Not critical for mapping file
                    "confidence": 1.0,
                    "country_code": country,
                    "region_slug": region,
                    "region_name": "",
                }
            )

    # Combine with new clusters for this region
    all_clusters = existing_clusters + clusters

    # Save everything
    generate_mapping_file(all_clusters)


def load_mappings(country_code: str | None = None) -> list[dict]:
    """
    Load farm mappings from JSON file.

    Args:
        country_code: Optional filter by country code.

    Returns:
        List of mapping dictionaries.
    """
    if not MAPPING_FILE.exists():
        return []

    try:
        with open(MAPPING_FILE, "r") as f:
            data = json.load(f)

        if country_code:
            return [m for m in data if m.get("country") == country_code]
        return data
    except json.JSONDecodeError:
        return []


def rehydrate_clusters_from_mappings(country_code: str, region_slug: str) -> list[dict]:
    """
    Reconstruct cluster objects for a region by combining DB data with saved mappings.

    Handles:
    1. Known clusters: Groups farms based on 'farm_mappings.json'.
    2. Region moves: Finds mappings regardless of their old region in JSON.
    3. New/Unclustered: Farms not in mappings are returned as singleton clusters.

    Args:
        country_code: ISO country code
        region_slug: Region slug to process

    Returns:
        List of cluster objects compatible with TUI/Script state.
    """
    from collections import defaultdict

    # 1. Load ALL mappings for this country to build lookup table
    # We need country-wide scope to detect if a farm moved regions
    mappings = load_mappings(country_code)

    # Map: normalized_name -> canonical_name
    farm_to_canonical = {}
    for m in mappings:
        canonical = m["canonical_farm_name"]
        for norm_name in m["normalized_farm_names"]:
            farm_to_canonical[norm_name] = canonical

    # 2. Get current raw farms from DB for this region
    # dict[normalized_name -> list[entries]]
    db_farms = get_farms_for_region(country_code, region_slug)

    # 3. Group DB entries by their mapped canonical name
    # canonical_name -> list of all entries (flattened)
    cluster_groups = defaultdict(list)
    unclustered_farms = []

    for norm_name, entries in db_farms.items():
        if norm_name in farm_to_canonical:
            canonical = farm_to_canonical[norm_name]
            cluster_groups[canonical].extend(entries)
        else:
            # Unclustered farm - create singleton cluster
            unclustered_farms.extend(entries)

    # 4. Construct Cluster Objects from known mappings
    clusters = []
    for canonical, entries in cluster_groups.items():
        total_beans = sum(e["bean_count"] for e in entries)
        # Get region name from first entry
        region_name = entries[0].get("region_name", "")

        clusters.append(
            {
                "canonical_name": canonical,
                "entries": entries,
                "total_bean_count": total_beans,
                "confidence": 1.0,  # Existing mappings imply 100% confidence
                "country_code": country_code,
                "region_slug": region_slug,  # Confirmed current location from DB
                "region_name": region_name,
            }
        )

    # 5. Add unclustered farms as singleton clusters
    for entry in unclustered_farms:
        clusters.append(
            {
                "canonical_name": entry["farm_name"],
                "entries": [entry],
                "total_bean_count": entry["bean_count"],
                "confidence": 1.0,
                "country_code": country_code,
                "region_slug": region_slug,
                "region_name": entry.get("region_name", ""),
            }
        )

    return clusters


def get_all_regions(country_code: str | None = None) -> list[tuple[str, str, str]]:
    """
    Get all regions from the database with canonical state mapping.

    Args:
        country_code: Optional country code to filter by (e.g., 'CO', 'ET')

    Returns:
        List of tuples: (country_code, canonical_region_name, canonical_region_slug)
    """
    query = """
        SELECT
            o.country,
            COALESCE(get_canonical_state(o.country, o.region), o.region, 'Unknown Region') as canonical_region,
            normalize_region_name(COALESCE(get_canonical_state(o.country, o.region), o.region, 'Unknown Region')) as canonical_slug
        FROM origins o
        WHERE o.country IS NOT NULL
    """

    params = []
    if country_code:
        query += " AND o.country = ?"
        params.append(country_code.upper())

    query += """
        GROUP BY o.country, canonical_region, canonical_slug
        ORDER BY o.country, canonical_region
    """

    rows = conn.execute(query, params).fetchall()

    regions = []
    for row in rows:
        country = row[0]
        region_name = row[1]
        region_slug = row[2]
        regions.append((country, region_name, f"{country}:{region_slug}"))

    return regions


def get_farms_for_region(country_code: str, region_slug: str) -> dict[str, list[dict]]:
    """
    Get all farms for a specific region, grouped by normalized farm name.

    Returns:
        Dict mapping farm_normalized -> list of farm entries
    """
    # Handle unknown region special case
    if region_slug == "unknown-region":
        region_filter = "(o.region IS NULL OR o.region = '')"
        params = [country_code]
    else:
        region_filter = (
            "normalize_region_name(COALESCE(get_canonical_state(o.country, o.region), o.region, 'Unknown Region')) = ?"
        )
        params = [country_code, region_slug]

    query = f"""
        SELECT
            arg_max(o.farm, length(o.farm)) as farm_name,
            o.farm_normalized,
            arg_max(o.producer, length(o.producer)) as producer_name,
            COUNT(DISTINCT o.bean_id) as bean_count,
            AVG((o.elevation_min + o.elevation_max) / 2) as avg_elevation
        FROM origins o
        WHERE o.country = ? AND {region_filter}
          AND o.farm IS NOT NULL AND o.farm != ''
        GROUP BY o.farm_normalized
    """

    rows = conn.execute(query, params).fetchall()

    farms = defaultdict(list)
    for row in rows:
        entry = {
            "farm_name": row[0],
            "farm_normalized": row[1],
            "producer_name": row[2] or "",
            "bean_count": row[3],
            "avg_elevation": int(row[4]) if row[4] else None,
            "surnames": list(name_utils.extract_surnames(row[2] or "")),
        }
        farms[row[1]].append(entry)

    return dict(farms)


# Helper imports
from kissaten.dedup import normalizer as name_utils
