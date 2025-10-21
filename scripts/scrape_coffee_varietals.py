"""
Script to scrape coffee varietal information from World Coffee Research.

Extracts name, description, and links for Arabica and Robusta varietals
from https://varieties.worldcoffeeresearch.org/

This script uses Pydantic for data validation to ensure:
- Names are non-empty and within reasonable length
- Links are valid URLs pointing to World Coffee Research varietal pages
- Species are correctly specified as either 'arabica' or 'robusta'
- Descriptions are properly cleaned and normalized

Usage:
    uv run python scripts/scrape_coffee_varietals.py

Output:
    Saves validated data to src/kissaten/database/coffee_varietals.json
"""

import asyncio
import json
from pathlib import Path
from typing import Literal

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from pydantic import BaseModel, Field, HttpUrl, field_validator


class CoffeeVarietal(BaseModel):
    """Pydantic model for coffee varietal data."""

    name: str = Field(..., min_length=1, max_length=100, description="Name of the coffee varietal")
    description: str = Field(default="", description="Brief description of the varietal")
    link: HttpUrl = Field(..., description="URL to the varietal's detail page")
    species: Literal["arabica", "robusta"] = Field(..., description="Coffee species")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and clean the varietal name."""
        # Strip whitespace and normalize
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v

    @field_validator("link")
    @classmethod
    def validate_link(cls, v: HttpUrl) -> HttpUrl:
        """Validate that the link points to a varietal page."""
        url_str = str(v)
        if "/varieties/" not in url_str or "worldcoffeeresearch.org" not in url_str:
            raise ValueError("Link must point to a World Coffee Research varietal page")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Clean the description."""
        # Strip whitespace and normalize
        return v.strip()


class VarietalCollection(BaseModel):
    """Collection of coffee varietals with metadata."""

    varietals: list[CoffeeVarietal] = Field(default_factory=list, description="List of coffee varietals")
    total_count: int = Field(default=0, description="Total number of varietals")
    arabica_count: int = Field(default=0, description="Number of Arabica varietals")
    robusta_count: int = Field(default=0, description="Number of Robusta varietals")

    @classmethod
    def from_varietals(cls, varietals: list[CoffeeVarietal]) -> "VarietalCollection":
        """Create a collection from a list of varietals."""
        arabica_count = sum(1 for v in varietals if v.species == "arabica")
        robusta_count = sum(1 for v in varietals if v.species == "robusta")
        return cls(
            varietals=varietals,
            total_count=len(varietals),
            arabica_count=arabica_count,
            robusta_count=robusta_count,
        )


async def scrape_varietals_page(url: str, species: str) -> list[CoffeeVarietal]:
    """
    Scrape coffee varietal information from a given URL.

    Args:
        url: The URL to scrape
        species: The coffee species (arabica or robusta)

    Returns:
        List of dictionaries containing varietal information
    """
    print(f"Scraping {species} varietals from {url}...")

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Navigate to the page
            await page.goto(url, wait_until="networkidle", timeout=30000)

            # Wait for content to load - adjust selector based on page structure
            await page.wait_for_selector("body", timeout=10000)

            # Get page content
            content = await page.content()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")

            varietals = []

            # Find all varietal cards/entries
            # Look for divs that contain varietal information
            # The parent div has class containing "theme-arabica" or "theme-robusta" and "flex flex-col"
            varietal_containers = soup.find_all("div", id=lambda x: x and x.startswith("variety-card-"))

            print(f"Found {len(varietal_containers)} potential varietal containers")

            # If we found structured containers, parse them
            if varietal_containers:
                for container in varietal_containers:
                    try:
                        # Find the link to the varietal page
                        link_elem = container.find("a", href=lambda x: x and "/varieties/" in x)
                        if not link_elem:
                            continue

                        # Extract link
                        link = link_elem.get("href")
                        if not link.startswith("http"):
                            link = f"https://varieties.worldcoffeeresearch.org/{link.lstrip('/')}"

                        # Skip if not a varietal page
                        if "/varieties/" not in link or "worldcoffeeresearch.org/varieties/" not in link:
                            continue

                        # Extract name from h3
                        name_elem = container.find("h3")
                        if name_elem:
                            name = name_elem.get_text(strip=True)
                        else:
                            # Fallback to link text
                            name = link_elem.get_text(strip=True).split("\n")[0]

                        if not name or len(name) > 100:
                            continue

                        # Extract description from paragraph
                        description = ""
                        desc_elem = container.find("p", class_=lambda x: x and "text-base" in x)
                        if desc_elem:
                            description = desc_elem.get_text(strip=True)

                        # Create and validate varietal using Pydantic model
                        try:
                            varietal = CoffeeVarietal(
                                name=name,
                                description=description,
                                link=link,
                                species=species,
                            )
                            varietals.append(varietal)
                            print(f"  - {varietal.name}: {varietal.link}")
                        except Exception as validation_error:
                            print(f"Validation error for {name}: {validation_error}")
                            continue

                    except Exception as e:
                        print(f"Error processing container: {e}")
                        continue

            # Fallback: if we didn't find structured containers, try finding links
            else:
                print("Using fallback link extraction method")
                varietal_elements = soup.find_all("a", href=True)

                for element in varietal_elements:
                    try:
                        # Extract name
                        name = None
                        if element.name == "a":
                            name = element.get_text(strip=True)

                        if not name or len(name) > 100:  # Skip if no name or too long
                            continue

                        # Extract link
                        link = None
                        if element.name == "a" and element.get("href"):
                            link = element["href"]

                        # Make link absolute if it's relative
                        if link and not link.startswith("http"):
                            base_url = "https://varieties.worldcoffeeresearch.org"
                            link = f"{base_url}/{link.lstrip('/')}"

                        # Only add if we have at least a name and link, and the link points to a varietal page
                        if (
                            name
                            and link
                            and link != url
                            and "/varieties/" in link
                            and "worldcoffeeresearch.org/varieties/" in link
                        ):
                            # Create and validate varietal using Pydantic model
                            try:
                                varietal = CoffeeVarietal(
                                    name=name,
                                    description="",
                                    link=link,
                                    species=species,
                                )
                                varietals.append(varietal)
                                print(f"  - {varietal.name}: {varietal.link}")
                            except Exception as validation_error:
                                print(f"Validation error for {name}: {validation_error}")
                                continue

                    except Exception as e:
                        print(f"Error processing element: {e}")
                        continue

            print(f"Extracted {len(varietals)} {species} varietals")

        except Exception as e:
            print(f"Error scraping {url}: {e}")

        finally:
            await browser.close()

    return varietals


async def main():
    """Main function to scrape both Arabica and Robusta varietals."""

    urls = {
        "arabica": "https://varieties.worldcoffeeresearch.org/arabica/varieties",
        "robusta": "https://varieties.worldcoffeeresearch.org/robusta/varieties",
    }

    all_varietals: list[CoffeeVarietal] = []

    # Scrape each species
    for species, url in urls.items():
        varietals = await scrape_varietals_page(url, species)
        all_varietals.extend(varietals)

    # Create validated collection
    collection = VarietalCollection.from_varietals(all_varietals)

    # Save to JSON file
    output_dir = Path(__file__).parent.parent / "src" / "kissaten" / "database"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "coffee_varietals.json"

    # Export as JSON with Pydantic's model_dump
    varietals_data = [v.model_dump(mode="json") for v in collection.varietals]

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(varietals_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Successfully saved {collection.total_count} varietals to {output_file}")

    # Print summary
    print("\nSummary:")
    print(f"  - Arabica varietals: {collection.arabica_count}")
    print(f"  - Robusta varietals: {collection.robusta_count}")
    print(f"  - Total: {collection.total_count}")


if __name__ == "__main__":
    asyncio.run(main())
