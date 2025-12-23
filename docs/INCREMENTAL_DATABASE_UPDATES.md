# Incremental Database Updates

This document explains the incremental database update feature that allows for efficient database refreshes by only processing files that have changed.

## Overview

The Kissaten database refresh functionality now supports two modes:

1. **Full Refresh** (default): Drops all tables and reloads everything from scratch
2. **Incremental Update** (new): Only processes files that have been added or modified since the last update

## How It Works

### Checksum-Based Tracking

The incremental update feature uses SHA256 checksums to track which files have been processed:

1. A new `processed_files` table stores:
   - `file_path`: Relative path from data directory
   - `checksum`: SHA256 hash of file contents
   - `file_type`: Either "json" or "diffjson"
   - `processed_at`: Timestamp when file was processed

2. Before processing a file, the system:
   - Calculates its current checksum
   - Checks if a matching entry exists in `processed_files`
   - Skips the file if checksum matches (unchanged)
   - Processes the file if it's new or has changed

3. After successfully processing a file:
   - The file is marked as processed in the `processed_files` table
   - Future runs will skip it unless its content changes

### Database Schema

The new `processed_files` table is created automatically:

```sql
CREATE TABLE IF NOT EXISTS processed_files (
    file_path VARCHAR PRIMARY KEY,
    checksum VARCHAR NOT NULL,
    file_type VARCHAR NOT NULL,
    processed_at TIMESTAMP NOT NULL
)
```

## Usage

### Command Line Interface

Use the `--incremental` (or `-i`) flag with the refresh command:

```bash
# Full refresh (default) - drops and recreates everything
kissaten refresh

# Incremental update - only process new/changed files
kissaten refresh --incremental

# Incremental with verbose output
kissaten refresh --incremental --verbose

# Short form
kissaten refresh -i -v
```

### When to Use Each Mode

**Use Full Refresh when:**
- Setting up the database for the first time
- Schema changes have been made to database tables
- You want to ensure complete consistency
- Database corruption is suspected
- You need to reprocess all historical data

**Use Incremental Update when:**
- Running regular updates after scraping new beans
- Only a few roasters have been scraped recently
- You want faster database updates
- The database schema hasn't changed
- You're doing frequent small updates

## Performance Benefits

Incremental updates provide significant performance improvements:

- **Speed**: Only processes changed files, not the entire dataset
- **Resource Usage**: Lower CPU and I/O usage
- **Scalability**: Performance doesn't degrade as dataset grows
- **Efficiency**: Ideal for automated/scheduled updates

### Example Performance

For a dataset with 10,000 beans across 50 roasters:

- **Full Refresh**: ~30-60 seconds to process all files
- **Incremental Update** (after scraping 1 roaster): ~2-5 seconds

## Implementation Details

### Modified Functions

1. **`init_database(incremental: bool = False)`**
   - If `incremental=False`: Drops all tables (original behavior)
   - If `incremental=True`: Preserves existing tables and data

2. **`load_coffee_data(data_dir: Path, incremental: bool = False)`**
   - Filters JSON files based on `processed_files` table
   - Only processes untracked or changed files
   - Marks processed files after successful loading

3. **`apply_diffjson_updates(data_dir: Path, incremental: bool = False)`**
   - Filters diffjson files similarly
   - Skips already-processed update files
   - Marks processed after successful application

### Helper Functions

New utility functions support the incremental feature:

```python
def calculate_file_checksum(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""

def is_file_processed(file_path: Path, data_dir: Path) -> bool:
    """Check if a file has already been processed based on its checksum."""

def mark_file_processed(file_path: Path, data_dir: Path, file_type: str):
    """Mark a file as processed by storing its checksum."""
```

## Programmatic Usage

You can also use the incremental feature in Python code:

```python
from pathlib import Path
from kissaten.api.db import init_database, load_coffee_data, load_tasting_notes_categories
from kissaten.api.fx import update_currency_rates
from kissaten.api.db import conn

async def refresh_database(incremental: bool = False):
    """Refresh database with optional incremental mode."""
    await init_database(incremental=incremental)
    await update_currency_rates(conn)
    await load_coffee_data(
        data_dir=Path("data/roasters"),
        incremental=incremental
    )
    await load_tasting_notes_categories()

# Full refresh
await refresh_database(incremental=False)

# Incremental update
await refresh_database(incremental=True)
```

## Troubleshooting

### Files Not Being Processed

If files that should be processed are being skipped:

1. Check if the file content has actually changed
2. Verify the file path is correct
3. Clear the `processed_files` table for a fresh start:
   ```sql
   DELETE FROM processed_files;
   ```

### Forcing Full Refresh

If you need to force reprocessing of all files:

```bash
# Use full refresh mode (default)
kissaten refresh

# Or manually clear processed files table first
# Then run incremental update
```

### Checksum Mismatches

The system uses SHA256 checksums. If you:
- Manually edit files
- Change file timestamps without content changes
- Restore files from backup

The checksums will be recalculated and files will be reprocessed if content differs.

## Best Practices

1. **Regular Incremental Updates**: Use incremental mode for daily/frequent updates
2. **Periodic Full Refresh**: Run full refresh weekly/monthly to ensure consistency
3. **After Schema Changes**: Always use full refresh after modifying database schema
4. **Monitor Processed Files**: Keep an eye on `processed_files` table growth
5. **Backup Database**: Backup before major updates, especially full refreshes

## Migration from Previous Version

If you're upgrading from a version without incremental updates:

1. The `processed_files` table will be created automatically on first run
2. First incremental update will process all files (since none are tracked)
3. Subsequent incremental updates will skip already-processed files
4. No manual migration steps required

## Future Improvements

Potential enhancements for the incremental update feature:

- [ ] Garbage collection for processed_files (remove entries for deleted files)
- [ ] Statistics on processed vs. skipped files
- [ ] Parallel processing of unprocessed files
- [ ] Differential updates for changed beans (update-in-place)
- [ ] Configurable checksum algorithms
- [ ] Web UI for monitoring processed files

## Related Documentation

- [QUICKSTART.md](../QUICKSTART.md) - Getting started guide
- [AGENTS.md](../AGENTS.md) - Project architecture and development guidelines
- [ADDING_SCRAPERS.md](../ADDING_SCRAPERS.md) - How to add new scrapers
