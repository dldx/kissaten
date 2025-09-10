#!/usr/bin/env python3
"""Migration tool to convert elevation field from single value to min/max range.

This script migrates data from elevation to elevation_min/elevation_max:
- Converts single 'elevation' field to 'elevation_min' and 'elevation_max'
- Sets both min and max to the same value (original elevation)
- Preserves all other existing data
"""

import json
import logging
import sys
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


def migrate_elevation_in_bean(bean: dict[str, Any]) -> bool:
    """Migrate elevation field in a single bean object.

    Args:
        bean: Bean data dictionary

    Returns:
        True if migration was needed and performed, False if no changes
    """
    if 'elevation' in bean and 'elevation_min' not in bean and 'elevation_max' not in bean:
        elevation = bean.get('elevation', 0)

        # Set both min and max to the original elevation value
        bean['elevation_min'] = elevation if elevation and elevation > 0 else 0
        bean['elevation_max'] = elevation if elevation and elevation > 0 else 0

        # Remove the old elevation field
        del bean['elevation']

        logger.debug(f"Converted elevation {elevation} to min/max: {bean['elevation_min']}-{bean['elevation_max']}")
        return True

    return False


def migrate_coffee_bean_elevation(data: dict[str, Any]) -> bool:
    """Migrate elevation fields in coffee bean data.

    Args:
        data: Coffee bean data dictionary

    Returns:
        True if any changes were made, False otherwise
    """
    changed = False

    # Handle origins list
    origins = data.get('origins', [])
    if isinstance(origins, list):
        for bean in origins:
            if isinstance(bean, dict) and migrate_elevation_in_bean(bean):
                changed = True

    # Handle legacy single origin field (just in case)
    origin = data.get('origin')
    if isinstance(origin, dict) and migrate_elevation_in_bean(origin):
        changed = True

    return changed


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


def migrate_file(file_path: Path, dry_run: bool = False, validate: bool = True) -> bool:
    """Migrate elevation fields in a single JSON file.

    Args:
        file_path: Path to the JSON file to migrate
        dry_run: If True, only validate migration without writing files

    Returns:
        True if migration was successful, False otherwise
    """
    try:
        # Read the data
        with open(file_path, encoding='utf-8') as f:
            data = json.load(f)

        # Migrate elevation fields
        changed = migrate_coffee_bean_elevation(data)

        # Validate migrated data if requested
        if validate and not validate_migrated_data(data, file_path):
            return False

        if not changed:
            logger.debug(f"No elevation migration needed for {file_path}")
            return True

        if dry_run:
            logger.info(f"✓ Elevation migration needed for {file_path}")
            return True

        # Create backup
        backup_path = file_path.with_suffix('.json.elevation_backup')
        if not backup_path.exists():
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Created backup: {backup_path}")

        # Write the migrated data
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Migrated elevation fields in {file_path}")
        return True

    except Exception as e:
        logger.error(f"✗ Failed to migrate {file_path}: {e}")
        return False


def find_json_files(data_dir: Path) -> list[Path]:
    """Find all JSON files in the data directory structure.

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
        if not any(backup_ext in file_path for backup_ext in ['.backup', '.elevation_backup'])
    ]

    logger.info(f"Found {len(json_files)} JSON files to check for elevation migration")
    return json_files


def main():
    """Main elevation migration function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate elevation fields from single value to min/max range"
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
        help="Check which files need migration without making changes"
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

    # Find all JSON files
    json_files = find_json_files(args.data_dir)

    if not json_files:
        logger.warning("No JSON files found")
        return 0

    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be modified")

    # Migrate files
    successful = 0
    failed = 0
    needs_migration = 0
    validation_enabled = not args.no_validate

    for file_path in json_files:
        if migrate_file(file_path, dry_run=args.dry_run, validate=validation_enabled):
            successful += 1
            # Count files that actually need migration
            if args.dry_run:
                try:
                    with open(file_path, encoding='utf-8') as f:
                        data = json.load(f)
                    if migrate_coffee_bean_elevation(data):
                        needs_migration += 1
                except Exception:
                    pass
        else:
            error_failed = file_path
            failed += 1

    # Summary
    logger.info("\nElevation migration complete:")
    logger.info(f"  ✓ Processed successfully: {successful}")
    logger.info(f"  ✗ Failed: {failed}")
    logger.error(error_failed)

    if validation_enabled:
        logger.info("  📋 All migrated data validated with CoffeeBean schema")

    if args.dry_run:
        logger.info(f"  📋 Files needing elevation migration: {needs_migration}")
        if needs_migration > 0:
            logger.info("Run without --dry-run to perform the migration")
        else:
            logger.info("All files already have elevation_min/elevation_max fields")
    else:
        logger.info("Backup files created with .elevation_backup extension")

    if failed > 0:
        logger.error(f"Migration completed with {failed} failures")
        return 1

    if not args.dry_run and successful > 0:
        logger.info("Elevation migration completed successfully!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
