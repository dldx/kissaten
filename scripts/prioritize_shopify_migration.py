#!/usr/bin/env python3
"""
Script to prioritize roaster scrapers for migration to Shopify products.json.
Identifies non-UK roasters currently using standard collection URLs and 
ranks them by the number of beans scraped in 2026.
"""

import os
import re

def get_bean_count(scraper_stem, data_dirs):
    """
    Finds the total number of JSON files scraped in 2026 for a given roaster stem.
    Includes fuzzy matching and manual overrides for directory names.
    """
    search_terms = {
        scraper_stem,
        scraper_stem.replace("_", " "),
        scraper_stem.replace("_", "-"),
        scraper_stem.replace("_", ""),
    }
    
    # Manual corrections for specific discrepancies between scraper filename and data directory
    special_mappings = {
        "mok": "mok_coffee",
        "vuivui": "vui_coffee",
        "gout_co": "goût_and_co",
        "greysoul_coffee": "grey_soul_coffee",
        "h_s_coffee_roasters": "h&s_coffee_roasters",
        "uncle_ben_coffee": "uncle_ben's_coffee",
        "taller_cafe": "taller_café",
        "mokcoffee": "mok_coffee",
        "phil_sebastian": "phil_&_sebastian_coffee_roasters",
        "acoustic_java": "acoustic_java"
    }
    
    if scraper_stem in special_mappings:
        search_terms.add(special_mappings[scraper_stem])

    count = 0
    matched_dirs = []
    
    for d in data_dirs:
        norm_d = d.lower()
        if any(term in norm_d for term in search_terms):
            matched_dirs.append(d)
    
    for d in matched_dirs:
        base_dir = os.path.join("data/roasters", d)
        for root, dirs, files in os.walk(base_dir):
            # Target specifically 2026 data
            if "2026" in root:
                for f in files:
                    if f.endswith(".json"):
                        count += 1
    return count

def main():
    scraper_dir = "src/kissaten/scrapers"
    data_root = "data/roasters"
    
    if not os.path.exists(data_root):
        print(f"Error: Data directory not found at {data_root}")
        return

    data_dirs = os.listdir(data_root)
    
    # Regex 1: Find roasters NOT in the United Kingdom or UK
    non_uk_pattern = re.compile(r'country\s*=\s*"(?!(United Kingdom|UK))([^"]+)"')
    
    # Regex 2: Find URLs containing /collections/ but NOT ending in products.json
    no_products_json_pattern = re.compile(r"/collections/(?!.*products\.json)")

    prioritized = []

    for filename in os.listdir(scraper_dir):
        # Skip base classes and utilities
        if filename.endswith(".py") and filename not in ["__init__.py", "base.py", "shopify_base.py", "registry.py", "template.py"]:
            path = os.path.join(scraper_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                    # Apply both filters
                    if non_uk_pattern.search(content) and no_products_json_pattern.search(content):
                        stem = filename[:-3]
                        count = get_bean_count(stem, data_dirs)
                        prioritized.append((stem, count))
            except Exception as e:
                print(f"Error reading {filename}: {e}")

    # Sort by 2026 bean volume descending
    prioritized.sort(key=lambda x: x[1], reverse=True)

    # Output results
    print(f"{'Roaster (Scraper)':<30} | {'2026 Beans':<10}")
    print("-" * 45)
    for roaster, count in prioritized:
        print(f"{roaster:<30} | {count:<10}")

if __name__ == "__main__":
    main()
