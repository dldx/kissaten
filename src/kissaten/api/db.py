import glob
import hashlib
import json
import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

import duckdb
from rich.console import Console

from kissaten.scrapers import get_registry

# Initialize Rich console for formatted output
console = Console(force_terminal=True)  # force_terminal ensures progress bars work in subprocess

logger = logging.getLogger(__name__)


def _get_database_path():
    """Get the database path based on environment variable."""
    # Allow explicit database path override
    env_path = os.environ.get("KISSATEN_DATABASE_PATH")
    if env_path:
        return env_path

    # Select database based on environment variable
    # Use rw_kissaten.duckdb for refresh operations, kissaten.duckdb for API queries
    if os.environ.get("KISSATEN_USE_RW_DB") == "1":
        return Path(__file__).parent.parent.parent.parent / "data" / "rw_kissaten.duckdb"
    else:
        return Path(__file__).parent.parent.parent.parent / "data" / "kissaten.duckdb"


# Database connection - initialized at module load time
# Will use the appropriate database based on KISSATEN_USE_RW_DB environment variable
conn = duckdb.connect(str(_get_database_path()))

# Global region mappings cache
_region_mappings: dict[str, dict[str, Any]] = {}

# Structure: country_code -> region_slug -> normalized_farm_name -> canonical_farm_name
_farm_mappings: dict[str, dict[str, dict[str, str]]] = {}


def load_region_mappings():
    """Load region name mappings from JSON files."""
    global _region_mappings

    mapping_dir = Path(__file__).parent.parent / "database" / "region_mappings"
    if not mapping_dir.exists():
        logger.warning(f"Region mappings directory not found: {mapping_dir}")
        return

    # Load all country mapping files
    for mapping_file in mapping_dir.glob("*.json"):
        country_code = mapping_file.stem.upper()
        try:
            with open(mapping_file, encoding="utf-8") as f:
                country_mappings = json.load(f)
                _region_mappings[country_code] = country_mappings
                logger.info(f"Loaded {len(country_mappings)} region mappings for {country_code}")
        except Exception as e:
            logger.error(f"Error loading region mappings for {country_code}: {e}")


def load_farm_mappings():
    """Load farm name mappings from JSON file."""
    global _farm_mappings

    mapping_file = Path(__file__).parent.parent / "database" / "farm_mappings.json"
    if not mapping_file.exists():
        # It's okay if it doesn't exist yet, deduplication might not have run
        return

    try:
        with open(mapping_file, encoding="utf-8") as f:
            mappings_list = json.load(f)
        
        # Transform list to nested dict for fast lookup
        # country -> region -> normalized -> canonical
        count = 0
        for entry in mappings_list:
            country = entry["country"]
            region = entry["region"]
            canonical = entry["canonical_farm_name"]
            
            if country not in _farm_mappings:
                _farm_mappings[country] = {}
            if region not in _farm_mappings[country]:
                _farm_mappings[country][region] = {}
            
            # Note: We do NOT need to map canonical to itself for normalized lookup,
            # because the function returns the input if no match.
            # But we might want to map normalize_farm_name(canonical) -> canonical?
            
            # Support both normalized and original farm names in the mapping file
            # If original farm names are provided, normalize them on the fly
            names_to_map = []
            if "normalized_farm_names" in entry:
                names_to_map = entry["normalized_farm_names"]
            elif "original_farm_names" in entry:
                names_to_map = [normalize_farm_name(name) for name in entry["original_farm_names"]]
            
            # Map all variations to canonical
            for normalized in names_to_map:
                _farm_mappings[country][region][normalized] = canonical
                count += 1
                
        logger.info(f"Loaded {count} farm mappings from {mapping_file.name}")
            
    except Exception as e:
        logger.error(f"Error loading farm mappings: {e}")


def normalize_region_name(region: str) -> str:
    """Normalize region name for URL-friendly slugs."""
    if not region:
        return ""
    # Normalize unicode to decompose accents, then filter to ASCII
    nfkd_form = unicodedata.normalize("NFKD", region)
    ascii_only = nfkd_form.encode("ASCII", "ignore").decode("ASCII")
    # Convert to lowercase, replace spaces and special chars with hyphens
    normalized = re.sub(r"[^a-zA-Z0-9\s]", "", ascii_only.lower())
    normalized = re.sub(r"\s+", "-", normalized.strip())
    return normalized


def normalize_farm_name(farm: str) -> str:
    """Normalize farm name for URL-friendly slugs."""
    if not farm:
        return ""
    # Normalize unicode to decompose accents, then filter to ASCII
    nfkd_form = unicodedata.normalize("NFKD", farm)
    ascii_only = nfkd_form.encode("ASCII", "ignore").decode("ASCII")
    # Convert to lowercase, replace spaces and special chars with hyphens
    normalized = re.sub(r"[^a-zA-Z0-9\s]", "", ascii_only.lower())
    normalized = re.sub(r"\s+", "-", normalized.strip())
    return normalized


def get_canonical_state(country_code: str, region_name: str) -> str | None:
    """
    Get canonical state name for a region.

    Args:
        country_code: Two-letter ISO country code
        region_name: Original region name from data

    Returns:
        Canonical state name if mapping exists, otherwise original region name.
        Returns None for invalid/failed regions (preserves NULL in database).
    """
    # Handle None inputs
    if country_code is None or region_name is None:
        return None

    country_code = country_code.upper()

    if country_code not in _region_mappings:
        return region_name

    country_map = _region_mappings[country_code]

    if region_name in country_map:
        canonical = country_map[region_name].get("canonical_state")
        # If canonical_state is None (invalid/failed regions), return None
        # This allows filtering these regions in queries
        if canonical is None:
            return None
        return canonical

    return region_name


def get_canonical_farm(country_code: str, region_slug: str, farm_normalized: str) -> str:
    """
    Get canonical name for a farm based on deduplication mappings.
    
    Args:
        country_code: Two-letter ISO country code
        region_slug: Normalized region slug
        farm_normalized: Normalized farm name slug from database
        
    Returns:
        Canonical farm name (Display Name) if mapping exists, otherwise returns None (let caller handle fallback).
        Actually, for UDF usage it's better to return something consistently.
        BUT if we return original normalized slug, it looks ugly.
        If we return NULL, we can coalese in SQL.
        Let's return the input normalized name if no match found? 
        No, user wants "Canonical Name". If no match, the canonical name IS the original name (from the row).
        But we don't have the original display name here, we only have farm_normalized.
        
        So:
        If match: return Canonical Display Name (e.g. "Quebraditas")
        If no match: return farm_normalized (e.g. "quebraditas")
        
        Ideally this function should be used as:
        COALESCE(get_canonical_farm(...), o.farm) -> Wait, o.farm is unnormalized.
        
        If I use this in GROUP BY, I want to group different physical rows together.
        GROUP BY get_canonical_farm(..., o.farm_normalized)
        
        If "quebraditas" and "finca-quebraditas" both map to "Quebraditas", then they group together.
        If "unknown-farm" doesn't map to anything, it returns "unknown-farm".
        Then in SELECT, I can select get_canonical_farm(...) as display_name.
        "unknown-farm" is ugly.
        
        Alternatively, passing the original name `o.farm` allows returning it as fallback.
        BUT `o.farm` has variations.
        So we definitely want to map based on `farm_normalized`.
        
        If we return None on no match, then:
        SELECT COALESCE(get_canonical_farm(..., o.farm_normalized), o.farm)
        This works perfectly! It preserves the original display name if no mapping exists.
    """
    if not farm_normalized:
        return None
        
    if not country_code or not region_slug:
        return None
        
    country_code = country_code.upper()
    
    if country_code in _farm_mappings:
        country_farms = _farm_mappings[country_code]
        if region_slug in country_farms:
            # Check for exact match on normalized key
            if farm_normalized in country_farms[region_slug]:
                return country_farms[region_slug][farm_normalized]
                
    return None


def _ensure_connection():
    """Ensure database connection is initialized (mainly for testing/explicit reconnection)."""
    global conn
    if conn is None:
        conn = duckdb.connect(str(_get_database_path()))


# Register region mapping function as DuckDB UDF with SPECIAL null handling
# This allows the function to return NULL for invalid/failed regions
conn.create_function(
    "get_canonical_state",
    get_canonical_state,
    [str, str],
    str,
    null_handling="special"
)

conn.create_function(
    "get_canonical_farm",
    get_canonical_farm,
    [str, str, str],
    str,
    null_handling="special"
)

# Register normalization functions as DuckDB UDFs
conn.create_function("normalize_farm_name", normalize_farm_name, [str], str)
conn.create_function("normalize_region_name", normalize_region_name, [str], str)

# Load region mappings on module initialization
load_region_mappings()
load_farm_mappings()


def calculate_file_checksum(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in chunks to handle large files efficiently
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def is_file_processed(file_path: Path, data_dir: Path, check_checksum: bool = False) -> bool:
    """Check if a file has already been processed.

    Args:
        file_path: Path to the file to check
        data_dir: Data directory for relative path calculation
        check_checksum: If True, verify checksum matches. If False, only check if path exists.

    Returns:
        True if file has been processed (and checksum matches if check_checksum=True)
    """
    try:
        # Get relative path from data_dir for consistent tracking
        relative_path = str(file_path.relative_to(data_dir))

        if check_checksum:
            # Check both path and checksum
            checksum = calculate_file_checksum(file_path)
            result = conn.execute(
                """
                SELECT checksum FROM processed_files
                WHERE file_path = ? AND checksum = ?
            """,
                [relative_path, checksum],
            ).fetchone()
        else:
            # Only check if path exists (assume files don't change)
            result = conn.execute(
                """
                SELECT file_path FROM processed_files
                WHERE file_path = ?
            """,
                [relative_path],
            ).fetchone()

        return result is not None
    except Exception:
        return False


def filter_unprocessed_files(file_paths: list[Path], data_dir: Path, check_checksum: bool = False) -> list[Path]:
    """Batch check which files have not been processed yet.

    Args:
        file_paths: List of file paths to check
        data_dir: Data directory for relative path calculation
        check_checksum: If True, verify checksums match. If False, only check if paths exist.

    Returns:
        List of file paths that have not been processed (or have changed if check_checksum=True)
    """
    if not file_paths:
        return []

    try:
        # Build mapping of relative paths to absolute paths
        path_mapping = {}
        checksum_mapping = {}

        for file_path in file_paths:
            try:
                relative_path = str(file_path.relative_to(data_dir))
                path_mapping[relative_path] = file_path

                if check_checksum:
                    checksum_mapping[relative_path] = calculate_file_checksum(file_path)
            except Exception:
                # If we can't get relative path, skip this file
                continue

        if not path_mapping:
            return []

        # Get all processed files in a single query
        relative_paths = list(path_mapping.keys())
        placeholders = ",".join(["?"] * len(relative_paths))

        if check_checksum:
            # Check both path and checksum
            query = f"""
                SELECT file_path, checksum FROM processed_files
                WHERE file_path IN ({placeholders})
            """
            processed_files = conn.execute(query, relative_paths).fetchall()

            # Build set of processed file paths with matching checksums
            processed_set = {
                row[0] for row in processed_files if row[0] in checksum_mapping and row[1] == checksum_mapping[row[0]]
            }
        else:
            # Only check if paths exist
            query = f"""
                SELECT file_path FROM processed_files
                WHERE file_path IN ({placeholders})
            """
            processed_files = conn.execute(query, relative_paths).fetchall()
            processed_set = {row[0] for row in processed_files}

        # Return files that are not in the processed set
        unprocessed_files = [
            path_mapping[rel_path] for rel_path in path_mapping.keys() if rel_path not in processed_set
        ]

        return unprocessed_files

    except Exception as e:
        # On error, assume all files are unprocessed to be safe
        console.print(f"[yellow]Warning: Error checking processed files: {e}[/yellow]")
        return file_paths


def mark_file_processed(file_path: Path, data_dir: Path, file_type: str):
    """Mark a file as processed by storing its checksum."""
    try:
        relative_path = str(file_path.relative_to(data_dir))
        checksum = calculate_file_checksum(file_path)

        # Use INSERT OR REPLACE to update if file path already exists
        conn.execute(
            """
            INSERT OR REPLACE INTO processed_files (file_path, checksum, file_type, processed_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """,
            [relative_path, checksum, file_type],
        )
        conn.commit()
    except Exception as e:
        print(f"Error marking file as processed: {e}")


async def init_database(incremental: bool = False, check_for_changes: bool = False):
    """Initialize the DuckDB database with required tables.

    Args:
        incremental: If True, preserve existing data and only add new/changed files.
                    If False, drop all tables and recreate from scratch (default).
        check_for_changes: If True (with incremental), verify file checksums to detect changes.
                          If False (default), only check if files exist in tracking table.
    """
    # Ensure database connection is initialized
    _ensure_connection()

    if not incremental:
        # Clear existing data - only in full refresh mode
        # Drop views first, as they depend on tables
        conn.execute("DROP VIEW IF EXISTS coffee_beans_with_categorized_notes")
        conn.execute("DROP VIEW IF EXISTS coffee_beans_with_origin")
        conn.execute("DROP VIEW IF EXISTS roasters_with_location")

        # Now drop tables. Order matters for foreign keys for DROPPING too!
        # Drop child tables before parent tables.
        conn.execute("DROP TABLE IF EXISTS origins")
        conn.execute("DROP TABLE IF EXISTS coffee_beans")
        conn.execute("DROP TABLE IF EXISTS roasters")
        conn.execute("DROP TABLE IF EXISTS country_codes")
        conn.execute("DROP TABLE IF EXISTS roaster_location_codes")
        conn.execute("DROP TABLE IF EXISTS tasting_notes_categories")
    # Create coffee beans table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coffee_beans (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            roaster VARCHAR,
            url VARCHAR,
            is_single_origin BOOLEAN,
            price_paid_for_green_coffee DOUBLE,
            currency_of_price_paid_for_green_coffee VARCHAR,
            roast_level VARCHAR,
            roast_profile VARCHAR,
            weight INTEGER,
            price DOUBLE,
            currency VARCHAR,
            price_usd DOUBLE,  -- Normalized price in USD for sorting/filtering
            is_decaf BOOLEAN,
            cupping_score DOUBLE,
            tasting_notes VARCHAR[], -- Array of strings
            description TEXT,
            in_stock BOOLEAN,
            scraped_at TIMESTAMP,
            scraper_version VARCHAR,
            filename VARCHAR,  -- Store the original JSON filename
            image_url VARCHAR,  -- Store the image URL
            clean_url_slug VARCHAR,  -- Store clean URL without timestamp
            bean_url_path VARCHAR,  -- Store the full bean URL path from directory structure
            date_added TIMESTAMP  -- Date when this coffee was first scraped/added
        )
    """)

    # Add price_usd column if it doesn't exist (migration for existing databases)
    try:
        conn.execute("ALTER TABLE coffee_beans ADD COLUMN price_usd DOUBLE")
        print("Added price_usd column to existing coffee_beans table")
    except Exception:
        # Column already exists, which is fine
        pass

    # Add date_added column if it doesn't exist (migration for existing databases)
    try:
        conn.execute("ALTER TABLE coffee_beans ADD COLUMN date_added TIMESTAMP")
        print("Added date_added column to existing coffee_beans table")
    except Exception:
        # Column already exists, which is fine
        pass

    # Create origins table to handle multiple origins per bean
    conn.execute("""
        CREATE TABLE IF NOT EXISTS origins (
            id INTEGER PRIMARY KEY,
            bean_id INTEGER,
            country VARCHAR,
            region VARCHAR,
            region_normalized VARCHAR,
            producer VARCHAR,
            farm VARCHAR,
            farm_normalized VARCHAR,
            elevation_min INTEGER DEFAULT 0,
            elevation_max INTEGER DEFAULT 0,
            latitude DOUBLE,
            longitude DOUBLE,
            process VARCHAR,
            process_common_name VARCHAR,
            variety VARCHAR,
            variety_canonical VARCHAR[],
            harvest_date TIMESTAMP,
            FOREIGN KEY (bean_id) REFERENCES coffee_beans (id)
        )
    """)

    # Add normalized columns if they don't exist (migration for existing databases)
    try:
        conn.execute("ALTER TABLE origins ADD COLUMN region_normalized VARCHAR")
        print("Added region_normalized column to existing origins table")
    except Exception:
        # Column already exists, which is fine
        pass

    try:
        conn.execute("ALTER TABLE origins ADD COLUMN farm_normalized VARCHAR")
        print("Added farm_normalized column to existing origins table")
    except Exception:
        # Column already exists, which is fine
        pass

    # Create roasters table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS roasters (
            id INTEGER PRIMARY KEY,
            name VARCHAR UNIQUE,
            slug VARCHAR UNIQUE,
            website VARCHAR,
            location VARCHAR,
            email VARCHAR,
            active BOOLEAN,
            last_scraped TIMESTAMP,
            total_beans_scraped INTEGER
        )
    """)

    # Create country codes table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS country_codes (
            name VARCHAR,
            alpha_2 VARCHAR PRIMARY KEY,
            alpha_3 VARCHAR,
            country_code VARCHAR,
            iso_3166_2 VARCHAR,
            region VARCHAR,
            sub_region VARCHAR,
            intermediate_region VARCHAR,
            region_code VARCHAR,
            sub_region_code VARCHAR,
            intermediate_region_code VARCHAR
        )
    """)

    # Create roaster location codes table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS roaster_location_codes (
            location VARCHAR,
            code VARCHAR PRIMARY KEY,
            region VARCHAR
        )
    """)

    # Create tasting notes categories table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasting_notes_categories (
            tasting_note VARCHAR PRIMARY KEY,
            primary_category VARCHAR,
            secondary_category VARCHAR,
            tertiary_category VARCHAR,
            confidence DOUBLE
        )
    """)

    # Create processed files table for incremental updates
    conn.execute("""
        CREATE TABLE IF NOT EXISTS processed_files (
            file_path VARCHAR PRIMARY KEY,
            checksum VARCHAR NOT NULL,
            file_type VARCHAR NOT NULL,
            processed_at TIMESTAMP NOT NULL
        )
    """)

    # Create currency exchange rates table for conversion
    conn.execute("""
        CREATE TABLE IF NOT EXISTS currency_rates (
            base_currency VARCHAR NOT NULL,
            target_currency VARCHAR NOT NULL,
            rate DOUBLE NOT NULL,
            fetched_at TIMESTAMP NOT NULL,
            data_timestamp INTEGER  -- Unix timestamp from API
        )
    """)

    # Create varietal mappings table to store canonical varietal information
    conn.execute("""
        CREATE TABLE IF NOT EXISTS varietal_mappings (
            original_name VARCHAR PRIMARY KEY,
            canonical_names VARCHAR[],
            confidence DOUBLE,
            is_compound BOOLEAN,
            separator VARCHAR
        )
    """)

    # Create coffee varietals table to store World Coffee Research varietal information
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coffee_varietals (
            name VARCHAR PRIMARY KEY,
            description TEXT,
            link VARCHAR,
            species VARCHAR
        )
    """)

    # Create a view to simplify queries by joining coffee beans with their primary origin
    conn.execute("""
        CREATE OR REPLACE VIEW coffee_beans_with_origin AS
        SELECT
            cb.*,
            o.country,
            o.region,
            o.region_normalized,
            o.producer,
            o.farm,
            o.farm_normalized,
            o.elevation_min,
            o.elevation_max,
            o.latitude,
            o.longitude,
            o.process,
            o.process_common_name,
            o.variety,
            o.harvest_date,
            cc.name as country_full_name
        FROM coffee_beans cb
        LEFT JOIN (
            -- Get the first origin for each bean (primary origin)
            SELECT DISTINCT ON (bean_id) *
            FROM origins
            ORDER BY bean_id, id
        ) o ON cb.id = o.bean_id
        LEFT JOIN country_codes cc ON o.country = cc.alpha_2
    """)

    # Create a view for roasters with location codes
    conn.execute("""
        CREATE OR REPLACE VIEW roasters_with_location AS
        SELECT
            r.*,
            rlc.code as roaster_country_code
        FROM roasters r
        LEFT JOIN roaster_location_codes rlc ON r.location = rlc.location
    """)


async def calculate_usd_prices():
    """Calculate USD prices for all coffee beans using current exchange rates."""
    try:
        # Update all beans with USD prices using DuckDB's CASE statement for efficient batch processing
        conn.execute("""
            UPDATE coffee_beans
            SET price_usd =
                CASE
                    WHEN currency = 'USD' OR currency IS NULL THEN price
                    WHEN price IS NULL OR price = 0 THEN NULL
                    ELSE
                        CASE
                            WHEN currency = 'USD' THEN price
                            ELSE
                                price / COALESCE((
                                    SELECT rate
                                    FROM currency_rates cr
                                    WHERE cr.base_currency = 'USD'
                                    AND cr.target_currency = coffee_beans.currency
                                    ORDER BY cr.fetched_at DESC
                                    LIMIT 1
                                ), 1.0)
                        END
                END
            WHERE price IS NOT NULL
        """)

        # Get statistics about the conversion
        stats_result = conn.execute("""
            SELECT
                COUNT(*) as total_beans,
                COUNT(price_usd) as beans_with_usd_price,
                COUNT(DISTINCT currency) as unique_currencies
            FROM coffee_beans
            WHERE price IS NOT NULL
        """).fetchone()

        if stats_result:
            total, with_usd, currencies = stats_result
            print(f"USD price calculation complete: {with_usd}/{total} beans processed across {currencies} currencies")

    except Exception as e:
        print(f"Error calculating USD prices: {e}")


async def apply_diffjson_updates(
    data_dir: Path,
    incremental: bool = False,
    check_for_changes: bool = False,
):
    """Apply partial updates from diffjson files to existing coffee beans, ordered by scraped_at timestamp.

    Args:
        data_dir: Directory containing roaster data
        incremental: If True, skip files that have already been processed (assumes files don't change)
        check_for_changes: If True (with incremental), verify file checksums to detect changes
    """
    import json
    from datetime import datetime

    from kissaten.schemas.coffee_bean import CoffeeBeanDiffUpdate

    # Find all diffjson files
    diffjson_pattern = str(data_dir / "**" / "*.diffjson")
    diffjson_files = glob.glob(diffjson_pattern, recursive=True)

    if not diffjson_files:
        console.print("[yellow]No diffjson files found - skipping partial updates[/yellow]")
        return

    # Filter out already processed files if in incremental mode
    if incremental:
        console.print(f"[cyan]Filtering {len(diffjson_files)} diffjson files...[/cyan]")

        # Batch check all files at once (much faster than checking one by one)
        file_paths = [Path(f) for f in diffjson_files]
        unprocessed_files = filter_unprocessed_files(file_paths, data_dir, check_checksum=check_for_changes)

        if not unprocessed_files:
            console.print("[yellow]All diffjson files already processed - skipping[/yellow]")
            return

        skipped_count = len(diffjson_files) - len(unprocessed_files)
        console.print(
            f"[cyan]📝 Processing {len(unprocessed_files)} new/changed diffjson files "
            f"(skipping {skipped_count} already processed)[/cyan]"
        )
        diffjson_files = [str(f) for f in unprocessed_files]
    else:
        console.print(f"Processing {len(diffjson_files)} diffjson update files...")

    # Parse all diffjson files and sort them by scraped_at timestamp
    diffjson_updates = []

    for diffjson_file in diffjson_files:
        try:
            with open(diffjson_file) as f:
                raw_update_data = json.load(f)

            # Validate the diffjson data using Pydantic schema
            try:
                diff_update = CoffeeBeanDiffUpdate.model_validate(raw_update_data)
            except Exception as validation_error:
                print(f"  Skipping {diffjson_file}: validation failed - {validation_error}")
                continue

            # Parse scraped_at timestamp for sorting
            scraped_at = None
            if hasattr(diff_update, "scraped_at") and diff_update.scraped_at:
                scraped_at = diff_update.scraped_at

            diffjson_updates.append({"file": diffjson_file, "update": diff_update, "scraped_at": scraped_at})
        except Exception as e:
            print(f"  Error parsing {diffjson_file}: {e}")
            continue

    # Sort by scraped_at timestamp (earliest first) to apply updates chronologically
    # Normalize all timestamps to timezone-naive for consistent comparison
    def get_sort_key(update_dict):
        ts = update_dict["scraped_at"]
        if ts is None:
            return datetime.min
        # Remove timezone information for consistent comparison
        if ts.tzinfo is not None:
            return ts.replace(tzinfo=None)
        return ts

    diffjson_updates.sort(key=get_sort_key)

    updates_applied = 0

    for update_info in diffjson_updates:
        diffjson_file = update_info["file"]
        diff_update = update_info["update"]
        try:
            # Extract URL from validated update data (already validated above)
            url = str(diff_update.url)

            # Check if bean exists in database
            existing_bean = conn.execute("SELECT id FROM coffee_beans WHERE url = ?", [url]).fetchone()

            if not existing_bean:
                print(f"  Skipping {diffjson_file}: no matching bean found for URL {url}")
                continue

            bean_id = existing_bean[0]

            # Convert the validated model to dict and exclude None values and URL
            update_data = diff_update.model_dump(exclude_none=True, exclude={"url"})

            # Build UPDATE query for fields that exist in the validated diffjson
            update_fields = []
            update_params = []

            # Handle special case for tasting_notes (array field)
            if "tasting_notes" in update_data:
                update_fields.append("tasting_notes = ?")
                update_params.append(update_data["tasting_notes"])
                del update_data["tasting_notes"]  # Remove so it's not processed again

            # Handle all other fields
            for field, value in update_data.items():
                update_fields.append(f"{field} = ?")
                update_params.append(value)

            if update_fields:
                # Execute update
                update_query = f"""
                    UPDATE coffee_beans
                    SET {", ".join(update_fields)}
                    WHERE id = ?
                """
                update_params.append(bean_id)

                conn.execute(update_query, update_params)

                updates_applied += 1

                # Mark file as processed after successful update
                # Track in both full refresh and incremental mode so subsequent incremental updates can skip
                mark_file_processed(Path(diffjson_file), data_dir, "diffjson")
            else:
                print(f"  Skipping {diffjson_file}: no updatable fields found")

        except Exception as e:
            print(f"  Error processing {diffjson_file}: {e}")
            continue

    if updates_applied > 0:
        # Recalculate USD prices for updated beans
        await calculate_usd_prices()
        print(f"Applied {updates_applied} diffjson updates")
    else:
        print("No diffjson updates were applied")


def normalize_country_code(country_value: str, country_mapping: dict) -> str:
    """
    Normalize country codes from various formats to ISO alpha-2 codes.

    Args:
        country_value: The country value from scraped data (could be name, code, etc.)
        country_mapping: Dictionary mapping various formats to alpha-2 codes

    Returns:
        Normalized ISO alpha-2 country code or original value if no match found
    """
    if not country_value or not isinstance(country_value, str):
        return ""

    # Clean the input - remove extra whitespace and convert to uppercase for comparison
    cleaned_value = country_value.strip().upper()

    # Return the mapping if found, otherwise return original value
    return country_mapping.get(cleaned_value, country_value)


def _insert_roasters_from_registry(scraper_infos, conn, incremental=False):
    """Helper function to insert roasters from the scraper registry.

    Args:
        scraper_infos: List of ScraperInfo objects from the registry
        conn: DuckDB connection
        incremental: If True, check existing roasters and only insert new ones
    """
    if incremental:
        # In incremental mode, only insert roasters that don't exist yet (by name/slug)
        # Get existing roaster names
        existing_roasters = conn.execute("SELECT slug FROM roasters").fetchall()
        existing_slugs = {row[0] for row in existing_roasters}

        # Get max ID to continue from there
        max_id_result = conn.execute("SELECT MAX(id) FROM roasters").fetchone()
        next_id = (max_id_result[0] if max_id_result and max_id_result[0] else 0) + 1

        # Filter to only new roasters
        new_roasters = [s for s in scraper_infos if s.directory_name not in existing_slugs]

        if not new_roasters:
            result = conn.execute("SELECT COUNT(*) FROM roasters").fetchone()
            roaster_count = result[0] if result else 0
            print(f"All {roaster_count} roasters already exist (no new roasters to add)")
            return

        # Insert only new roasters
        roaster_values = []
        for i, scraper_info in enumerate(new_roasters, start=next_id):
            roaster_values.append(
                (
                    i,
                    scraper_info.roaster_name,
                    scraper_info.directory_name,
                    scraper_info.website,
                    f"{scraper_info.country}",
                    "",  # email
                    True,  # active
                    None,  # last_scraped
                    0,  # total_beans_scraped
                )
            )

        for values in roaster_values:
            conn.execute(
                """
                INSERT INTO roasters (
                    id, name, slug, website, location, email, active,
                    last_scraped, total_beans_scraped
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                values,
            )

        result = conn.execute("SELECT COUNT(*) FROM roasters").fetchone()
        roaster_count = result[0] if result else 0
        print(f"Added {len(new_roasters)} new roasters (total: {roaster_count})")
    else:
        # Full refresh mode - insert all roasters with sequential IDs
        roaster_values = []
        for i, scraper_info in enumerate(scraper_infos, 1):
            roaster_values.append(
                (
                    i,
                    scraper_info.roaster_name,
                    scraper_info.directory_name,
                    scraper_info.website,
                    f"{scraper_info.country}",
                    "",  # email
                    True,  # active
                    None,  # last_scraped
                    0,  # total_beans_scraped
                )
            )

        for values in roaster_values:
            conn.execute(
                """
                INSERT INTO roasters (
                    id, name, slug, website, location, email, active,
                    last_scraped, total_beans_scraped
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                values,
            )

        result = conn.execute("SELECT COUNT(*) FROM roasters").fetchone()
        roaster_count = result[0] if result else 0
        print(f"Loaded {roaster_count} roasters from registry")


async def load_coffee_data(data_dir: Path, incremental: bool = False, check_for_changes: bool = False):
    """Load coffee bean data from JSON files into DuckDB using DuckDB's native glob functionality.

    Args:
        data_dir: Directory containing roaster data
        incremental: If True, skip files that have already been processed (assumes files don't change)
        check_for_changes: If True (with incremental), verify file checksums to detect changes
    """
    countrycodes_path = Path(__file__).parent.parent / "database" / "countrycodes.csv"
    processing_methods_mapping_path = Path(__file__).parent.parent / "database/processing_methods_mappings.json"
    varietal_mappings_path = Path(__file__).parent.parent / "database" / "varietal_mappings.json"

    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        return

    # Load processing methods mapping
    processing_mapping = {}
    if processing_methods_mapping_path.exists():
        try:
            import json

            with open(processing_methods_mapping_path, encoding="utf-8") as f:
                mapping_data = json.load(f)

            for mapping in mapping_data:
                original_name = mapping.get("original_name", "")
                common_name = mapping.get("common_name", "")
                if original_name and common_name:
                    processing_mapping[original_name] = common_name

            print(f"Loaded {len(processing_mapping)} processing method mappings")
        except Exception as e:
            print(f"Error loading processing methods mapping: {e}")
    else:
        print(f"Processing methods mapping file not found: {processing_methods_mapping_path}")

    # Load varietal mappings into both memory (for data processing) and database (for API queries)
    varietal_mapping = {}
    if varietal_mappings_path.exists():
        try:
            import json

            with open(varietal_mappings_path, encoding="utf-8") as f:
                mapping_data = json.load(f)

            for mapping in mapping_data:
                original_name = mapping.get("original_name", "")
                canonical_names = mapping.get("canonical_names", [])
                if original_name and canonical_names:
                    # Store the canonical names array for data processing
                    varietal_mapping[original_name] = canonical_names

            # Load into database table for API queries
            # In incremental mode, only insert if table is empty
            should_load_to_db = True
            if incremental:
                existing_count = conn.execute("SELECT COUNT(*) FROM varietal_mappings").fetchone()[0]
                should_load_to_db = existing_count == 0

            if should_load_to_db:
                # Clear table in non-incremental mode
                if not incremental:
                    conn.execute("DELETE FROM varietal_mappings")

                # Insert all mappings
                for mapping in mapping_data:
                    original_name = mapping.get("original_name", "")
                    canonical_names = mapping.get("canonical_names", [])
                    confidence = mapping.get("confidence", 1.0)
                    is_compound = mapping.get("is_compound", False)
                    separator = mapping.get("separator")

                    if original_name and canonical_names:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO varietal_mappings
                            (original_name, canonical_names, confidence, is_compound, separator)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            [original_name, canonical_names, confidence, is_compound, separator],
                        )

                conn.commit()
                print(f"Loaded {len(varietal_mapping)} varietal mappings into database")
            else:
                print("Varietal mappings already loaded in database (incremental mode)")

        except Exception as e:
            print(f"Error loading varietal mappings: {e}")
    else:
        print(f"Varietal mappings file not found: {varietal_mappings_path}")

    # Get scraper registry to map directory names to roaster info
    registry = get_registry()
    scraper_infos = registry.list_scrapers()

    # Create mapping from directory name to roaster info
    directory_to_roaster = {}
    for scraper_info in scraper_infos:
        directory_to_roaster[scraper_info.directory_name] = scraper_info

    # Load country codes from CSV
    country_mapping = {}
    if countrycodes_path.exists():
        try:
            # In incremental mode, use INSERT OR IGNORE to avoid duplicates
            insert_mode = "INSERT OR IGNORE" if incremental else "INSERT"
            conn.execute(f"""
                {insert_mode} INTO country_codes
                SELECT * FROM read_csv('{countrycodes_path}', header=true, auto_detect=true)
            """)
            result = conn.execute("SELECT COUNT(*) FROM country_codes").fetchone()
            country_count = result[0] if result else 0
            print(f"Loaded {country_count} country codes")

            # Create country mapping for normalization
            # Include various formats: uppercase names, lowercase names, alpha-2, alpha-3
            country_codes_data = conn.execute("""
                SELECT name, alpha_2, alpha_3 FROM country_codes
            """).fetchall()

            for row in country_codes_data:
                country_name, alpha_2, alpha_3 = row
                if country_name and alpha_2:
                    # Map uppercase country name to alpha-2
                    country_mapping[country_name.upper()] = alpha_2
                    # Map lowercase country name to alpha-2
                    country_mapping[country_name.lower()] = alpha_2
                    # Map alpha-2 to itself (in case it's already correct)
                    country_mapping[alpha_2.upper()] = alpha_2
                    # Map alpha-3 to alpha-2
                    if alpha_3:
                        country_mapping[alpha_3.upper()] = alpha_2

            # Add special mappings for common variations
            special_mappings = {
                "BOLIVIA": "BO",
                "bolivia": "BO",
                "UNITED STATES": "US",
                "USA": "US",
                "UNITED KINGDOM": "GB",
                "SOUTH KOREA": "KR",
                "DEMOCRATIC REPUBLIC OF CONGO": "CD",
                "REPUBLIC OF CONGO": "CG",
                "CONGO": "CG",
                "IVORY COAST": "CI",
                "CAPE VERDE": "CV",
                "CZECH REPUBLIC": "CZ",
                "EAST TIMOR": "TL",
                "RUSSIA": "RU",
                "SOUTH AFRICA": "ZA",
                "PALESTINE": "PS",
            }

            country_mapping.update(special_mappings)

            print(f"Created country mapping with {len(country_mapping)} entries")
        except Exception as e:
            print(f"Error loading country codes: {e}")
    else:
        print(f"Country codes file not found: {countrycodes_path}")

    # Load roaster location codes from CSV
    roaster_location_codes_path = Path(__file__).parent.parent / "database" / "roaster_location_codes.csv"
    if roaster_location_codes_path.exists():
        try:
            # In incremental mode, use INSERT OR IGNORE to avoid duplicates
            insert_mode = "INSERT OR IGNORE" if incremental else "INSERT"
            conn.execute(f"""
                {insert_mode} INTO roaster_location_codes
                SELECT * FROM read_csv('{roaster_location_codes_path}', header=true, auto_detect=true)
            """)
            result = conn.execute("SELECT COUNT(*) FROM roaster_location_codes").fetchone()
            location_count = result[0] if result else 0
            print(f"Loaded {location_count} roaster location codes")
        except Exception as e:
            print(f"Error loading roaster location codes: {e}")
    else:
        print(f"Roaster location codes file not found: {roaster_location_codes_path}")

    # Load coffee varietals from JSON
    coffee_varietals_path = Path(__file__).parent.parent / "database" / "coffee_varietals.json"
    if coffee_varietals_path.exists():
        try:
            import json

            # In incremental mode, only load if table is empty
            should_load = True
            if incremental:
                existing_count = conn.execute("SELECT COUNT(*) FROM coffee_varietals").fetchone()[0]
                should_load = existing_count == 0

            if should_load:
                # Clear table in non-incremental mode
                if not incremental:
                    conn.execute("DELETE FROM coffee_varietals")

                # Load JSON data
                with open(coffee_varietals_path, encoding="utf-8") as f:
                    varietals_data = json.load(f)

                # Insert varietals into database
                for varietal in varietals_data:
                    name = varietal.get("name")
                    description = varietal.get("description")
                    link = varietal.get("link")
                    species = varietal.get("species")

                    if name:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO coffee_varietals (name, description, link, species)
                            VALUES (?, ?, ?, ?)
                            """,
                            [name, description, link, species],
                        )

                conn.commit()
                result = conn.execute("SELECT COUNT(*) FROM coffee_varietals").fetchone()
                varietal_count = result[0] if result else 0
                print(f"Loaded {varietal_count} coffee varietals from World Coffee Research")
            else:
                print("Coffee varietals already loaded in database (incremental mode)")

        except Exception as e:
            print(f"Error loading coffee varietals: {e}")
    else:
        print(f"Coffee varietals file not found: {coffee_varietals_path}")

    # Insert roasters from the registry
    # In incremental mode, INSERT OR IGNORE will skip existing roasters but allow new ones
    try:
        _insert_roasters_from_registry(scraper_infos, conn, incremental=incremental)
    except Exception as e:
        print(f"Error inserting roasters from registry: {e}")

    try:
        # Always use glob pattern to load all files first
        json_pattern = str(data_dir / "**" / "*.json")
        # Create a temporary view with the raw JSON data, including file path for roaster extraction
        conn.execute(f"""
            CREATE OR REPLACE TEMPORARY VIEW raw_coffee_data AS
            SELECT
                json_data.*,
                -- Extract roaster directory name from file path
                split_part(filename, '/', -3) as roaster_directory,
                -- Extract scrape date from file path (e.g., 20250911)
                split_part(filename, '/', -2) as scrape_date,
                filename
            FROM read_json('{json_pattern}',
                filename=true,
                auto_detect=true,
                union_by_name=true,
                ignore_errors=true
            ) as json_data
        """)

        # In incremental mode, filter to only unprocessed files
        if incremental:
            from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
            ) as progress:
                filter_task = progress.add_task("[cyan]Filtering processed JSON files...", total=None)

                # Save the original raw_coffee_data to a temp table
                conn.execute("""
                    CREATE OR REPLACE TEMPORARY TABLE raw_coffee_data_temp AS
                    SELECT * FROM raw_coffee_data
                """)

                # Step 1: Detect and handle deleted JSON files
                # Get all JSON files that were previously processed
                processed_json_files = conn.execute("""
                    SELECT file_path FROM processed_files WHERE file_type = 'json'
                """).fetchall()

                deleted_files = []
                for (relative_path,) in processed_json_files:
                    full_path = data_dir / relative_path
                    if not full_path.exists():
                        deleted_files.append((str(full_path), relative_path))

                if deleted_files:
                    console.print(
                        f"[yellow]🗑️  Detected {len(deleted_files)} deleted JSON files - removing their beans[/yellow]"
                    )

                    for full_path, relative_path in deleted_files:
                        # Get bean IDs first
                        bean_ids = conn.execute(
                            "SELECT id FROM coffee_beans WHERE filename = ?", [full_path]
                        ).fetchall()

                        if bean_ids:
                            # Delete origins first (foreign key constraint)
                            for (bean_id,) in bean_ids:
                                conn.execute("DELETE FROM origins WHERE bean_id = ?", [bean_id])

                            # Now delete beans
                            deleted_beans = conn.execute(
                                "DELETE FROM coffee_beans WHERE filename = ? RETURNING id, url", [full_path]
                            ).fetchall()

                            console.print(
                                f"  Removed {len(deleted_beans)} beans from deleted file {Path(full_path).name}"
                            )

                        # Remove from processed_files tracking
                        conn.execute("DELETE FROM processed_files WHERE file_path = ?", [relative_path])

                # Get all JSON filenames from raw data
                all_json_files_result = conn.execute("""
                    SELECT DISTINCT filename FROM raw_coffee_data_temp
                """).fetchall()

                all_json_files = [Path(f[0]) for f in all_json_files_result if f[0]]

                # Use Python to check which files need processing
                # This properly calculates checksums when check_for_changes=True
                unprocessed_json_files = filter_unprocessed_files(
                    all_json_files, data_dir, check_checksum=check_for_changes
                )

                # If check_for_changes is True, identify which files have changed (not just new)
                changed_json_files = []
                if check_for_changes:
                    # Files that exist in processed_files but have different checksums
                    for json_file in unprocessed_json_files:
                        relative_path = str(json_file.relative_to(data_dir))
                        existing = conn.execute(
                            "SELECT checksum FROM processed_files WHERE file_path = ?", [relative_path]
                        ).fetchone()
                        if existing:  # File was previously processed but checksum changed
                            changed_json_files.append(json_file)

                # Delete old beans from changed files before re-inserting
                changed_files_result = [(str(f),) for f in changed_json_files]
                if changed_files_result:
                    console.print(
                        f"[yellow]⚠️  Detected {len(changed_files_result)} changed JSON files "
                        "- removing old data before re-inserting[/yellow]"
                    )

                    # Step 1: Collect all changed JSON files and their URLs
                    changed_urls = set()
                    changed_roasters = set()

                    for (filename,) in changed_files_result:
                        # Get bean IDs and URLs first
                        beans_to_delete = conn.execute(
                            "SELECT id, url FROM coffee_beans WHERE filename = ?", [filename]
                        ).fetchall()

                        if beans_to_delete:
                            console.print(f"  Removing {len(beans_to_delete)} old beans from {Path(filename).name}")

                            # Delete origins first (foreign key constraint)
                            for bean_id, url in beans_to_delete:
                                conn.execute("DELETE FROM origins WHERE bean_id = ?", [bean_id])

                                # Collect URLs for diffjson cleanup
                                if url:
                                    changed_urls.add(url)

                            # Now delete beans
                            conn.execute("DELETE FROM coffee_beans WHERE filename = ?", [filename])

                            # Extract roaster directory from filename
                            try:
                                file_path = Path(filename)
                                roaster_dir = file_path.parts[-3]
                                changed_roasters.add(roaster_dir)
                            except Exception:
                                pass

                    # Step 2: Find diffjson files for changed roasters and check their URLs
                    if changed_urls and changed_roasters:
                        import json

                        diffjson_files_to_reprocess = []

                        for roaster_dir in changed_roasters:
                            # Find all diffjson files for this roaster
                            roaster_diffjson_pattern = str(data_dir / roaster_dir / "**" / "*.diffjson")
                            roaster_diffjson_files = glob.glob(roaster_diffjson_pattern, recursive=True)

                            # Check each diffjson file's URL
                            for diffjson_path in roaster_diffjson_files:
                                try:
                                    with open(diffjson_path) as f:
                                        diffjson_data = json.load(f)
                                        if diffjson_data.get("url") in changed_urls:
                                            diffjson_files_to_reprocess.append(diffjson_path)
                                except Exception:
                                    continue

                        # Step 3: Remove processed_files tracking for matching diffjson files
                        if diffjson_files_to_reprocess:
                            console.print(
                                f"[yellow]  Found {len(diffjson_files_to_reprocess)} diffjson files "
                                "to re-apply for changed beans[/yellow]"
                            )

                            for diffjson_path in diffjson_files_to_reprocess:
                                relative_path = str(Path(diffjson_path).relative_to(data_dir))
                                conn.execute("DELETE FROM processed_files WHERE file_path = ?", [relative_path])

                # Create filtered view based on Python-calculated unprocessed files
                if unprocessed_json_files:
                    # Create a temp table with unprocessed filenames
                    conn.execute("""
                        CREATE OR REPLACE TEMPORARY TABLE unprocessed_filenames (filename VARCHAR)
                    """)

                    # Insert filenames using parameterized query
                    for file_path in unprocessed_json_files:
                        conn.execute("INSERT INTO unprocessed_filenames VALUES (?)", [str(file_path)])

                    # Create filtered view by joining with temp table
                    conn.execute("""
                        CREATE OR REPLACE TEMPORARY VIEW filtered_coffee_data AS
                        SELECT rcd.*
                        FROM raw_coffee_data_temp rcd
                        INNER JOIN unprocessed_filenames uf ON rcd.filename = uf.filename
                    """)

                    result = conn.execute("SELECT COUNT(*) FROM filtered_coffee_data").fetchone()
                    unprocessed_count = result[0] if result else 0
                else:
                    # No unprocessed files
                    conn.execute("""
                        CREATE OR REPLACE TEMPORARY VIEW filtered_coffee_data AS
                        SELECT * FROM raw_coffee_data_temp WHERE FALSE
                    """)
                    unprocessed_count = 0

                total_result = conn.execute("SELECT COUNT(*) FROM raw_coffee_data_temp").fetchone()
                total_count = total_result[0] if total_result else 0
                skipped_count = total_count - unprocessed_count

                progress.update(filter_task, completed=True)

            if unprocessed_count == 0:
                console.print("[yellow]All JSON files already processed - skipping[/yellow]")
                # Clean up temp table
                conn.execute("DROP TABLE IF EXISTS raw_coffee_data_temp")
                # Still need to apply diffjson updates
                await apply_diffjson_updates(data_dir, incremental, check_for_changes)
                return

            console.print(
                f"[cyan]📁 Processing {unprocessed_count} new/changed JSON files "
                f"(skipping {skipped_count} already processed)[/cyan]"
            )

            # Replace raw_coffee_data view with filtered version
            conn.execute("DROP VIEW IF EXISTS raw_coffee_data")
            conn.execute("""
                CREATE OR REPLACE TEMPORARY VIEW raw_coffee_data AS
                SELECT * FROM filtered_coffee_data
            """)

        # Also create a view to get scrape dates from diffjson files to determine the actual latest scrape dates
        # First check if there are any diffjson files to avoid DuckDB errors
        diffjson_pattern = str(data_dir / "**" / "*.diffjson")

        diffjson_files_exist = bool(glob.glob(diffjson_pattern, recursive=True))

        if diffjson_files_exist:
            conn.execute(f"""
                CREATE OR REPLACE TEMPORARY VIEW diffjson_scrape_dates AS
                SELECT DISTINCT
                    split_part(filename, '/', -3) as roaster_directory,
                    split_part(filename, '/', -2) as scrape_date
                FROM read_json('{diffjson_pattern}',
                    filename=true,
                    auto_detect=true,
                    union_by_name=true,
                    ignore_errors=true
                )
            """)
        else:
            # Create empty view if no diffjson files exist
            conn.execute("""
                CREATE OR REPLACE TEMPORARY VIEW diffjson_scrape_dates AS
                SELECT NULL as roaster_directory, NULL as scrape_date
                WHERE false
            """)

        # Create a view to identify the latest scrape date for each roaster (considering both JSON and diffjson)
        conn.execute("""
            CREATE OR REPLACE TEMPORARY VIEW latest_scrapes AS
            SELECT
                roaster_directory,
                MAX(scrape_date) as latest_scrape_date
            FROM (
                -- Include scrape dates from JSON files
                SELECT roaster_directory, scrape_date
                FROM raw_coffee_data
                UNION ALL
                -- Include scrape dates from diffjson files
                SELECT roaster_directory, scrape_date
                FROM diffjson_scrape_dates
            ) all_scrape_dates
            GROUP BY roaster_directory
        """)

        # Create a view to identify the earliest scrape date for each unique coffee bean
        conn.execute("""
            CREATE OR REPLACE TEMPORARY VIEW earliest_coffee_dates AS
            SELECT
                roaster_directory,
                url,
                MIN(scraped_at) as date_added
            FROM raw_coffee_data
            WHERE url IS NOT NULL AND url != ''
            GROUP BY roaster_directory, url
        """)

        # Create a view with only the latest scrape data for each roaster, deduplicated by URL
        conn.execute("""
            CREATE OR REPLACE TEMPORARY VIEW latest_coffee_data AS
            SELECT rcd.*
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY rcd.roaster_directory, rcd.url
                           ORDER BY rcd.scraped_at DESC
                       ) as rn
                FROM raw_coffee_data rcd
                JOIN latest_scrapes ls ON rcd.roaster_directory = ls.roaster_directory
                    AND rcd.scrape_date = ls.latest_scrape_date
                WHERE rcd.url IS NOT NULL AND rcd.url != ''
            ) rcd
            WHERE rcd.rn = 1
        """)

        # Create a comprehensive view that handles both in-stock and out-of-stock beans
        # with proper stock status based on whether they appear in the latest scrape
        conn.execute("""
            CREATE OR REPLACE TEMPORARY VIEW all_coffee_beans_with_stock_status AS
            SELECT
                rcd.*,
                -- Determine stock status: in-stock if URL exists in latest scrape, out-of-stock otherwise
                CASE
                    WHEN latest_urls.url IS NOT NULL THEN true
                    ELSE false
                END as calculated_in_stock,
                -- Use latest scrape data if available, otherwise use historical data
                COALESCE(latest_data.scraped_at, rcd.scraped_at) as final_scraped_at,
                COALESCE(latest_data.filename, rcd.filename) as final_filename,
                -- Add the date when this coffee was first added/scraped
                ecd.date_added
            FROM (
                -- Get the most recent version of each unique bean (by URL and roaster)
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY roaster_directory, url
                           ORDER BY scrape_date DESC, scraped_at DESC
                       ) as rn
                FROM raw_coffee_data
                WHERE url IS NOT NULL AND url != ''
            ) rcd
            LEFT JOIN (
                -- Get URLs that exist in the latest scrape (these are in-stock)
                SELECT DISTINCT roaster_directory, url
                FROM latest_coffee_data
            ) latest_urls ON rcd.roaster_directory = latest_urls.roaster_directory
                         AND rcd.url = latest_urls.url
            LEFT JOIN latest_coffee_data latest_data ON rcd.roaster_directory = latest_data.roaster_directory
                                                    AND rcd.url = latest_data.url
            LEFT JOIN earliest_coffee_dates ecd ON rcd.roaster_directory = ecd.roaster_directory
                                               AND rcd.url = ecd.url
            WHERE rcd.rn = 1
        """)

        # Get the maximum existing ID for incremental mode
        max_id = 0
        if incremental:
            result = conn.execute("SELECT COALESCE(MAX(id), 0) FROM coffee_beans").fetchone()
            max_id = result[0] if result else 0

        # Insert all coffee beans with correct stock status
        conn.execute(f"""
            INSERT INTO coffee_beans (
                id, name, roaster, url, is_single_origin, price_paid_for_green_coffee,
                currency_of_price_paid_for_green_coffee, roast_level, roast_profile, weight, price, currency,
                price_usd, is_decaf, cupping_score, tasting_notes, description, in_stock, scraped_at, scraper_version,
                filename, image_url, clean_url_slug, bean_url_path, date_added
            )
            SELECT
                ROW_NUMBER() OVER (ORDER BY calculated_in_stock DESC, name) + {max_id} as id,
                COALESCE(name, '') as name,
                COALESCE(roaster, 'Unknown Roaster') as roaster,
                COALESCE(url, '') as url,
                COALESCE(is_single_origin, true) as is_single_origin,
                TRY_CAST(price_paid_for_green_coffee AS DOUBLE) as price_paid_for_green_coffee,
                currency_of_price_paid_for_green_coffee,
                roast_level,
                roast_profile,
                TRY_CAST(weight AS INTEGER) as weight,
                TRY_CAST(price AS DOUBLE) as price,
                COALESCE(currency, 'EUR') as currency,
                -- Initialize price_usd as NULL, will be calculated after currency rates are available
                NULL as price_usd,
                COALESCE(is_decaf, false) as is_decaf,
                cupping_score,
                COALESCE(tasting_notes, []) as tasting_notes,
                COALESCE(description, '') as description,
                calculated_in_stock as in_stock,  -- Use calculated stock status
                TRY_CAST(final_scraped_at AS TIMESTAMP) as scraped_at,
                COALESCE(scraper_version, '1.0') as scraper_version,
                final_filename as filename,
                -- Generate static image URL based on filename and roaster path, only if original image_url exists
                CASE
                    WHEN final_filename IS NOT NULL AND image_url IS NOT NULL AND image_url != '' THEN
                        '/static/data/' ||
                        regexp_replace(split_part(final_filename, '/data/', -1), '\\.json$', '.png', 'g')
                    ELSE ''
                END as image_url,
                -- Generate clean URL slug by removing timestamp from filename
                regexp_replace(
                    regexp_replace(split_part(final_filename, '/', -1), '\\.json$', '', 'g'),
                    '_\\d{6}$', '', 'g'
                ) as clean_url_slug,
                -- Generate bean_url_path from actual directory structure
                CASE
                    WHEN final_filename IS NOT NULL THEN
                        '/' || roaster_directory || '/' ||
                        regexp_replace(
                            regexp_replace(split_part(final_filename, '/', -1), '\\.json$', '', 'g'),
                            '_\\d{6}$', '', 'g'
                        )
                    ELSE ''
                END as bean_url_path,
                -- Add the date when this coffee was first scraped/added
                TRY_CAST(date_added AS TIMESTAMP) as date_added
            FROM all_coffee_beans_with_stock_status
            WHERE name IS NOT NULL AND name != ''
        """)

        # Get the maximum existing origin ID for incremental mode
        max_origin_id = 0
        if incremental:
            result = conn.execute("SELECT COALESCE(MAX(id), 0) FROM origins").fetchone()
            max_origin_id = result[0] if result else 0

        # Create a temporary table with varietal mappings for SQL lookups
        conn.execute("DROP TABLE IF EXISTS temp_varietal_mappings")
        conn.execute("""
            CREATE TEMPORARY TABLE temp_varietal_mappings (
                original_name VARCHAR,
                canonical_names VARCHAR[]
            )
        """)

        # Insert varietal mappings into the temporary table
        if varietal_mapping:
            mapping_rows = [(original, canonical) for original, canonical in varietal_mapping.items()]
            conn.executemany("INSERT INTO temp_varietal_mappings VALUES (?, ?)", mapping_rows)

        # Insert origins data from all beans (both in-stock and out-of-stock)
        conn.execute(f"""
            INSERT INTO origins (
                id, bean_id, country, region, region_normalized, producer, farm, farm_normalized,
                elevation_min, elevation_max, latitude, longitude, process, process_common_name,
                variety, variety_canonical, harvest_date
            )
            SELECT
                ROW_NUMBER() OVER (ORDER BY cb.id) + {max_origin_id} as id,
                cb.id as bean_id,
                COALESCE(t.origin.country, '') as country,
                COALESCE(t.origin.region, '') as region,
                normalize_region_name(COALESCE(t.origin.region, '')) as region_normalized,
                COALESCE(t.origin.producer, '') as producer,
                COALESCE(t.origin.farm, '') as farm,
                normalize_farm_name(COALESCE(t.origin.farm, '')) as farm_normalized,
                COALESCE(TRY_CAST(t.origin.elevation_min AS INTEGER), 0) as elevation_min,
                COALESCE(TRY_CAST(t.origin.elevation_max AS INTEGER), 0) as elevation_max,
                TRY_CAST(t.origin.latitude AS DOUBLE) as latitude,
                TRY_CAST(t.origin.longitude AS DOUBLE) as longitude,
                COALESCE(t.origin.process, '') as process,
                '' as process_common_name,  -- Will be populated after origins are inserted
                COALESCE(t.origin.variety, '') as variety,
                COALESCE(
                    vm.canonical_names,
                    CASE
                        WHEN COALESCE(t.origin.variety, '') = '' THEN CAST([] AS VARCHAR[])
                        ELSE CAST([t.origin.variety] AS VARCHAR[])
                    END
                ) as variety_canonical,
                TRY_CAST(t.origin.harvest_date AS TIMESTAMP) as harvest_date
            FROM all_coffee_beans_with_stock_status abs
            JOIN coffee_beans cb ON cb.filename = abs.final_filename
            CROSS JOIN UNNEST(abs.origins) AS t(origin)
            LEFT JOIN temp_varietal_mappings vm ON LOWER(COALESCE(t.origin.variety, '')) = LOWER(vm.original_name)
            WHERE abs.origins IS NOT NULL
        """)

        # Now update roaster names based on directory mapping using parameterized queries
        for directory_name, scraper_info in directory_to_roaster.items():
            conn.execute(
                """
                UPDATE coffee_beans
                SET roaster = ?
                WHERE filename LIKE ?
            """,
                [scraper_info.roaster_name, f"%/{directory_name}/%"],
            )

        # Apply processing methods mapping to convert process to process_common_name
        if processing_mapping:
            print("Applying processing methods mapping...")

            # Get all unique process values that need mapping
            raw_processes = conn.execute("""
                SELECT DISTINCT process, COUNT(*) as count
                FROM origins
                WHERE process IS NOT NULL AND process != ''
                GROUP BY process
                ORDER BY count DESC
            """).fetchall()

            mapping_stats = {"mapped": 0, "unchanged": 0}

            for process_value, count in raw_processes:
                common_name = processing_mapping.get(process_value)

                if common_name:
                    # Update all origins with this process value
                    conn.execute(
                        """
                        UPDATE origins
                        SET process_common_name = ?
                        WHERE process = ?
                    """,
                        [common_name, process_value],
                    )

                    mapping_stats["mapped"] += count
                else:
                    # Keep the original process name as the common name if no mapping exists
                    conn.execute(
                        """
                        UPDATE origins
                        SET process_common_name = process
                        WHERE process = ? AND (process_common_name IS NULL OR process_common_name = '')
                    """,
                        [process_value],
                    )
                    mapping_stats["unchanged"] += count

            mapped_count = mapping_stats["mapped"]
            unchanged_count = mapping_stats["unchanged"]
            print(f"Processing methods mapping complete: {mapped_count} mapped, {unchanged_count} unchanged")

        # Normalize country codes using the mapping
        if country_mapping:
            print("Normalizing country codes...")

            # Get all unique country values that need normalization from origins table
            raw_countries = conn.execute("""
                SELECT DISTINCT country, COUNT(*) as count
                FROM origins
                WHERE country IS NOT NULL AND country != ''
                GROUP BY country
                ORDER BY count DESC
            """).fetchall()

            normalization_stats = {"normalized": 0, "unchanged": 0}

            for country_value, count in raw_countries:
                normalized_country = normalize_country_code(country_value, country_mapping)

                if normalized_country != country_value:
                    # Update all origins with this country value
                    conn.execute(
                        """
                        UPDATE origins
                        SET country = ?
                        WHERE country = ?
                    """,
                        [normalized_country, country_value],
                    )

                    normalization_stats["normalized"] += count
                    print(f"  Normalized '{country_value}' -> '{normalized_country}' ({count} origins)")
                else:
                    normalization_stats["unchanged"] += count

            normalized_count = normalization_stats["normalized"]
            unchanged_count = normalization_stats["unchanged"]
            print(f"Country normalization complete: {normalized_count} normalized, {unchanged_count} unchanged")

        # Mark processed JSON files (in both full refresh and incremental mode)
        # This allows subsequent incremental updates to know what's been processed
        from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

        # Get list of files that were just processed
        processed_files_result = conn.execute("""
            SELECT DISTINCT filename
            FROM raw_coffee_data
        """).fetchall()

        if processed_files_result:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
            ) as progress:
                mark_task = progress.add_task(
                    f"[cyan]Marking {len(processed_files_result)} JSON files as processed...",
                    total=len(processed_files_result),
                )

                for (filename,) in processed_files_result:
                    if filename:
                        mark_file_processed(Path(filename), data_dir, "json")
                    progress.advance(mark_task)

        # Calculate USD prices for all coffee beans after currency rates are available
        print("Calculating USD prices for currency conversion...")
        await calculate_usd_prices()

        # Apply diffjson updates if any exist
        # Note: If any JSON files changed, their related diffjson tracking was removed above,
        # so those updates will be automatically re-applied
        await apply_diffjson_updates(data_dir, incremental, check_for_changes)

        # Get counts for logging
        result = conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()
        bean_count = result[0] if result else 0
        result = conn.execute("SELECT COUNT(*) FROM roasters").fetchone()
        roaster_count = result[0] if result else 0

        print(f"Loaded {bean_count} coffee beans from {roaster_count} roasters using DuckDB glob with registry")

        # Get counts for in-stock vs out-of-stock
        in_stock_result = conn.execute("SELECT COUNT(*) FROM coffee_beans WHERE in_stock = true").fetchone()
        out_of_stock_result = conn.execute("SELECT COUNT(*) FROM coffee_beans WHERE in_stock = false").fetchone()
        in_stock_count = in_stock_result[0] if in_stock_result else 0
        out_of_stock_count = out_of_stock_result[0] if out_of_stock_result else 0

        print(f"  - In stock: {in_stock_count} beans")
        print(f"  - Out of stock: {out_of_stock_count} beans")

        # Commit all changes before cleaning up views
        conn.commit()

        # Clean up temporary views and tables
        conn.execute("DROP VIEW IF EXISTS raw_coffee_data")
        conn.execute("DROP VIEW IF EXISTS diffjson_scrape_dates")
        conn.execute("DROP VIEW IF EXISTS latest_scrapes")
        conn.execute("DROP VIEW IF EXISTS earliest_coffee_dates")
        conn.execute("DROP VIEW IF EXISTS latest_coffee_data")
        conn.execute("DROP VIEW IF EXISTS all_coffee_beans_with_stock_status")
        conn.execute("DROP VIEW IF EXISTS filtered_coffee_data")
        conn.execute("DROP TABLE IF EXISTS raw_coffee_data_temp")

    except Exception as e:
        print(f"Error loading coffee data with DuckDB glob: {e}")
        # Fallback: if glob fails, we could implement a simple directory scan
        # For now, just log the error
        raise


async def load_tasting_notes_categories():
    """Load tasting notes categorizations from CSV file into database."""
    csv_file_path = Path(__file__).parent.parent / "database" / "tasting_notes_categorized.csv"

    # Check if the CSV file exists
    if not csv_file_path.exists():
        print(f"Tasting notes categories CSV file not found: {csv_file_path}")
        print("Skipping tasting notes categories loading")
        return

    try:
        # Clear existing data first
        conn.execute("DELETE FROM tasting_notes_categories")

        # Load data from CSV
        conn.execute(f"""
            INSERT INTO tasting_notes_categories
            SELECT * FROM read_csv_auto('{csv_file_path}')
        """)

        # Create the comprehensive view that joins coffee beans with categorized tasting notes
        conn.execute("""
            CREATE OR REPLACE VIEW coffee_beans_with_categorized_notes AS
            SELECT
                cb.*,
                list(DISTINCT tnc.primary_category) as primary_categories,
                list(DISTINCT tnc.secondary_category) as secondary_categories,
                list(DISTINCT tnc.tertiary_category) as tertiary_categories,
                avg(tnc.confidence) as avg_categorization_confidence
            FROM coffee_beans cb
            LEFT JOIN (
                SELECT
                    cb.id as bean_id,
                    tnc.primary_category,
                    tnc.secondary_category,
                    tnc.tertiary_category,
                    tnc.confidence
                FROM coffee_beans cb,
                     unnest(cb.tasting_notes) as note_table(note)
                INNER JOIN tasting_notes_categories tnc ON note_table.note = tnc.tasting_note
                WHERE cb.tasting_notes IS NOT NULL
            ) tnc ON cb.id = tnc.bean_id
            GROUP BY cb.id, cb.name, cb.roaster, cb.url, cb.is_single_origin,
                     cb.price_paid_for_green_coffee, cb.currency_of_price_paid_for_green_coffee,
                     cb.roast_level, cb.roast_profile, cb.weight, cb.price, cb.currency, cb.price_usd,
                     cb.is_decaf, cb.cupping_score, cb.tasting_notes, cb.description,
                     cb.in_stock, cb.scraped_at, cb.scraper_version, cb.filename,
                     cb.image_url, cb.clean_url_slug, cb.bean_url_path, cb.date_added
        """)

        # Get count of loaded categorizations
        result = conn.execute("SELECT COUNT(*) FROM tasting_notes_categories").fetchone()
        categorizations_count = result[0] if result else 0
        print(f"Loaded {categorizations_count} tasting note categorizations from {csv_file_path}")
        print("Created coffee_beans_with_categorized_notes view")

    except Exception as e:
        print(f"Error loading tasting notes categories: {e}")
        # Don't raise the error as this is optional data


async def main(incremental: bool = False, check_for_changes: bool = False):
    """Initialize database and load coffee bean data.

    Args:
        incremental: If True, only process new/changed files. If False, full refresh (default).
        check_for_changes: If True (with incremental), verify file checksums to detect changes.
    """
    from kissaten.api.fx import update_currency_rates

    await init_database(incremental=incremental, check_for_changes=check_for_changes)
    # Load currency rates first, before loading coffee data (which calculates USD prices)
    await update_currency_rates(conn)
    await load_coffee_data(
        data_dir=Path(__file__).parent.parent.parent.parent / "data" / "roasters",
        incremental=incremental,
        check_for_changes=check_for_changes,
    )
    await load_tasting_notes_categories()
    conn.close()


if __name__ == "__main__":
    import asyncio

    # Check for incremental mode via environment variable
    incremental_mode = os.environ.get("KISSATEN_INCREMENTAL", "0") == "1"
    check_for_changes_mode = os.environ.get("KISSATEN_CHECK_FOR_CHANGES", "0") == "1"
    asyncio.run(main(incremental=incremental_mode, check_for_changes=check_for_changes_mode))
