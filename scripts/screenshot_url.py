"""Render a URL headless with Playwright (sync API) and save a PNG.

Shared by the scraper-authoring skills (shopify-scraper, squarespace-scraper,
non-shopify-scraper) for a quick visual check of a product/listing page before
choosing a scrape shape. Simple, self-contained, standard library + Playwright.

Usage examples:
    uv run python scripts/screenshot_url.py https://castironroasters.com/products/samusure-rwanda
    uv run python scripts/screenshot_url.py https://example.com /tmp/opencode/shot.png --full-page
    uv run python scripts/screenshot_url.py <url> --no-full-page \
        --cookie-selector "#onetrust-accept-btn-handler" --no-scroll-lazy
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

# Matches the Chrome UA used by the scraper skills.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _default_output_name(url: str) -> str:
    """Derive a filename from the URL host, e.g. castironroasters_com.png."""
    host = urlparse(url).netloc.split("@")[-1].split(":")[0]
    safe = host.replace(".", "_") or "page"
    return f"{safe}.png"


def _load_lazy_content(page: object, wait_ms: int, max_steps: int = 300) -> None:
    """Scroll incrementally through the page so lazy-loaded content loads.

    IntersectionObserver/lazy-loaders fire for every viewport-height chunk, and
    we re-read the expanded scroll height each step (with ``documentElement``
    as a fallback) so newly rendered images that grow the layout are included in
    a full-page capture. A single ``scrollTo(0, scrollHeight)`` can skip content
    in the middle of some sites, so we step through it instead. Bounded by
    ``max_steps`` so this can never loop forever. Returns to the top before the
    caller captures.
    """
    last_height = -1
    for _ in range(max_steps):
        page.evaluate("window.scrollBy(0, window.innerHeight)")
        page.wait_for_timeout(wait_ms)
        height = page.evaluate("Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
        if height <= last_height:
            break
        last_height = height
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(wait_ms)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render a URL headless and save a PNG screenshot.")
    parser.add_argument("url", help="The URL to screenshot.")
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="Output PNG path. Defaults to '<host>.png' derived from the URL.",
    )
    parser.add_argument(
        "--full-page",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Capture the full scrollable page (default: True).",
    )
    parser.add_argument("--width", type=int, default=1280, help="Viewport width (default: 1280).")
    parser.add_argument("--height", type=int, default=900, help="Viewport height (default: 900).")
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=2000,
        help="Milliseconds to wait after DOMContentLoaded for dynamic content (default: 2000).",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=30000,
        help="Navigation timeout in milliseconds (default: 30000).",
    )
    parser.add_argument(
        "--wait-until",
        choices=["domcontentloaded", "load", "networkidle"],
        default="networkidle",
        help=(
            "When to consider navigation complete. Defaults to networkidle, falling "
            "back to domcontentloaded gracefully if it times out (some sites with "
            "chat/analytics widgets never go idle)."
        ),
    )
    parser.add_argument(
        "--cookie-selector",
        action="append",
        default=[],
        metavar="SELECTOR",
        help="CSS selector to click to dismiss a cookie banner. Repeatable. Best-effort.",
    )
    parser.add_argument(
        "--scroll-lazy",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Scroll incrementally through the page before capturing so lazy-loaded "
            "content loads into a full-page screenshot (default: True). Pass "
            "--no-scroll-lazy to disable. Only meaningful with --full-page."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    output_path = Path(args.output) if args.output else Path(_default_output_name(args.url))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build the Playwright launch options, honoring HTTP(S)_PROXY like base.py.
    proxy_url = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    launch_options: dict = {
        "headless": True,
        "args": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-first-run",
        ],
    }
    if proxy_url:
        parsed = urlparse(proxy_url)
        if parsed.username or parsed.password:
            server_url = f"{parsed.scheme}://{parsed.hostname}"
            if parsed.port:
                server_url += f":{parsed.port}"
            launch_options["proxy"] = {
                "server": server_url,
                "username": parsed.username or "",
                "password": parsed.password or "",
            }
        else:
            launch_options["proxy"] = {"server": proxy_url}

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_options)
        try:
            page = browser.new_page(viewport={"width": args.width, "height": args.height}, user_agent=USER_AGENT)
            try:
                page.goto(args.url, wait_until=args.wait_until, timeout=args.timeout_ms)
            except Exception as exc:
                # Some sites with chat/analytics widgets never reach networkidle/load;
                # fall back gracefully instead of crashing the script.
                if args.wait_until == "domcontentloaded":
                    raise
                print(f"Navigation with wait_until={args.wait_until} failed ({exc}); retrying with domcontentloaded")
                page.goto(args.url, wait_until="domcontentloaded", timeout=args.timeout_ms)
            page.wait_for_timeout(args.wait_ms)

            # Best-effort cookie banner dismissal (ignore any failure).
            for selector in args.cookie_selector:
                try:
                    with page.expect_navigation(wait_until="domcontentloaded", timeout=3000):
                        page.click(selector, timeout=3000)
                        page.wait_for_timeout(500)
                except Exception:
                    try:
                        page.click(selector, timeout=500)
                        page.wait_for_timeout(500)
                    except Exception:
                        pass

            if args.full_page and args.scroll_lazy:
                _load_lazy_content(page, wait_ms=500)

            page.screenshot(path=str(output_path), full_page=args.full_page, type="png")
        finally:
            browser.close()

    size = output_path.stat().st_size
    print(f"Saved screenshot: {output_path.resolve()} ({size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
