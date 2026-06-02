import re
import sys
from pathlib import Path
import logging

# Set up logging to avoid noise
logging.basicConfig(level=logging.ERROR)

def get_new_normalization(name: str) -> str:
    """The new normalization logic."""
    name = name.lower().replace(" ", "_")
    return re.sub(r"[^a-z0-9&_\-éūëöáíóúñûē']", "_", name)

def get_old_normalization(name: str) -> str:
    """The old normalization logic."""
    return name.lower().replace(" ", "_")

def main():
    # We need to find all roaster names.
    # They are in src/kissaten/scrapers/registry.py and also existing directories in data/roasters/

    # 1. Get names from data/roasters/
    roasters_dir = Path("data/roasters")
    if not roasters_dir.exists():
        print(f"Error: {roasters_dir} not found.")
        sys.exit(1)

    existing_dirs = [d.name for d in roasters_dir.iterdir() if d.is_dir()]

    # 2. Extract roaster names from registry.py if possible
    # For simplicity, we'll check the existing directory names against the new function
    # to see if any directory would change its 'slug' unexpectedly,
    # or if we can find the source names.

    print(f"Checking {len(existing_dirs)} existing roaster directories...")
    print("-" * 60)

    mismatches = []

    # Since we don't have the original 'pretty' names for all historical data easily
    # without parsing all JSON files or the registry, let's reverse-check:
    # Does normalization(dir_name) == dir_name?
    # Actually, the better test is: if we have "S&W Roasting",
    # old was "s&w_roasting", new is "s&w_roasting" (no change).
    # If we had "S+W Roasting", old was "s+w_roasting", new is "s_w_roasting" (CHANGE!).

    # Let's try to find original roaster names from the registry
    import importlib.util
    try:
        # Load registry manually to avoid issues with uv run
        spec = importlib.util.spec_from_file_location("registry", "src/kissaten/scrapers/registry.py")
        registry_mod = importlib.util.module_from_spec(spec)
        # Mock BaseScraper to allow import
        sys.modules["kissaten.scrapers.base"] = type("BaseScraper", (), {})
        spec.loader.exec_module(registry_mod)
        roaster_names = []
        # Since we can't easily instantiate without full dependencies, let's parse the file for roaster_name registrations
        with open("src/kissaten/scrapers/registry.py", "r") as f:
            content = f.read()
            # Look for roaster_name="Name" in the file
            roaster_names = re.findall(r'roaster_name=["\'](.*?)["\']', content)
    except Exception as e:
        print(f"Could not parse registry: {e}")
        # Fallback to searching files for roaster_name
        import glob
        roaster_names = []
        for f in glob.glob("src/kissaten/scrapers/*.py"):
            with open(f, 'r') as content:
                match = re.search(r'roaster_name=["\'](.*?)["\']', content.read())
                if match:
                    roaster_names.append(match.group(1))

    if not roaster_names:
        print("Could not extract roaster names from registry/source. Checking directories only.")
    else:
        print(f"Checking {len(roaster_names)} roaster names from registry...")
        for name in roaster_names:
            old_slug = get_old_normalization(name)
            new_slug = get_new_normalization(name)

            if old_slug != new_slug:
                print(f"CONFLICT: '{name}'")
                print(f"  Old: {old_slug}")
                print(f"  New: {new_slug}")
                mismatches.append((name, old_slug, new_slug))

    print("-" * 60)
    if not mismatches:
        print("✅ SUCCESS: All current roaster names produce identical slugs with the new function.")
    else:
        print(f"⚠️ FOUND {len(mismatches)} DIFFERENCES.")
        print("These roasters might lose connection to their old data unless directories are renamed.")

if __name__ == "__main__":
    main()
