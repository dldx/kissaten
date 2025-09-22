from pathlib import Path

import duckdb

from kissaten.scrapers import get_registry

if __name__ != "__main__":
    # Database connection
    DATABASE_PATH = Path(__file__).parent.parent.parent.parent / "data" / "kissaten.duckdb"
    conn = duckdb.connect(str(DATABASE_PATH))
else:
    RW_DATABASE_PATH = Path(__file__).parent.parent.parent.parent / "data" / "rw_kissaten.duckdb"  # noqa: N806
    conn = duckdb.connect(str(RW_DATABASE_PATH))


async def init_database():
    """Initialize the DuckDB database with required tables."""
    # Clear existing data
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
            producer VARCHAR,
            farm VARCHAR,
            elevation_min INTEGER DEFAULT 0,
            elevation_max INTEGER DEFAULT 0,
            latitude DOUBLE,
            longitude DOUBLE,
            process VARCHAR,
            process_common_name VARCHAR,
            variety VARCHAR,
            harvest_date TIMESTAMP,
            FOREIGN KEY (bean_id) REFERENCES coffee_beans (id)
        )
    """)

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

    # Create a view to simplify queries by joining coffee beans with their primary origin
    conn.execute("""
        CREATE OR REPLACE VIEW coffee_beans_with_origin AS
        SELECT
            cb.*,
            o.country,
            o.region,
            o.producer,
            o.farm,
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


async def apply_diffjson_updates(data_dir: Path):
    """Apply partial updates from diffjson files to existing coffee beans."""
    import glob
    import json

    from kissaten.schemas.coffee_bean import CoffeeBeanDiffUpdate

    # Find all diffjson files
    diffjson_pattern = str(data_dir / "**" / "*.diffjson")
    diffjson_files = glob.glob(diffjson_pattern, recursive=True)

    if not diffjson_files:
        print("No diffjson files found - skipping partial updates")
        return

    print(f"Processing {len(diffjson_files)} diffjson update files...")
    updates_applied = 0

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

            # Extract URL from validated update data
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


async def load_coffee_data(data_dir: Path):
    """Load coffee bean data from JSON files into DuckDB using DuckDB's native glob functionality."""
    countrycodes_path = Path(__file__).parent.parent / "database" / "countrycodes.csv"
    processing_methods_mapping_path = Path(__file__).parent.parent / "database/processing_methods_mappings.json"

    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        return

    # Load processing methods mapping
    processing_mapping = {}
    if processing_methods_mapping_path.exists():
        try:
            import json

            with open(processing_methods_mapping_path, "r", encoding="utf-8") as f:
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
            conn.execute(f"""
                INSERT INTO country_codes
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
            conn.execute(f"""
                INSERT INTO roaster_location_codes
                SELECT * FROM read_csv('{roaster_location_codes_path}', header=true, auto_detect=true)
            """)
            result = conn.execute("SELECT COUNT(*) FROM roaster_location_codes").fetchone()
            location_count = result[0] if result else 0
            print(f"Loaded {location_count} roaster location codes")
        except Exception as e:
            print(f"Error loading roaster location codes: {e}")
    else:
        print(f"Roaster location codes file not found: {roaster_location_codes_path}")

    # Insert roasters from the registry
    try:
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

        # Use a proper INSERT with all values
        for values in roaster_values:
            conn.execute(
                """
                INSERT INTO roasters (
                    id, name, slug, website, location, email, active,
                    last_scraped, total_beans_scraped
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (name) DO NOTHING
            """,
                values,
            )

        result = conn.execute("SELECT COUNT(*) FROM roasters").fetchone()
        roaster_count = result[0] if result else 0
        print(f"Loaded {roaster_count} roasters from registry")
    except Exception as e:
        print(f"Error inserting roasters from registry: {e}")

    try:
        # Use DuckDB's glob functionality to read all JSON files directly
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

        # Create a view to identify the latest scrape date for each roaster
        conn.execute("""
            CREATE OR REPLACE TEMPORARY VIEW latest_scrapes AS
            SELECT
                roaster_directory,
                MAX(scrape_date) as latest_scrape_date
            FROM raw_coffee_data
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
                COALESCE(latest_data.scraper_version, rcd.scraper_version) as final_scraper_version,
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

        # Insert all coffee beans with correct stock status
        conn.execute("""
            INSERT INTO coffee_beans (
                id, name, roaster, url, is_single_origin, price_paid_for_green_coffee,
                currency_of_price_paid_for_green_coffee, roast_level, roast_profile, weight, price, currency,
                price_usd, is_decaf, cupping_score, tasting_notes, description, in_stock, scraped_at, scraper_version,
                filename, image_url, clean_url_slug, bean_url_path, date_added
            )
            SELECT
                ROW_NUMBER() OVER (ORDER BY calculated_in_stock DESC, name) as id,
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
                is_decaf,
                cupping_score,
                COALESCE(tasting_notes, []) as tasting_notes,
                COALESCE(description, '') as description,
                calculated_in_stock as in_stock,  -- Use calculated stock status
                TRY_CAST(final_scraped_at AS TIMESTAMP) as scraped_at,
                COALESCE(final_scraper_version, '1.0') as scraper_version,
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

        # Insert origins data from all beans (both in-stock and out-of-stock)
        conn.execute("""
            INSERT INTO origins (
                id, bean_id, country, region, producer, farm, elevation_min, elevation_max,
                latitude, longitude, process, process_common_name, variety, harvest_date
            )
            SELECT
                ROW_NUMBER() OVER (ORDER BY cb.id) as id,
                cb.id as bean_id,
                COALESCE(t.origin.country, '') as country,
                COALESCE(t.origin.region, '') as region,
                COALESCE(t.origin.producer, '') as producer,
                COALESCE(t.origin.farm, '') as farm,
                COALESCE(TRY_CAST(t.origin.elevation_min AS INTEGER), 0) as elevation_min,
                COALESCE(TRY_CAST(t.origin.elevation_max AS INTEGER), 0) as elevation_max,
                TRY_CAST(t.origin.latitude AS DOUBLE) as latitude,
                TRY_CAST(t.origin.longitude AS DOUBLE) as longitude,
                COALESCE(t.origin.process, '') as process,
                '' as process_common_name,  -- Will be populated after origins are inserted
                COALESCE(t.origin.variety, '') as variety,
                TRY_CAST(t.origin.harvest_date AS TIMESTAMP) as harvest_date
            FROM all_coffee_beans_with_stock_status abs
            JOIN coffee_beans cb ON cb.filename = abs.final_filename
            CROSS JOIN UNNEST(abs.origins) AS t(origin)
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

        # Calculate USD prices for all coffee beans after currency rates are available
        print("Calculating USD prices for currency conversion...")
        await calculate_usd_prices()

        # Apply diffjson updates if any exist
        await apply_diffjson_updates(data_dir)

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

        # Clean up temporary views
        conn.execute("DROP VIEW IF EXISTS raw_coffee_data")
        conn.execute("DROP VIEW IF EXISTS latest_scrapes")
        conn.execute("DROP VIEW IF EXISTS earliest_coffee_dates")
        conn.execute("DROP VIEW IF EXISTS latest_coffee_data")
        conn.execute("DROP VIEW IF EXISTS all_coffee_beans_with_stock_status")

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


async def main():
    """Initialize database and load coffee bean data."""
    from kissaten.api.fx import update_currency_rates

    await init_database()
    # Load currency rates first, before loading coffee data (which calculates USD prices)
    await update_currency_rates(conn)
    await load_coffee_data(data_dir=Path(__file__).parent.parent.parent.parent / "data" / "roasters")
    await load_tasting_notes_categories()
    conn.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
