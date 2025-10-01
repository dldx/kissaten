#!/usr/bin/env python3
"""
Script to capture high-resolution screenshots of flavour painting pages using Firefox and gnome-screenshot.

This script reads the wikidata_flavour_images.json file and captures screenshots
of the flavour painting pages by:
1. Opening each page in Firefox kiosk mode
2. Taking a screenshot with gnome-screenshot
3. Filtering out tasting notes without valid wikidata entities

Images are saved to data/flavours/ with filenames based on the flavour note.
"""

import json
import re
import subprocess
import time
from pathlib import Path

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


def main():
    """Main function to orchestrate the image capturing process."""

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


if __name__ == "__main__":
    main()
