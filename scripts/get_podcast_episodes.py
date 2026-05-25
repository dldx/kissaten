# /// script
# dependencies = ["feedparser", "httpx", "tenacity", "requests", "pydantic", "python-dotenv"]
# requires-python = ">=3.10"
# ///

import asyncio
import math
import os
import subprocess
import sys
import uuid
import base64
import json
import argparse
from pathlib import Path

import dotenv
import feedparser
import httpx
import requests
from pydantic import BaseModel, Field, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

# Load environment variables
dotenv.load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
TRANSCRIPTION_ENDPOINT = os.getenv("HF_TRANSCRIPTION_ENDPOINT")
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}


# Pydantic models for transcription
class Chunk(BaseModel):
    text: str
    timestamp: list[float | None]


class TranscriptionResponse(BaseModel):
    text: str
    chunks: list[Chunk]


@retry(
    retry=(retry_if_exception_type(httpx.HTTPError)),
    stop=stop_after_attempt(10),
    wait=wait_fixed(60),
)
async def download_file(*, url, path, client=None):
    """Atomically download a file."""
    path = Path(path)
    if path.exists():
        return path

    path.parent.mkdir(parents=True, exist_ok=True)

    _owns_client = client is None
    if _owns_client:
        client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            }
        )

    try:
        async with client.stream("GET", url, follow_redirects=True) as resp:
            resp.raise_for_status()
            tmp_path = path.parent / f"{path.name}.{uuid.uuid4()}.tmp"
            with open(tmp_path, "wb") as out_file:
                async for chunk in resp.aiter_raw():
                    out_file.write(chunk)
    except Exception as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        raise
    finally:
        if _owns_client:
            await client.aclose()

    os.rename(tmp_path, path)
    return path


def split_episode(episode_filepath):
    """Split episode into chunks using ffmpeg."""
    max_segment_duration_ms = 1700 * 1000  # 1700 seconds in ms
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(episode_filepath),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    total_ms = float(result.stdout.strip()) * 1000
    num_segments = math.ceil(total_ms / max_segment_duration_ms)

    chunk_paths = []
    for i in range(num_segments):
        start_ms = i * max_segment_duration_ms
        chunk_path = Path(f"temp_chunk_{i}.mp3")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                str(start_ms / 1000),
                "-i",
                str(episode_filepath),
                "-t",
                str(max_segment_duration_ms / 1000),
                "-c",
                "copy",
                str(chunk_path),
            ],
            check=True,
            capture_output=True,
        )
        chunk_paths.append(chunk_path)
    return chunk_paths


async def transcribe_audio(audio_file_path):
    """Transcribe audio using direct async requests with Base64 encoding."""
    file_size = os.path.getsize(audio_file_path)
    chunk_size_limit = 25 * 1024 * 1024  # 25MB
    max_segment_duration_s = 1700

    def send_request(audio_bytes):
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        payload = {
            "inputs": audio_base64,
            "parameters": {"return_timestamps": True},
        }

        @retry(
            retry=retry_if_exception_type((requests.exceptions.RequestException, Exception)),
            stop=stop_after_attempt(5),
            wait=wait_fixed(10),
        )
        def _get_response():
            response = requests.post(
                TRANSCRIPTION_ENDPOINT,
                headers=HEADERS,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

        try:
            data = _get_response()
            return TranscriptionResponse.model_validate(data)
        except ValidationError:
            # Fallback to model_construct if validation fails
            data = _get_response()
            return TranscriptionResponse.model_construct(**data)

    if file_size > chunk_size_limit:
        chunk_paths = split_episode(audio_file_path)
        all_chunks = []
        combined_text = []

        for i, path in enumerate(chunk_paths):
            offset = i * max_segment_duration_s
            with open(path, "rb") as f:
                result = send_request(f.read())
            combined_text.append(result.text)
            for chunk in result.chunks:
                chunk.timestamp = [(ts + offset if ts is not None else None) for ts in chunk.timestamp]
                all_chunks.append(chunk)
            if os.path.exists(path):
                os.remove(path)

        final_response = TranscriptionResponse(text=" ".join(combined_text), chunks=all_chunks)
        return final_response.model_dump_json()
    else:
        with open(audio_file_path, "rb") as f:
            result = send_request(f.read())
        return result.model_dump_json()


PODCASTS_CONFIG = [
    {
        "name": "making-coffee-with-lucia-solis",
        "rss_url": "https://rss.buzzsprout.com/604165.rss",
    },
    {
        "name": "tim-wendelboe",
        "rss_url": "https://feed.podbean.com/timwendelboe/feed.xml",
    },
]


async def main():
    parser = argparse.ArgumentParser(description="Download and transcribe podcast episodes")
    parser.add_argument("--skip-transcription", action="store_true", help="Skip the transcription step")
    args, _ = parser.parse_known_args()

    skip_transcription = args.skip_transcription

    all_feeds = [{"name": p["name"], "feed": feedparser.parse(p["rss_url"])} for p in PODCASTS_CONFIG]

    async with httpx.AsyncClient(
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
    ) as dl_client:
        for podcast_feed in all_feeds:
            podcast_name = podcast_feed["name"]
            feed = podcast_feed["feed"]
            podcast_dir = Path("podcast_data") / podcast_name
            podcast_dir.mkdir(parents=True, exist_ok=True)

            print(f"--- Processing podcast: {podcast_name} ---")

            # Backfill metadata for existing MP3s
            feed_lookup = {}
            for entry in feed.entries:
                entry_url = None
                for link in entry.links:
                    if link.rel == "enclosure":
                        entry_url = link.href
                        break
                if not entry_url and entry.links:
                    entry_url = entry.links[0].href
                if entry_url:
                    filename = Path(entry_url.split("?")[0]).name
                    feed_lookup[filename] = (entry, entry_url)

            for mp3_path in podcast_dir.glob("*.mp3"):
                meta_path = mp3_path.with_suffix(".metadata.json")
                if not meta_path.exists():
                    if mp3_path.name in feed_lookup:
                        entry, entry_url = feed_lookup[mp3_path.name]
                        metadata = {
                            "episode_title": entry.title,
                            "url": entry.get("link"),
                            "audio_url": entry_url,
                            "published_date": entry.get("published"),
                        }

                        # Handle missing Buzzsprout links
                        if not metadata["url"] and entry_url and "buzzsprout.com" in entry_url:
                            # Convert: .../episodes/123-slug.mp3?token -> .../episodes/123-slug
                            url = entry_url.split("?")[0]
                            if url.endswith(".mp3"):
                                url = url[:-4]
                            metadata["url"] = url

                        meta_path.write_text(json.dumps(metadata, indent=2))
                        print(f"[backfill] Generated metadata for {mp3_path.name}")

            for episode in feed.entries:
                try:
                    audio_url = None
                    for link in episode.links:
                        if link.rel == "enclosure":
                            audio_url = link.href
                            break
                    if not audio_url and episode.links:
                        audio_url = episode.links[0].href

                    if not audio_url:
                        continue

                    episode_filepath = podcast_dir / Path(audio_url.split("?")[0]).name
                    json_path = episode_filepath.with_suffix(".json")
                    metadata_path = episode_filepath.with_suffix(".metadata.json")

                    metadata = {
                        "episode_title": episode.title,
                        "url": episode.get("link"),
                        "audio_url": audio_url,
                        "published_date": episode.get("published"),
                    }

                    # Handle missing Buzzsprout links
                    if not metadata["url"] and audio_url and "buzzsprout.com" in audio_url:
                        # Convert: .../episodes/123-slug.mp3?token -> .../episodes/123-slug
                        url = audio_url.split("?")[0]
                        if url.endswith(".mp3"):
                            url = url[:-4]
                        metadata["url"] = url

                    metadata_path.write_text(json.dumps(metadata, indent=2))

                    await download_file(url=audio_url, path=episode_filepath, client=dl_client)

                    if skip_transcription:
                        print(f"[metadata only] {episode_filepath.name}")
                        continue
                    elif json_path.exists():
                        print(f"[skip transcription] {json_path} already exists")
                    else:
                        print(f"[transcribe] {episode_filepath}")
                        transcription = await transcribe_audio(episode_filepath)
                        json_path.write_text(transcription)
                        print(f"[transcribe] saved: {json_path}")
                except Exception as e:
                    print(f"[error] Failed to process episode '{episode.title}': {e}")

if __name__ == "__main__":
    asyncio.run(main())
