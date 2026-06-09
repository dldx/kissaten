import json
import logging
import re
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def normalize_url(url):
    """Remove /collections/.../ segments from Shopify URLs."""
    if not url:
        return None
    # Replace /collections/anything/products/ with /products/
    return re.sub(r'/collections/[^/]+/', '/', url)

def get_handle_from_url(url):
    """Extract the product handle from a canonical URL."""
    if not url:
        return None
    return url.split('/')[-1].split('?')[0]

def process_file(file_path, handle_tracker, dry_run=False):
    """Process a single JSON or DIFFJSON file."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        original_url = data.get("url")
        if not original_url:
            return False

        canonical_url = normalize_url(original_url)
        handle = get_handle_from_url(canonical_url)

        if not handle:
            return False

        # Update the content with the canonical URL
        if original_url != canonical_url:
            if not dry_run:
                data["url"] = canonical_url
                with open(file_path, "w") as f:
                    json.dump(data, f, indent=2)
                logger.debug(f"Updated URL in {file_path.name}")
            else:
                logger.info(f"[Dry Run] Would update URL in {file_path.name}: {original_url} -> {canonical_url}")

        # Check for cross-collection duplicates within the same session
        ext = "".join(file_path.suffixes)  # .json or .diffjson
        tracker_key = (handle, ext)

        if tracker_key in handle_tracker:
            if not dry_run:
                logger.info(f"Deleting duplicate {ext}: {file_path.name} (already have {handle}{ext})")
                file_path.unlink()
                # Also try to delete associated images if this is a .json file
                if ext == ".json":
                    for img_ext in ['.png', '.jpg', '.webp', '.avif']:
                        img_file = file_path.with_suffix(img_ext)
                        if img_file.exists():
                            img_file.unlink()
            else:
                logger.info(f"[Dry Run] Would delete duplicate {file_path.name}")
            return True

        # Track that we've seen this handle in this session
        handle_tracker[tracker_key] = file_path
        return True

    except Exception as e:
        logger.error(f"Error processing {file_path.name}: {e}")
        return False

def migrate_standout_data(dry_run=False):
    base_dir = Path("data/roasters/standout_coffee_ab")
    if not base_dir.exists():
        logger.error(f"Directory {base_dir} not found.")
        return

    if dry_run:
        logger.info("--- DRY RUN MODE ---")

    # 1. Group files by timestamped session
    sessions = sorted([d for d in base_dir.iterdir() if d.is_dir() and d.name.isdigit()], reverse=True)

    logger.info(f"Processing {len(sessions)} sessions...")

    for session_dir in sessions:
        logger.info(f"Cleaning session: {session_dir.name}")

        # handle_tracker: (handle, ext) -> Path
        handle_tracker = {}

        # Process ALL .json and .diffjson files
        files_to_process = sorted(list(session_dir.glob("*.json")) + list(session_dir.glob("*.diffjson")))

        for f in files_to_process:
            if f.name in ["logo.json"]:
                continue
            process_file(f, handle_tracker, dry_run=dry_run)

    logger.info("Cleanup complete.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without changing files")
    args = parser.parse_args()

    migrate_standout_data(dry_run=args.dry_run)
