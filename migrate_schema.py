#!/usr/bin/env python3
"""Migration tool to convert coffee bean JSON data from old schema to new schema.

This script migrates data from the old schema format to the new schema format:
- Converts single 'origin' field to 'origins' list with Bean objects
- Moves 'process' and 'variety' fields from CoffeeBean to Bean level
- Adds missing fields with appropriate defaults
- Preserves all existing data
"""

import json
import logging
import sys
from datetime import datetime
from glob import glob
from pathlib import Path
from typing import Any

# Import the Pydantic schema for validation
from src.kissaten.schemas.coffee_bean import CoffeeBean

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def convert_roast_level(roast_level: str | None) -> str | None:
    """Convert roast level to valid enum value."""
    if not roast_level:
        return None

    # Mapping of invalid roast levels to valid ones
    roast_mapping = {
        "Filter": "Medium",  # Filter roasts are typically lighter
        "Espresso": "Medium",  # Espresso roasts are typically darker
        "Omni": "Medium",  # Omni roasts are typically medium
    }

    # If it's already a valid roast level, return as-is
    valid_levels = ["Light", "Medium-Light", "Medium", "Medium-Dark", "Dark"]
    if roast_level in valid_levels:
        return roast_level

    # Try to map invalid values
    mapped_level = roast_mapping.get(roast_level)
    if mapped_level:
        logger.debug(f"Mapped roast level '{roast_level}' to '{mapped_level}'")
        return mapped_level

    # If we can't map it, log and return None
    logger.warning(f"Unknown roast level '{roast_level}', setting to None")
    return None


def convert_harvest_date(date_str: str | None) -> str | None:
    """Convert harvest date string to ISO format if needed."""
    if not date_str:
        return None

    try:
        # Try to parse existing format
        if isinstance(date_str, str):
            # If it's already a valid datetime string, parse and convert to ISO
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

            # Validate the date is reasonable for coffee harvest
            now = datetime.now(dt.tzinfo or None)
            min_date = datetime(2020, 1, 1, tzinfo=dt.tzinfo)

            # If the date is in the future or before 2020, return None
            if dt > now:
                logger.warning(f"Harvest date '{date_str}' is in the future, setting to None")
                return None
            if dt < min_date:
                logger.warning(f"Harvest date '{date_str}' is before 2020, setting to None")
                return None

            return dt.isoformat()
        return date_str
    except Exception as e:
        logger.warning(f"Could not parse harvest date '{date_str}': {e}")
        return None
def migrate_coffee_bean(old_data: dict[str, Any]) -> dict[str, Any]:
    """Migrate a single coffee bean from old schema to new schema.

    Args:
        old_data: Coffee bean data in old schema format

    Returns:
        Coffee bean data in new schema format
    """
    # Start with the basic fields that remain the same
    new_data = {
        "name": old_data.get("name"),
        "roaster": old_data.get("roaster"),
        "url": old_data.get("url"),
        "image_url": old_data.get("image_url"),
        "is_single_origin": old_data.get("is_single_origin", True),
        "price_paid_for_green_coffee": old_data.get("price_paid_for_green_coffee"),
        "currency_of_price_paid_for_green_coffee": old_data.get("currency_of_price_paid_for_green_coffee"),
        "roast_level": convert_roast_level(old_data.get("roast_level")),
        "roast_profile": old_data.get("roast_profile"),
        "weight": old_data.get("weight"),
        "price": old_data.get("price"),
        "currency": old_data.get("currency", "GBP"),
        "is_decaf": old_data.get("is_decaf", False),
        "cupping_score": old_data.get("cupping_score"),
        "tasting_notes": old_data.get("tasting_notes", []),
        "description": old_data.get("description"),
        "in_stock": old_data.get("in_stock"),
        "scraped_at": old_data.get("scraped_at"),
        "scraper_version": old_data.get("scraper_version", "1.0"),
        "raw_data": old_data.get("raw_data")
    }

    # Convert the origin field to origins list
    old_origin = old_data.get("origin", {})

    # Create the new Bean object
    bean = {
        "country": old_origin.get("country"),
        "region": old_origin.get("region"),
        "producer": old_origin.get("producer"),
        "farm": old_origin.get("farm"),
        "elevation": old_origin.get("elevation", 0),
        "latitude": old_origin.get("latitude"),
        "longitude": old_origin.get("longitude"),
        # Move process and variety from coffee level to bean level
        "process": old_data.get("process"),
        "variety": old_data.get("variety"),
        "harvest_date": convert_harvest_date(old_data.get("harvest_date"))
    }

    # Set the origins as a list containing the single bean
    new_data["origins"] = [bean]

    return new_data


def migrate_file(file_path: Path, dry_run: bool = False, validate: bool = True) -> bool:
    """Migrate a single JSON file from old schema to new schema.

    Args:
        file_path: Path to the JSON file to migrate
        dry_run: If True, only validate migration without writing files
        validate: If True, validate migrated data with Pydantic schema

    Returns:
        True if migration was successful, False otherwise
    """
    try:
        # Read the old data
        with open(file_path, encoding='utf-8') as f:
            old_data = json.load(f)

        # Migrate to new schema
        new_data = migrate_coffee_bean(old_data)

        # Validate migrated data if requested
        if validate and not validate_migrated_data(new_data, file_path):
            return False

        if dry_run:
            logger.info(f"✓ Migration validation passed for {file_path}")
            return True

        # Create backup
        backup_path = file_path.with_suffix('.json.backup')
        if not backup_path.exists():
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(old_data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Created backup: {backup_path}")

        # Write the new data
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Migrated {file_path}")
        return True

    except Exception as e:
        logger.error(f"✗ Failed to migrate {file_path}: {e}")
        return False


def find_json_files(data_dir: Path) -> list[Path]:
    """Find all JSON files in the data directory structure using glob.

    Args:
        data_dir: Path to the data directory

    Returns:
        List of paths to JSON files
    """
    if not data_dir.exists():
        logger.error(f"Data directory does not exist: {data_dir}")
        return []

    # Use glob to find all JSON files in roasters subdirectories, excluding backups
    pattern = str(data_dir / "roasters" / "*" / "*" / "*.json")
    json_files = [
        Path(file_path) for file_path in glob(pattern)
        if not file_path.endswith('.backup')
    ]

    logger.info(f"Found {len(json_files)} JSON files to migrate")
    return json_files


def validate_migrated_data(data: dict[str, Any], file_path: Path) -> bool:
    """Validate migrated data using the CoffeeBean Pydantic schema.

    Args:
        data: Migrated coffee bean data
        file_path: Path to the file for error reporting

    Returns:
        True if validation passes, False otherwise
    """
    try:
        # Attempt to create a CoffeeBean instance to validate the data
        coffee_bean = CoffeeBean(**data)
        logger.debug(f"✓ Validation passed for {file_path}: {coffee_bean.name}")
        return True
    except Exception as e:
        logger.error(f"✗ Validation failed for {file_path}: {e}")
        return False


def main():
    """Main migration function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate coffee bean JSON data from old schema to new schema"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Path to data directory (default: data)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate migration without making changes"
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip Pydantic schema validation"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Find all JSON files using glob
    json_files = find_json_files(args.data_dir)

    if not json_files:
        logger.warning("No JSON files found to migrate")
        return 0

    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be modified")

    # Migrate files
    successful = 0
    failed = 0
    validation_enabled = not args.no_validate

    for file_path in json_files:
        if migrate_file(file_path, dry_run=args.dry_run, validate=validation_enabled):
            successful += 1
        else:
            failed += 1

    # Summary
    logger.info("\nMigration complete:")
    logger.info(f"  ✓ Successful: {successful}")
    logger.info(f"  ✗ Failed: {failed}")

    if validation_enabled:
        logger.info("  📋 All migrated data validated with Pydantic schema")

    if failed > 0:
        logger.error(f"Migration completed with {failed} failures")
        return 1

    if not args.dry_run:
        logger.info("All files migrated successfully!")
        logger.info("Backup files created with .backup extension")
    else:
        logger.info("Dry run completed - all files would migrate successfully")

    return 0


if __name__ == "__main__":
    sys.exit(main())
