"""
FastAPI application for Kissaten coffee bean search API.
"""

from pathlib import Path
from typing import Optional

import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from kissaten.schemas import APIResponse

# Initialize FastAPI app
app = FastAPI(
    title="Kissaten Coffee Bean API",
    description="Search and discover coffee beans from roasters worldwide",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
DATABASE_PATH = Path(__file__).parent.parent.parent.parent / "data" / "kissaten.duckdb"
conn = duckdb.connect(str(DATABASE_PATH))

@app.get("/health")
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Kissaten API is running"}

# Initialize database and load data on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and load coffee bean data."""
    await init_database()
    await load_coffee_data()

async def init_database():
    """Initialize the DuckDB database with required tables."""
    # Create coffee beans table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coffee_beans (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            roaster VARCHAR,
            url VARCHAR,
            country VARCHAR,
            region VARCHAR,
            producer VARCHAR,
            farm VARCHAR,
            elevation INTEGER,
            is_single_origin BOOLEAN,
            process VARCHAR,
            variety VARCHAR,
            harvest_date TIMESTAMP,
            price_paid_for_green_coffee DOUBLE,
            currency_of_price_paid_for_green_coffee VARCHAR,
            roast_level VARCHAR,
            weight INTEGER,
            price DOUBLE,
            currency VARCHAR,
            is_decaf BOOLEAN,
            tasting_notes VARCHAR[], -- Array of strings
            description TEXT,
            in_stock BOOLEAN,
            scraped_at TIMESTAMP,
            scraper_version VARCHAR
        )
    """)

    # Add is_decaf column if it doesn't exist (migration)
    try:
        conn.execute("ALTER TABLE coffee_beans ADD COLUMN is_decaf BOOLEAN DEFAULT false")
    except Exception:
        # Column already exists or other error, ignore
        pass

    # Create roasters table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS roasters (
            id INTEGER PRIMARY KEY,
            name VARCHAR UNIQUE,
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

async def load_coffee_data():
    """Load coffee bean data from JSON files into DuckDB using DuckDB's native glob functionality."""
    data_dir = Path(__file__).parent.parent.parent.parent / "data" / "roasters"
    countrycodes_path = Path(__file__).parent.parent / "database" / "countrycodes.csv"

    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        return

    # Clear existing data
    conn.execute("DELETE FROM coffee_beans")
    conn.execute("DELETE FROM roasters")
    conn.execute("DELETE FROM country_codes")

    # Load country codes from CSV
    if countrycodes_path.exists():
        try:
            conn.execute(f"""
                INSERT INTO country_codes
                SELECT * FROM read_csv('{countrycodes_path}', header=true, auto_detect=true)
            """)
            country_count = conn.execute("SELECT COUNT(*) FROM country_codes").fetchone()[0]
            print(f"Loaded {country_count} country codes")
        except Exception as e:
            print(f"Error loading country codes: {e}")
    else:
        print(f"Country codes file not found: {countrycodes_path}")

    try:
        # Use DuckDB's glob functionality to read all JSON files directly
        json_pattern = str(data_dir / "**" / "*.json")

        # Create a temporary view with the raw JSON data, including file path for roaster extraction
        conn.execute(f"""
            CREATE OR REPLACE TEMPORARY VIEW raw_coffee_data AS
            SELECT
                json_data.*,
                -- Extract roaster name from file path
                regexp_replace(
                    regexp_replace(
                        split_part(filename, '/', -3),  -- Get roaster directory name
                        '_', ' ', 'g'                   -- Replace underscores with spaces
                    ),
                    '(^|\\s)(\\w)',
                    '\\1\\U\\2', 'g'                    -- Title case
                ) as roaster_from_path,
                -- Add is_decaf field with default value (since not in JSON yet)
                false as is_decaf_field,
                filename
            FROM read_json('{json_pattern}',
                filename=true,
                auto_detect=true,
                union_by_name=true,
                ignore_errors=true
            ) as json_data
        """)

        # Insert roasters from the data
        conn.execute("""
            INSERT INTO roasters (id, name, website, location, email, active, last_scraped, total_beans_scraped)
            SELECT
                ROW_NUMBER() OVER (ORDER BY roaster_name) as id,
                roaster_name as name,
                '' as website,
                '' as location,
                '' as email,
                true as active,
                NULL as last_scraped,
                0 as total_beans_scraped
            FROM (
                SELECT DISTINCT COALESCE(roaster, roaster_from_path) as roaster_name
                FROM raw_coffee_data
                WHERE COALESCE(roaster, roaster_from_path) IS NOT NULL
            ) distinct_roasters
        """)

        # Insert coffee beans with proper data transformation and null handling
        conn.execute("""
                INSERT INTO coffee_beans (
                    id, name, roaster, url, country, region, producer, farm, elevation,
                    is_single_origin, process, variety, harvest_date, price_paid_for_green_coffee,
                    currency_of_price_paid_for_green_coffee, roast_level, weight, price, currency,
                is_decaf, tasting_notes, description, in_stock, scraped_at, scraper_version
            )
            SELECT
                ROW_NUMBER() OVER (ORDER BY name) as id,
                COALESCE(name, '') as name,
                COALESCE(roaster, roaster_from_path, '') as roaster,
                COALESCE(url, '') as url,
                COALESCE(origin.country, '') as country,
                COALESCE(origin.region, '') as region,
                COALESCE(origin.producer, '') as producer,
                COALESCE(origin.farm, '') as farm,
                COALESCE(TRY_CAST(origin.elevation AS INTEGER), 0) as elevation,
                COALESCE(is_single_origin, true) as is_single_origin,
                COALESCE(process, '') as process,
                COALESCE(variety, '') as variety,
                TRY_CAST(harvest_date AS TIMESTAMP) as harvest_date,
                TRY_CAST(price_paid_for_green_coffee AS DOUBLE) as price_paid_for_green_coffee,
                currency_of_price_paid_for_green_coffee,
                roast_level,
                TRY_CAST(weight AS INTEGER) as weight,
                TRY_CAST(price AS DOUBLE) as price,
                COALESCE(currency, 'EUR') as currency,
                is_decaf_field as is_decaf,
                COALESCE(tasting_notes, []) as tasting_notes,
                COALESCE(description, '') as description,
                COALESCE(in_stock, true) as in_stock,
                TRY_CAST(scraped_at AS TIMESTAMP) as scraped_at,
                COALESCE(scraper_version, '1.0') as scraper_version
            FROM raw_coffee_data
            WHERE name IS NOT NULL AND name != ''
        """)

        # Get counts for logging
        bean_count = conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()[0]
        roaster_count = conn.execute("SELECT COUNT(*) FROM roasters").fetchone()[0]

        print(f"Loaded {bean_count} coffee beans from {roaster_count} roasters using DuckDB glob")

        # Clean up temporary view
        conn.execute("DROP VIEW IF EXISTS raw_coffee_data")

    except Exception as e:
        print(f"Error loading coffee data with DuckDB glob: {e}")
        # Fallback: if glob fails, we could implement a simple directory scan
        # For now, just log the error
        raise

# API Endpoints

@app.get("/", response_model=APIResponse[dict])
async def root():
    """Root endpoint with API information."""
    return APIResponse.success_response(
        data={"message": "Welcome to Kissaten Coffee Bean API"},
        metadata={"version": "1.0.0"}
    )



@app.get("/api/v1/search", response_model=APIResponse[list[dict]])
async def search_coffee_beans(
    query: Optional[str] = Query(None, description="Search query text"),
    roaster: Optional[str] = Query(None, description="Filter by roaster name"),
    country: Optional[str] = Query(None, description="Filter by origin country"),
    roast_level: Optional[str] = Query(None, description="Filter by roast level"),
    process: Optional[str] = Query(None, description="Filter by processing method"),
    variety: Optional[str] = Query(None, description="Filter by coffee variety"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    min_weight: Optional[int] = Query(None, description="Minimum weight filter (grams)"),
    max_weight: Optional[int] = Query(None, description="Maximum weight filter (grams)"),
    in_stock_only: bool = Query(False, description="Show only in-stock items"),
    is_decaf: Optional[bool] = Query(None, description="Filter by decaf status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("name", description="Sort field"),
    sort_order: str = Query("asc", description="Sort order (asc/desc)")
):
    """Search coffee beans with filters and pagination."""

    # Build SQL query
    where_conditions = []
    params = []

    if query:
        where_conditions.append("(cb.name ILIKE ? OR cb.description ILIKE ? OR array_to_string(cb.tasting_notes, ' ') ILIKE ?)")
        search_term = f"%{query}%"
        params.extend([search_term, search_term, search_term])

    if roaster:
        where_conditions.append("cb.roaster ILIKE ?")
        params.append(f"%{roaster}%")

    if country:
        where_conditions.append("cb.country ILIKE ?")
        params.append(f"%{country}%")

    if roast_level:
        where_conditions.append("cb.roast_level ILIKE ?")
        params.append(f"%{roast_level}%")

    if process:
        where_conditions.append("cb.process ILIKE ?")
        params.append(f"%{process}%")

    if variety:
        where_conditions.append("cb.variety ILIKE ?")
        params.append(f"%{variety}%")

    if min_price is not None:
        where_conditions.append("cb.price >= ?")
        params.append(min_price)

    if max_price is not None:
        where_conditions.append("cb.price <= ?")
        params.append(max_price)

    if min_weight is not None:
        where_conditions.append("cb.weight >= ?")
        params.append(min_weight)

    if max_weight is not None:
        where_conditions.append("cb.weight <= ?")
        params.append(max_weight)

    if in_stock_only:
        where_conditions.append("cb.in_stock = true")

    if is_decaf is not None:
        where_conditions.append("cb.is_decaf = ?")
        params.append(is_decaf)

    # Build WHERE clause
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)

    # Validate sort fields
    valid_sort_fields = ['cb.name', 'cb.roaster', 'cb.price', 'cb.weight', 'cb.scraped_at', 'cb.country', 'cb.variety']
    sort_field_mapping = {
        'name': 'cb.name',
        'roaster': 'cb.roaster',
        'price': 'cb.price',
        'weight': 'cb.weight',
        'scraped_at': 'cb.scraped_at',
        'country': 'cb.country',
        'variety': 'cb.variety'
    }

    if sort_by in sort_field_mapping:
        sort_by = sort_field_mapping[sort_by]
    elif sort_by not in valid_sort_fields:
        sort_by = 'cb.name'

    if sort_order.lower() not in ['asc', 'desc']:
        sort_order = 'asc'

    # Get total count
    count_query = f"SELECT COUNT(*) FROM coffee_beans cb {where_clause}"
    total_count = conn.execute(count_query, params).fetchone()[0]

    # Calculate pagination
    offset = (page - 1) * per_page
    total_pages = (total_count + per_page - 1) // per_page

    # Build main query with country name lookup
    main_query = f"""
        SELECT
            cb.id, cb.name, cb.roaster, cb.url, cb.country, cb.region, cb.producer, cb.farm, cb.elevation,
            cb.is_single_origin, cb.process, cb.variety, cb.harvest_date, cb.price_paid_for_green_coffee,
            cb.currency_of_price_paid_for_green_coffee, cb.roast_level, cb.weight, cb.price, cb.currency,
            cb.is_decaf, cb.tasting_notes, cb.description, cb.in_stock, cb.scraped_at, cb.scraper_version,
            cc.name as country_full_name
        FROM coffee_beans cb
        LEFT JOIN country_codes cc ON cb.country = cc.alpha_2
        {where_clause}
        ORDER BY {sort_by} {sort_order.upper()}
        LIMIT ? OFFSET ?
    """

    results = conn.execute(main_query, params + [per_page, offset]).fetchall()

    # Convert results to dictionaries
    columns = [
        'id', 'name', 'roaster', 'url', 'country', 'region', 'producer', 'farm', 'elevation',
        'is_single_origin', 'process', 'variety', 'harvest_date', 'price_paid_for_green_coffee',
        'currency_of_price_paid_for_green_coffee', 'roast_level', 'weight', 'price', 'currency',
        'is_decaf', 'tasting_notes', 'description', 'in_stock', 'scraped_at', 'scraper_version',
        'country_full_name'
    ]

    coffee_beans = []
    for row in results:
        bean_dict = dict(zip(columns, row))
        coffee_beans.append(bean_dict)

    # Create pagination info
    from kissaten.schemas.search import PaginationInfo
    pagination = PaginationInfo(
        page=page,
        per_page=per_page,
        total_items=total_count,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )

    return APIResponse.success_response(
        data=coffee_beans,
        pagination=pagination,
        metadata={
            "total_results": total_count,
            "search_query": query,
            "filters_applied": len(where_conditions)
        }
    )

@app.get("/api/v1/roasters", response_model=APIResponse[list[dict]])
async def get_roasters():
    """Get all roasters with their coffee bean counts."""
    query = """
        SELECT
            r.id, r.name, r.website, r.location, r.email, r.active,
            r.last_scraped, r.total_beans_scraped,
            COUNT(cb.id) as current_beans_count
        FROM roasters r
        LEFT JOIN coffee_beans cb ON r.name = cb.roaster
        GROUP BY r.id, r.name, r.website, r.location, r.email, r.active, r.last_scraped, r.total_beans_scraped
        ORDER BY r.name
    """

    results = conn.execute(query).fetchall()

    roasters = []
    for row in results:
        roaster_dict = {
            'id': row[0],
            'name': row[1],
            'website': row[2],
            'location': row[3],
            'email': row[4],
            'active': row[5],
            'last_scraped': row[6],
            'total_beans_scraped': row[7],
            'current_beans_count': row[8]
        }
        roasters.append(roaster_dict)

    return APIResponse.success_response(data=roasters)

@app.get("/api/v1/roasters/{roaster_name}/beans", response_model=APIResponse[list[dict]])
async def get_roaster_beans(roaster_name: str):
    """Get all coffee beans from a specific roaster with full country names."""
    query = """
        SELECT
            cb.id, cb.name, cb.roaster, cb.url, cb.country, cb.region, cb.producer, cb.farm, cb.elevation,
            cb.is_single_origin, cb.process, cb.variety, cb.harvest_date, cb.price_paid_for_green_coffee,
            cb.currency_of_price_paid_for_green_coffee, cb.roast_level, cb.weight, cb.price, cb.currency,
            cb.is_decaf, cb.tasting_notes, cb.description, cb.in_stock, cb.scraped_at, cb.scraper_version,
            cc.name as country_full_name
        FROM coffee_beans cb
        LEFT JOIN country_codes cc ON cb.country = cc.alpha_2
        WHERE cb.roaster ILIKE ?
        ORDER BY cb.name
    """

    results = conn.execute(query, [f"%{roaster_name}%"]).fetchall()

    if not results:
        raise HTTPException(status_code=404, detail=f"No beans found for roaster: {roaster_name}")

    columns = [
        'id', 'name', 'roaster', 'url', 'country', 'region', 'producer', 'farm', 'elevation',
        'is_single_origin', 'process', 'variety', 'harvest_date', 'price_paid_for_green_coffee',
        'currency_of_price_paid_for_green_coffee', 'roast_level', 'weight', 'price', 'currency',
        'is_decaf', 'tasting_notes', 'description', 'in_stock', 'scraped_at', 'scraper_version',
        'country_full_name'
    ]

    coffee_beans = []
    for row in results:
        bean_dict = dict(zip(columns, row))
        coffee_beans.append(bean_dict)

    return APIResponse.success_response(data=coffee_beans)

@app.get("/api/v1/countries", response_model=APIResponse[list[dict]])
async def get_countries():
    """Get all coffee origin countries with bean counts and full country names."""
    query = """
        SELECT
            cb.country,
            cc.name as country_full_name,
            COUNT(*) as bean_count,
            COUNT(DISTINCT cb.roaster) as roaster_count
        FROM coffee_beans cb
        LEFT JOIN country_codes cc ON cb.country = cc.alpha_2
        WHERE cb.country IS NOT NULL AND cb.country != ''
        GROUP BY cb.country, cc.name
        ORDER BY bean_count DESC
    """

    results = conn.execute(query).fetchall()

    countries = []
    for row in results:
        country_dict = {
            'country_code': row[0],
            'country_name': row[1] or row[0],  # Fallback to code if name not found
            'bean_count': row[2],
            'roaster_count': row[3]
        }
        countries.append(country_dict)

    return APIResponse.success_response(data=countries)

@app.get("/api/v1/country-codes", response_model=APIResponse[list[dict]])
async def get_country_codes():
    """Get all country codes with full details."""
    query = """
        SELECT
            name, alpha_2, alpha_3, country_code, region, sub_region
        FROM country_codes
        ORDER BY name
    """

    results = conn.execute(query).fetchall()

    country_codes = []
    for row in results:
        country_dict = {
            'name': row[0],
            'alpha_2': row[1],
            'alpha_3': row[2],
            'country_code': row[3],
            'region': row[4],
            'sub_region': row[5]
        }
        country_codes.append(country_dict)

    return APIResponse.success_response(data=country_codes)

@app.get("/api/v1/stats", response_model=APIResponse[dict])
async def get_stats():
    """Get database statistics and analytics."""

    # Total counts
    total_beans = conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()[0]
    total_roasters = conn.execute("SELECT COUNT(*) FROM roasters").fetchone()[0]
    total_countries = conn.execute("SELECT COUNT(DISTINCT country) FROM coffee_beans WHERE country IS NOT NULL AND country != ''").fetchone()[0]

    # Price statistics
    price_stats = conn.execute("""
        SELECT
            MIN(price) as min_price,
            MAX(price) as max_price,
            AVG(price) as avg_price,
            MEDIAN(price) as median_price
        FROM coffee_beans
        WHERE price IS NOT NULL AND price > 0
    """).fetchone()

    # Top roasters by bean count
    top_roasters = conn.execute("""
        SELECT roaster, COUNT(*) as bean_count
        FROM coffee_beans
        GROUP BY roaster
        ORDER BY bean_count DESC
        LIMIT 5
    """).fetchall()

    # Most common processes
    top_processes = conn.execute("""
        SELECT process, COUNT(*) as count
        FROM coffee_beans
        WHERE process IS NOT NULL AND process != ''
        GROUP BY process
        ORDER BY count DESC
        LIMIT 5
    """).fetchall()

    stats = {
        'total_beans': total_beans,
        'total_roasters': total_roasters,
        'total_countries': total_countries,
        'price_statistics': {
            'min_price': price_stats[0] if price_stats[0] else 0,
            'max_price': price_stats[1] if price_stats[1] else 0,
            'avg_price': round(price_stats[2], 2) if price_stats[2] else 0,
            'median_price': round(price_stats[3], 2) if price_stats[3] else 0
        },
        'top_roasters': [{'roaster': r[0], 'bean_count': r[1]} for r in top_roasters],
        'top_processes': [{'process': p[0], 'count': p[1]} for p in top_processes]
    }

    return APIResponse.success_response(data=stats)

@app.get("/api/v1/beans/{bean_id}", response_model=APIResponse[dict])
async def get_coffee_bean(bean_id: int):
    """Get a specific coffee bean by ID with full country name."""
    query = """
        SELECT
            cb.id, cb.name, cb.roaster, cb.url, cb.country, cb.region, cb.producer, cb.farm, cb.elevation,
            cb.is_single_origin, cb.process, cb.variety, cb.harvest_date, cb.price_paid_for_green_coffee,
            cb.currency_of_price_paid_for_green_coffee, cb.roast_level, cb.weight, cb.price, cb.currency,
            cb.is_decaf, cb.tasting_notes, cb.description, cb.in_stock, cb.scraped_at, cb.scraper_version,
            cc.name as country_full_name
        FROM coffee_beans cb
        LEFT JOIN country_codes cc ON cb.country = cc.alpha_2
        WHERE cb.id = ?
    """

    result = conn.execute(query, [bean_id]).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail=f"Coffee bean with ID {bean_id} not found")

    columns = [
        'id', 'name', 'roaster', 'url', 'country', 'region', 'producer', 'farm', 'elevation',
        'is_single_origin', 'process', 'variety', 'harvest_date', 'price_paid_for_green_coffee',
        'currency_of_price_paid_for_green_coffee', 'roast_level', 'weight', 'price', 'currency',
        'is_decaf', 'tasting_notes', 'description', 'in_stock', 'scraped_at', 'scraper_version',
        'country_full_name'
    ]

    bean_dict = dict(zip(columns, result))

    return APIResponse.success_response(data=bean_dict)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
