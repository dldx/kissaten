# /// script
# dependencies = ["marimo", "feedparser", "httpx", "tenacity", "requests", "pydantic"]
# requires-python = ">=3.13"
# ///

import marimo

__generated_with = "0.21.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import asyncio
    import math
    import os
    import subprocess
    import dotenv
    import sys
    import uuid
    from pathlib import Path
    import base64
    import json
    import requests
    from pydantic import BaseModel, Field

    import feedparser
    import httpx
    from tenacity import (
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_fixed,
    )

    return (
        BaseModel,
        Field,
        Path,
        base64,
        feedparser,
        httpx,
        json,
        os,
        requests,
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        sys,
        uuid,
        wait_fixed,
    )


@app.cell
def _(Path):
    path_cls = Path
    return (path_cls,)


@app.cell
def _(
    httpx,
    os,
    path_cls,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    sys,
    uuid,
    wait_fixed,
):
    @retry(
        retry=(retry_if_exception_type(httpx.HTTPError)),
        stop=stop_after_attempt(10),
        wait=wait_fixed(60),
    )
    async def download_file(*, url, path, client=None):
        """
        Atomically download a file from ``url`` to ``path``.

        If ``path`` already exists, the file will not be downloaded again.
        This means that different URLs should be saved to different paths.

        This function is meant to be used in cases where the contents of ``url``
        is immutable -- calling it more than once should always return the same bytes.

        Returns the download path.

        """
        path = path_cls(path)

        # If the URL has already been downloaded, we can skip downloading it again.
        if path.exists():
            return path

        path.parent.mkdir(parents=True, exist_ok=True)

        _owns_client = client is None
        if _owns_client:
            client = httpx.AsyncClient(
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/123.0.0.0 Safari/537.36"
                    )
                }
            )

        try:
            async with client.stream("GET", url, follow_redirects=True) as resp:
                resp.raise_for_status()

                # Download to a temporary path first.  That way, we only get
                # something at the destination path if the download is successful.
                #
                # We download to a path in the same directory so we can do an
                # atomic ``os.rename()`` later -- atomic renames don't work
                # across filesystem boundaries.
                tmp_path = path.parent / f"{path.name}.{uuid.uuid4()}.tmp"

                with open(tmp_path, "wb") as out_file:
                    async for chunk in resp.aiter_raw():
                        out_file.write(chunk)

        # If something goes wrong, it will probably be retried by tenacity.
        # Log the exception in case a programming bug has been introduced in
        # the ``try`` block or there's a persistent error.
        except Exception as exc:
            print(exc, file=sys.stderr)
            raise
        finally:
            if _owns_client:
                await client.aclose()

        os.rename(tmp_path, path)
        return path

    return (download_file,)


@app.cell
def _(dotenv, os):
    dotenv.load_dotenv()
    HF_TOKEN = os.getenv("HF_TOKEN")
    TRANSCRIPTION_ENDPOINT = os.getenv("HF_TRANSCRIPTION_ENDPOINT")

    # Headers for authentication
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    return TRANSCRIPTION_ENDPOINT, headers


@app.cell
def _(
    BaseModel,
    TRANSCRIPTION_ENDPOINT,
    base64,
    headers,
    json,
    os,
    requests,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
):
    from pydantic import ValidationError

    class Chunk(BaseModel):
        text: str
        timestamp: list[float | None]

    class TranscriptionResponse(BaseModel):
        text: str
        chunks: list[Chunk]

    async def transcribe_audio(audio_file_path):
        """Transcribe audio using direct async requests with Base64 encoding.
        Splits audio if needed and returns combined response.
        """
        file_size = os.path.getsize(audio_file_path)
        chunk_size_limit = 25 * 1024 * 1024  # 25MB
        max_segment_duration_s = 1700  # Match split_episode logic

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
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                return response.json()

            try:
                data = _get_response()
                return TranscriptionResponse.model_validate(data)
            except ValidationError as e:
                print(f"[retry] Validation error: {e}")
                try:
                    # Try once more
                    data = _get_response()
                    return TranscriptionResponse.model_validate(data)
                except ValidationError:
                    print("[fallback] Still failing validation, ignoring timestamp issue")
                    # Fallback: create model via model_construct or manually parse
                    # Since we updated Chunk to allow None, it should have passed if it was just a None value.
                    # If it's still failing, we can use model_construct to bypass validation if necessary
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
                    # Adjust timestamps based on chunk offset
                    chunk.timestamp = [(ts + offset if ts is not None else None) for ts in chunk.timestamp]
                    all_chunks.append(chunk)

                # Cleanup temporary chunk
                if os.path.exists(path):
                    os.remove(path)

            final_response = TranscriptionResponse(text=" ".join(combined_text), chunks=all_chunks)
            return final_response.model_dump_json()
        else:
            with open(audio_file_path, "rb") as f:
                result = send_request(f.read())
            return result.model_dump_json()

    return (transcribe_audio,)


@app.cell
def _():
    podcasts_config = [
        {
            "name": "making-coffee-with-lucia-solis",
            "rss_url": "https://oorss.buzzsprout.com/604165.rss",
        },
        {
            "name": "tim-wendelboe",
            "rss_url": "https://feed.podbean.com/timwendelboe/feed.xml",
        },
    ]
    return (podcasts_config,)


@app.cell
def _(feedparser, podcasts_config):
    all_feeds = [{"name": p["name"], "feed": feedparser.parse(p["rss_url"])} for p in podcasts_config]
    return (all_feeds,)


@app.function
def split_episode(episode_filepath):
    """Split episode into chunks of ~1.7 million ms (~28 min) using ffmpeg."""
    import subprocess
    import math
    from pathlib import Path

    max_segment_duration_ms = 1700 * 1000  # 1700 seconds in ms
    # Get total duration via ffprobe
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


@app.cell
def _(all_feeds):
    all_feeds[0]["feed"].entries[0]
    return


@app.cell
def _():
    return


@app.cell
def _(path_cls, split_episode):
    split_episode(
        path_cls(
            "podcast_data/making-coffee-with-lucia-solis/16881653-69-whole-coffee-cherry-fermentations-the-multiple-paradoxes-of-naturals.mp3"
        )
    )
    return


@app.cell
async def _(all_feeds, download_file, path_cls, transcribe_audio):
    """
    For each podcast and each episode, sequentially:
      1. Download the MP3 (skipped if already on disk) to its specific folder.
      2. Transcribe the audio and write the result to a .txt file next to the MP3.
    """

    results = []

    async with __import__("httpx").AsyncClient(
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
        }
    ) as dl_client:
        for podcast_feed in all_feeds:
            podcast_name = podcast_feed["name"]
            feed = podcast_feed["feed"]
            podcast_dir = path_cls("podcast_data") / podcast_name
            podcast_dir.mkdir(parents=True, exist_ok=True)

            print(f"--- Processing podcast: {podcast_name} ---")

            for episode in feed.entries:
                # Find the enclosure link for the audio file
                audio_url = None
                for link in episode.links:
                    if link.rel == "enclosure":
                        audio_url = link.href
                        break

                # Fallback to the first link if no enclosure is found
                if not audio_url and episode.links:
                    audio_url = episode.links[0].href

                if not audio_url:
                    print(f"[skip] No audio link found for episode: {episode.title}")
                    continue

                episode_filepath = podcast_dir / path_cls(audio_url.split("?")[0]).name
                txt_path = episode_filepath.with_suffix(".txt")

                # --- Step 1: Download ---
                print(f"[download] {episode.title} → {episode_filepath}")
                await download_file(url=audio_url, path=episode_filepath, client=dl_client)

                # --- Step 2: Transcribe (skip if transcript already exists) ---
                if txt_path.exists():
                    print(f"[skip transcription] {txt_path} already exists")
                    transcription = txt_path.read_text()
                else:
                    print(f"[transcribe] {episode_filepath}")
                    transcription = await transcribe_audio(episode_filepath)
                    txt_path.write_text(transcription)
                    print(f"[saved] {txt_path}")

                results.append(
                    {
                        "podcast": podcast_name,
                        "title": episode.title,
                        "path": str(episode_filepath),
                        "transcription": transcription,
                    }
                )

    return (results,)


if __name__ == "__main__":
    app.run()
