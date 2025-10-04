#!/usr/bin/env python3
"""
Script to capture high-resolution screenshots of flavour painting pages using Firefox and gnome-screenshot.

This script reads the wikidata_flavour_images.json file and captures screenshots
of the flavour painting pages by:
1. Opening each page in Firefox kiosk mode
2. Taking a screenshot with gnome-screenshot
3. Filtering out tasting notes without valid wikidata entities

Images are saved to data/flavours/ with filenames based on the flavour note.

Curation mode:
- Calculate hashes of all downloaded images and map to Wikidata entity IDs
- Pause for manual file deletion/renaming
- Re-scan and update the JSON file based on changes
"""

import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

import typer

# Configuration
BASE_URL = "http://localhost:5173"
FLAVOUR_IMAGES_JSON = "src/kissaten/database/wikidata_flavour_images.json"
OUTPUT_DIR = Path("data/flavours/paintings")
SLEEP_DURATION = 6  # seconds to wait for page load


def sanitize_filename(filename: str) -> str:
    """Sanitize a string to be safe for use as a filename."""
    # Replace problematic characters with underscores
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)
    # Remove multiple consecutive underscores and trailing/leading underscores
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    # Limit length to 200 characters to stay well under filesystem limits
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    return sanitized


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        print(f"⚠️  Failed to calculate hash for {file_path}: {e}")
        return ""


def get_filename_without_extension(filename: str) -> str:
    """Get filename without extension."""
    return Path(filename).stem


def find_flavour_by_filename(filename: str, flavours_data: dict) -> tuple[str, dict]:
    """
    Find a flavour entry by matching the filename (without extension) to the sanitized flavour note.

    Returns (flavour_note, flavour_data) or (None, None) if not found.
    """
    filename_stem = get_filename_without_extension(filename)

    for flavour_note, flavour_data in flavours_data.items():
        if flavour_data is None:
            continue
        sanitized_note = sanitize_filename(flavour_note)
        if sanitized_note == filename_stem:
            return flavour_note, flavour_data

    return None, None


def build_image_inventory(flavours_data: dict) -> tuple[dict, dict, dict]:
    """
    Build a complete inventory of current images.

    Returns three dictionaries:
    - filename_to_info: maps filename -> (hash, flavour_note, wikidata_id)
    - hash_to_filenames: maps hash -> list of filenames with that hash
    - flavour_to_filename: maps flavour_note -> filename
    """
    filename_to_info = {}
    hash_to_filenames = {}
    flavour_to_filename = {}

    if not OUTPUT_DIR.exists():
        print(f"❌ Output directory does not exist: {OUTPUT_DIR}")
        return filename_to_info, hash_to_filenames, flavour_to_filename

    for image_file in OUTPUT_DIR.glob("*.png"):
        if not image_file.is_file():
            continue

        # Calculate hash
        file_hash = calculate_file_hash(image_file)
        if not file_hash:
            continue

        # Find corresponding flavour data
        flavour_note, flavour_data = find_flavour_by_filename(image_file.name, flavours_data)

        if flavour_note and flavour_data:
            wikidata_id = flavour_data.get("id", "")
            filename_to_info[image_file.name] = (file_hash, flavour_note, wikidata_id)

            if file_hash not in hash_to_filenames:
                hash_to_filenames[file_hash] = []
            hash_to_filenames[file_hash].append(image_file.name)

            flavour_to_filename[flavour_note] = image_file.name

    return filename_to_info, hash_to_filenames, flavour_to_filename


def detect_curation_changes(flavours_data: dict, before_inventory: tuple, after_inventory: tuple) -> dict:
    """
    Detect changes between before and after inventories.

    Returns a dictionary with:
    - 'deleted': files that were deleted
    - 'renamed': files that were renamed (same hash, different filename, no longer exists with old name)
    - 'copied': files that were copied (same hash appears with multiple filenames)
    - 'new': completely new files (new hash that didn't exist before)
    """
    before_files, before_hashes, before_flavours = before_inventory
    after_files, after_hashes, after_flavours = after_inventory

    changes = {
        "deleted": [],      # list of (filename, flavour_note, wikidata_id)
        "renamed": [],      # list of (old_filename, new_filename, flavour_note, wikidata_id)
        "copied": [],       # list of (source_filename, target_filename, source_flavour, target_flavour)
        "new": [],          # list of (filename, flavour_note, wikidata_id)
    }

    # Track which files we've already processed
    processed_after_files = set()

    # Step 1: Detect deletions and renames
    for old_filename, (old_hash, old_flavour, old_wikidata_id) in before_files.items():
        if old_filename not in after_files:
            # File no longer exists with this name
            # Check if this hash still exists somewhere else (renamed)
            if old_hash in after_hashes:
                # The content still exists but with different filename(s)
                new_filenames = after_hashes[old_hash]

                # Find a filename that hasn't been processed yet as a rename target
                renamed_to = None
                for new_filename in new_filenames:
                    if new_filename not in before_files and new_filename not in processed_after_files:
                        renamed_to = new_filename
                        processed_after_files.add(new_filename)
                        break

                if renamed_to:
                    # This is a rename
                    new_flavour, new_data = find_flavour_by_filename(renamed_to, flavours_data)
                    if new_flavour and new_data:
                        new_wikidata_id = new_data.get("id", "")
                        changes["renamed"].append((old_filename, renamed_to, new_flavour, new_wikidata_id))
                        print(f"🔄 Detected rename: {old_filename} -> {renamed_to} ({old_flavour} -> {new_flavour})")
                else:
                    # Hash exists but all instances are accounted for, treat as deleted
                    changes["deleted"].append((old_filename, old_flavour, old_wikidata_id))
                    print(f"🗑️  Detected deletion: {old_filename} ({old_flavour})")
            else:
                # File and its content are completely gone
                changes["deleted"].append((old_filename, old_flavour, old_wikidata_id))
                print(f"🗑️  Detected deletion: {old_filename} ({old_flavour})")

    # Step 2: Detect copies and new files
    for new_filename, (new_hash, new_flavour, new_wikidata_id) in after_files.items():
        if new_filename in processed_after_files:
            # Already processed as a rename target
            continue

        if new_filename in before_files:
            # File existed before
            old_hash, old_flavour, old_wikidata_id = before_files[new_filename]
            if new_hash != old_hash:
                # Content changed - this is a replacement/copy from another file
                # Find the source of this content
                source_found = False
                for source_filename, (source_hash, source_flavour, source_wikidata_id) in before_files.items():
                    if source_hash == new_hash and source_filename != new_filename:
                        # Found the source
                        changes["copied"].append((source_filename, new_filename, source_flavour, new_flavour))
                        print(f"📋 Detected copy: {source_filename} -> {new_filename} ({source_flavour} -> {new_flavour})")
                        source_found = True
                        break

                if not source_found:
                    # Check if this is a copy from a file that still exists in after
                    for source_filename, (source_hash, source_flavour, source_wikidata_id) in after_files.items():
                        if source_hash == new_hash and source_filename != new_filename and source_filename in before_files:
                            # Found the source in current files
                            changes["copied"].append((source_filename, new_filename, source_flavour, new_flavour))
                            print(f"📋 Detected copy: {source_filename} -> {new_filename} ({source_flavour} -> {new_flavour})")
                            break
        else:
            # File didn't exist before
            if new_hash in before_hashes:
                # This hash existed before - it's a copy
                # Find the source file
                source_found = False
                for source_filename, (source_hash, source_flavour, source_wikidata_id) in before_files.items():
                    if source_hash == new_hash:
                        changes["copied"].append((source_filename, new_filename, source_flavour, new_flavour))
                        print(f"📋 Detected copy: {source_filename} -> {new_filename} ({source_flavour} -> {new_flavour})")
                        source_found = True
                        break

                if not source_found:
                    # Also check current files for the source
                    for source_filename, (source_hash, source_flavour, source_wikidata_id) in after_files.items():
                        if source_hash == new_hash and source_filename != new_filename and source_filename in before_files:
                            changes["copied"].append((source_filename, new_filename, source_flavour, new_flavour))
                            print(f"📋 Detected copy: {source_filename} -> {new_filename} ({source_flavour} -> {new_flavour})")
                            break
            else:
                # Completely new hash - this is a new file
                changes["new"].append((new_filename, new_flavour, new_wikidata_id))
                print(f"✨ Detected new file: {new_filename} ({new_flavour})")

    return changes


def update_flavour_data_with_changes(flavours_data: dict, changes: dict) -> dict:
    """
    Update the flavours data based on the detected changes.

    Returns the updated flavours data.
    """
    print("\n📝 Updating flavour data based on changes...")

    updated_data = flavours_data.copy()

    # Handle deletions - set to null
    for filename, flavour_note, wikidata_id in changes["deleted"]:
        if flavour_note in updated_data:
            # Delete the image and wikidata keys in the entry
            updated_data[flavour_note] = {
                "flavor_note": flavour_note,
                "source": None,
                "label": None,
                "description": None,
                "id": None,
                "image_url": None,
                "image_author": None,
                "image_license": None,
                "image_license_url": None,
            }
            print(f"   ✅ Marked {flavour_note} as rejected (deleted)")

    # Handle renames - update the flavour entry with potentially new data
    for old_filename, new_filename, new_flavour_note, new_wikidata_id in changes["renamed"]:
        # Find the old flavour note from the old filename
        old_flavour_note = None
        for flavour_note, data in flavours_data.items():
            if data and sanitize_filename(flavour_note) == get_filename_without_extension(old_filename):
                old_flavour_note = flavour_note
                break

        if old_flavour_note and old_flavour_note != new_flavour_note:
            # The file was renamed to match a different flavour
            # Copy the old data to the new flavour note
            if old_flavour_note in updated_data and updated_data[old_flavour_note]:
                old_data = updated_data[old_flavour_note].copy()
                old_data["flavor_note"] = new_flavour_note
                updated_data[new_flavour_note] = old_data
                # Mark the old flavour as null since its image was moved
                updated_data[old_flavour_note] = None
                print(f"   ✅ Moved data from {old_flavour_note} to {new_flavour_note}")
        else:
            print(f"   ℹ️  Rename within same flavour: {old_filename} -> {new_filename}")

    # Handle copies - update target flavour with source flavour's data
    for source_filename, target_filename, source_flavour, target_flavour in changes["copied"]:
        if source_flavour in flavours_data and flavours_data[source_flavour]:
            source_data = flavours_data[source_flavour].copy()
            source_data["flavor_note"] = target_flavour
            updated_data[target_flavour] = source_data
            print(f"   ✅ Copied data from {source_flavour} to {target_flavour}")

    # Handle new files - these would typically need manual data entry or another source
    for filename, flavour_note, wikidata_id in changes["new"]:
        print(f"   ℹ️  New file {filename} for {flavour_note} - keeping existing data if any")

    return updated_data


def save_updated_flavour_data(updated_data: dict, output_path: Path) -> bool:
    """Save the updated flavour data to the JSON file."""
    try:
        # Create backup
        backup_path = output_path.with_suffix(".json.backup")
        if output_path.exists():
            import shutil

            shutil.copy2(output_path, backup_path)
            print(f"💾 Created backup: {backup_path}")

        # Save updated data
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"results": updated_data}, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved updated flavour data to {output_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to save updated data: {e}")
        return False


def curation_mode():
    """Handle the manual curation mode."""
    print("🎨 Starting manual curation mode...")

    # Load the flavour data
    flavour_data_path = Path(FLAVOUR_IMAGES_JSON)
    if not flavour_data_path.exists():
        print(f"❌ Flavour data file not found: {flavour_data_path}")
        return

    print(f"📖 Loading flavour data from {flavour_data_path}")
    with open(flavour_data_path, encoding="utf-8") as f:
        data = json.load(f)

    flavours = data.get("results", {})

    # Step 1: Build inventory of all current images
    print("\n📊 Step 1: Building image inventory...")
    before_inventory = build_image_inventory(flavours)
    before_files, before_hashes, before_flavours = before_inventory

    if not before_files:
        print("❌ No images found to curate")
        return

    print(f"📈 Found {len(before_files)} images to curate")
    print(f"   Unique image contents (by hash): {len(before_hashes)}")

    # Step 2: Pause for manual curation
    print("\n⏸️  Step 2: Manual curation phase")
    print("=" * 60)
    print("You can now manually:")
    print("  • Delete image files you want to reject")
    print("  • Rename image files to match different flavour notes")
    print("  • Copy image files to use the same image for multiple flavours")
    print(f"\nImages are located in: {OUTPUT_DIR.absolute()}")
    print("=" * 60)
    input("\nPress Enter when you're done with manual curation...")

    # Step 3: Re-scan and detect changes
    print("\n🔍 Step 3: Re-scanning images...")
    after_inventory = build_image_inventory(flavours)
    after_files, after_hashes, after_flavours = after_inventory

    # Step 4: Detect what changed
    changes = detect_curation_changes(flavours, before_inventory, after_inventory)

    # Report changes
    print("\n📊 Change Summary:")
    print(f"  🗑️  Deleted files: {len(changes['deleted'])}")
    print(f"  🔄 Renamed files: {len(changes['renamed'])}")
    print(f"  📋 Copied files: {len(changes['copied'])}")
    print(f"  ✨ New files: {len(changes['new'])}")

    if changes["deleted"]:
        print("\n🗑️  Deleted files:")
        for filename, flavour_note, wikidata_id in changes["deleted"]:
            print(f"  • {filename} ({flavour_note})")

    if changes["renamed"]:
        print("\n🔄 Renamed files:")
        for old_filename, new_filename, new_flavour, new_wikidata_id in changes["renamed"]:
            print(f"  • {old_filename} -> {new_filename} ({new_flavour})")

    if changes["copied"]:
        print("\n📋 Copied files:")
        for source_filename, target_filename, source_flavour, target_flavour in changes["copied"]:
            print(f"  • {source_filename} -> {target_filename} ({source_flavour} -> {target_flavour})")

    if changes["new"]:
        print("\n✨ New files:")
        for filename, flavour_note, wikidata_id in changes["new"]:
            print(f"  • {filename} ({flavour_note})")

    # Step 5: Update the JSON file
    if any([changes["deleted"], changes["renamed"], changes["copied"], changes["new"]]):
        print("\n📝 Step 5: Updating flavour data...")
        updated_data = update_flavour_data_with_changes(flavours, changes)

        if save_updated_flavour_data(updated_data, flavour_data_path):
            print("✅ Curation completed successfully!")
        else:
            print("❌ Failed to save changes")
    else:
        print("\n✅ No changes detected - nothing to update")

    print("\n🎉 Curation mode completed!")
    print(f"   📁 Images directory: {OUTPUT_DIR.absolute()}")
    print(f"   📄 Updated data file: {flavour_data_path.absolute()}")


def close_firefox():
    """Close any existing Firefox instances."""
    try:
        subprocess.run(["pkill", "-f", "firefox"], check=False, capture_output=True)
        time.sleep(1)  # Give time for Firefox to close
    except Exception:
        pass  # Ignore if no Firefox processes to kill


def start_firefox_kiosk() -> subprocess.Popen:
    """
    Start Firefox in kiosk mode with an initial page.

    Returns the Firefox process.
    """
    # Close any existing Firefox instances first
    close_firefox()

    # Start Firefox in kiosk mode with a blank page
    firefox_process = subprocess.Popen(
        ["firefox", "--kiosk", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    # Give Firefox time to start
    time.sleep(3)
    return firefox_process


def open_new_tab(url: str) -> bool:
    """
    Open a new tab in the existing Firefox instance.

    Returns True if successful, False otherwise.
    """
    try:
        # Use firefox to open a new tab with the URL
        subprocess.run(["firefox", "--new-tab", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        return True
    except subprocess.TimeoutExpired:
        print("⚠️  Timeout opening new tab")
        return False
    except Exception as e:
        print(f"⚠️  Failed to open new tab: {e}")
        return False


def capture_screenshot_with_firefox(wikidata_id: str, flavour_note: str) -> bool:
    """
    Capture a screenshot of the current Firefox window with gnome-screenshot.

    Returns True if successful, False otherwise.
    """
    try:
        url = f"{BASE_URL}/flavour-image/{wikidata_id}"
        print(f"📷 Capturing screenshot for {flavour_note} ({wikidata_id})")

        # Open the URL in a new tab
        if not open_new_tab(url):
            print(f"❌ Failed to open tab for {flavour_note}")
            return False

        # Wait for page to load
        time.sleep(SLEEP_DURATION)

        # Sanitize filename
        sanitized_name = sanitize_filename(flavour_note)
        output_path = OUTPUT_DIR / f"{sanitized_name}.png"

        # Take screenshot with scrot
        screenshot_result = subprocess.run(["scrot", "-F", str(output_path)], capture_output=True, text=True)

        if screenshot_result.returncode == 0:
            print(f"✅ Saved screenshot: {output_path}")
            return True
        else:
            print(f"❌ Screenshot failed: {screenshot_result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Failed to capture screenshot for {flavour_note} ({wikidata_id}): {e}")
        return False


def check_frontend_server() -> bool:
    """
    Check if the frontend server is running and responsive.

    Returns True if the server is accessible, False otherwise.
    """
    try:
        import requests

        response = requests.get(f"{BASE_URL}/", timeout=10)
        if response.status_code == 200:
            print(f"✅ Frontend server is responding at {BASE_URL}")
            return True
        else:
            print(f"⚠️  Frontend server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to frontend server at {BASE_URL}: {e}")
        print("   Make sure the frontend is running with: cd frontend && npm run dev")
        return False


def capture_mode():
    """Handle the normal image capture mode."""
    print("🎨 Starting flavour image capture process...")

    # Load the flavour data
    flavour_data_path = Path(FLAVOUR_IMAGES_JSON)
    if not flavour_data_path.exists():
        print(f"❌ Flavour data file not found: {flavour_data_path}")
        return

    print(f"📖 Loading flavour data from {flavour_data_path}")
    with open(flavour_data_path, encoding="utf-8") as f:
        data = json.load(f)

    flavours = data.get("results", {})

    # Filter out flavours without wikidata entities and check for existing images
    valid_flavours = {}
    skipped_existing = 0

    for flavour_note, flavour_data in flavours.items():
        # Skip None values
        if flavour_data is None:
            print(f"⚠️  Skipping {flavour_note}: no data (None value)")
            continue

        wikidata_id = flavour_data.get("id")
        if not (wikidata_id and wikidata_id.startswith("Q")):  # Valid Wikidata ID format
            print(f"⚠️  Skipping {flavour_note}: no valid wikidata entity (ID: {wikidata_id})")
            continue

        # Check if image already exists
        sanitized_name = sanitize_filename(flavour_note)
        output_path = OUTPUT_DIR / f"{sanitized_name}.png"

        if output_path.exists():
            print(f"⏭️  Skipping {flavour_note}: image already exists")
            skipped_existing += 1
            continue

        valid_flavours[flavour_note] = flavour_data

    total_flavours = len(valid_flavours)
    total_in_data = len([f for f in flavours.values() if f is not None])

    if total_flavours == 0:
        if skipped_existing > 0:
            print(f"✅ All {skipped_existing} valid flavour images already exist - nothing to process")
        else:
            print("❌ No valid flavours with wikidata entities found")
        return

    print(f"🔍 Found {total_in_data} total flavours in data")
    if skipped_existing > 0:
        print(f"⏭️  Skipped {skipped_existing} flavours with existing images")
    print(f"📷 Will process {total_flavours} new flavours")

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Check if frontend server is running
    if not check_frontend_server():
        return

    # Start Firefox once at the beginning
    print("🚀 Starting Firefox in kiosk mode...")
    firefox_process = start_firefox_kiosk()

    try:
        # Process flavours one at a time
        successful_count = 0
        failed_count = 0

        for i, (flavour_note, flavour_data) in enumerate(valid_flavours.items(), 1):
            wikidata_id = flavour_data["id"]

            print(f"\n📷 Processing {i}/{total_flavours}: {flavour_note}")

            # Capture screenshot
            success = capture_screenshot_with_firefox(wikidata_id, flavour_note)

            if success:
                successful_count += 1
            else:
                failed_count += 1
                print(f"⚠️  Failed to process: {flavour_note}")

            # Small delay between captures to be respectful to the system
            if i < total_flavours:  # Don't sleep after the last one
                time.sleep(1)

            ## Every 10 captures, pause and use xdotool to close tabs
            if i % 10 == 0 and i < total_flavours:
                print("🛑 Pausing to close tabs...")
                time.sleep(2)
                try:
                    for _ in range(10):
                        # Close all tabs except the first one
                        subprocess.run(
                            ["xdotool", "key", "ctrl+w"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                        )
                        time.sleep(0.5)
                except Exception as e:
                    print(f"⚠️  Failed to close tabs with xdotool: {e}")
                print("▶️  Resuming...")

            # Every 50 captures, pause and check with user
            if i % 50 == 0 and i < total_flavours:
                print("\n⏸️  Pausing after 50 captures. Please check Firefox is still running correctly.")
                input("Press Enter to continue...")

    finally:
        # Ensure Firefox is closed at the end
        print("🔒 Closing Firefox...")
        try:
            firefox_process.terminate()
            firefox_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            firefox_process.kill()
        except Exception:
            # Fallback to pkill if process handling fails
            close_firefox()

    print("\n🎉 Image capture completed!")
    print(f"   ✅ Successful: {successful_count}")
    print(f"   ❌ Failed: {failed_count}")
    if skipped_existing > 0:
        print(f"   ⏭️  Skipped (already exist): {skipped_existing}")
    print(f"   📁 Images saved to: {OUTPUT_DIR.absolute()}")


app = typer.Typer(
    name="capture_flavour_images",
    help="Capture flavour images or curate existing ones",
    no_args_is_help=True,
)


@app.command("capture")
def capture_command():
    """Capture new flavour images using Firefox screenshots."""
    capture_mode()


@app.command("curate")
def curate_command():
    """Manually curate existing flavour images by deleting/renaming files."""
    curation_mode()


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit"),
):
    """Capture flavour images or curate existing ones.

    Examples:
        python capture_flavour_images.py capture    # Normal capture mode
        python capture_flavour_images.py curate    # Manual curation mode
    """
    if version:
        typer.echo("capture_flavour_images v1.0.0")
        raise typer.Exit()


if __name__ == "__main__":
    app()