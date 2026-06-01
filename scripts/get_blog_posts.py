# /// script
# dependencies = ["feedparser", "httpx", "pydantic", "beautifulsoup4", "python-dotenv"]
# requires-python = ">=3.10"
# ///

import argparse
import asyncio
import json
import logging
import os
import re
import uuid
from pathlib import Path

import dotenv
import feedparser
import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

# Load environment variables
dotenv.load_dotenv()

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Compatible models with ingest_podcasts.py pipeline
class Chunk(BaseModel):
    text: str
    timestamp: list[float | None]

class TranscriptionResponse(BaseModel):
    """Mimics transcript format to ensure compatibility with PodcastTagger pipeline."""
    text: str
    chunks: list[Chunk]

class BlogMetadata(BaseModel):
    episode_title: str  # Use same key as podcast for compatibility
    url: str | None
    published_date: str | None

BLOGS_CONFIG = [
    {
        "name": "christopher-feran",
        "rss_url": "https://christopherferan.com/feed/",
    },
    {
        "name": "perfect-daily-grind",
        "rss_url": "https://perfectdailygrind.com/category/varieties/feed/",
    },
    {
        "name": "perfect-daily-grind",
        "rss_url": "https://perfectdailygrind.com/category/processing/feed/",
    },
    {
        "name": "perfect-daily-grind",
        "rss_url": "https://perfectdailygrind.com/category/origins/feed/",
    },
    {
        "name": "cafe-imports",
        "rss_url": "https://www.cafeimports.com/europe/blog/feed/",
    },
    {
        "name": "cafe-imports",
        "rss_url": "https://www.cafeimports.com/europe/blog/2023/feed/",
    },
    {
        "name": "cafe-imports",
        "rss_url": "https://www.cafeimports.com/europe/blog/2024/feed/",
    },
    {
        "name": "cafe-imports",
        "rss_url": "https://www.cafeimports.com/europe/blog/2025/feed/",
    },
]

def clean_html(html_content: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    # Remove script and style elements
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()

    text = soup.get_text(separator=" ", strip=True)
    # Normalize multiple spaces and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_slug(url: str, title: str) -> str:
    """Generate a filename-friendly slug from URL or title."""
    if url:
        # Extract the last part of the URL (ignoring trailing slash)
        slug = url.rstrip("/").split("/")[-1]
        if slug:
            return slug

    # Fallback to title-based slug
    slug = title.lower()
    slug = re.sub(r'[^a-z0-0]+', '-', slug).strip("-")
    return slug

async def main():
    parser = argparse.ArgumentParser(description="Download blog posts from RSS feeds")
    parser.add_argument("--blog", type=str, help="Process only a specific blog by name")
    args = parser.parse_args()

    async with httpx.AsyncClient(
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        },
        follow_redirects=True
    ) as client:
        for blog_cfg in BLOGS_CONFIG:
            if args.blog and blog_cfg["name"] != args.blog:
                continue

            blog_name = blog_cfg["name"]
            rss_url = blog_cfg["rss_url"]
            blog_dir = Path("blog_data") / blog_name
            blog_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"--- Processing blog: {blog_name} ---")

            try:
                resp = await client.get(rss_url)
                resp.raise_for_status()
                feed = feedparser.parse(resp.text)
            except Exception as e:
                logger.error(f"Failed to fetch RSS for {blog_name}: {e}")
                continue

            for entry in feed.entries:
                try:
                    title = entry.get("title", "Untitled Post")
                    url = entry.get("link")
                    published = entry.get("published")
                    content_html = entry.get("description", "")

                    # Some feeds use content:encoded
                    if hasattr(entry, "content"):
                        content_html = entry.content[0].value
                    elif "content" in entry:
                        content_html = entry.content[0].value

                    clean_text = clean_html(content_html)
                    if not clean_text:
                        logger.warning(f"No content found for {title}")
                        continue

                    slug = get_slug(url, title)
                    json_path = blog_dir / f"{slug}.json"
                    meta_path = blog_dir / f"{slug}.metadata.json"

                    # Prepare metadata (Podcast compatible keys)
                    metadata = BlogMetadata(
                        episode_title=title,
                        url=url,
                        published_date=published
                    )

                    # Prepare blog content (TranscriptionResponse compatible)
                    blog_data = TranscriptionResponse(
                        text=clean_text,
                        chunks=[
                            Chunk(text=clean_text, timestamp=[0.0, 0.0])
                        ]
                    )

                    # Atomic write metadata
                    meta_path.write_text(metadata.model_dump_json(indent=2))

                    # Skip if JSON already exists
                    if json_path.exists():
                        logger.info(f"[skip] {json_path.name} already exists")
                        continue

                    # Atomic write content
                    tmp_path = json_path.with_suffix(".tmp")
                    tmp_path.write_text(blog_data.model_dump_json(indent=2))
                    tmp_path.rename(json_path)

                    logger.info(f"[saved] {json_path.name}")

                except Exception as e:
                    logger.error(f"Failed to process post '{entry.get('title')}': {e}")

if __name__ == "__main__":
    asyncio.run(main())
