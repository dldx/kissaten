#!/usr/bin/env python3
"""Capture a reproducible baseline of `tasting_notes_query` matches on /v1/search.

Purpose
-------
We are about to make the single existing `tasting_notes_query` parameter
hierarchy-aware, so that a bare family term like ``fruity`` expands to every
note in the Fruity family (no new API params). To prove the change is safe we
snapshot the CURRENT (pre-change) result sets here, then after the change
verify the new id sets are a SUPERSET of these baselines. Because the
hierarchy change is a pure OR-expansion, a superset is the invariant for every
query/mode; per-query ``expect`` records that default explicitly.

This is a pure data-capture task. It only performs GETs against an already
running API and writes one JSON artifact; it never mutates server state.

Each query/mode record is deliberately slim — only ``total_items``,
``returned_count``, ``truncated`` and the list of integer bean ``ids`` — to
keep the committed fixture small. ``category_reference`` is retained in full
as the ground truth for computing a family's expected child notes.

Both scoring branches are captured per query:
  * strict    -> sort_by=name&sort_order=asc
                (exercises the WHERE/ILIKE branch of
                 parse_boolean_search_query_for_field)
  * relevance -> sort_by=relevance&sort_order=desc
                (exercises the granular-scoring branch)

Usage
-----
  python scripts/capture_flavour_search_baseline.py
  python scripts/capture_flavour_search_baseline.py --api-base http://localhost:8000 \
      --output tests/fixtures/flavour_search_baseline.json --per-page 100 --max-pages 60
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Top-level invariant recorded in the dataset. The hierarchy-aware change ORs
# each bare term with its category expansion, so it can only ever ADD matches:
# new result sets must be supersets of the pre-change baselines.
INVARIANT = (
    "Hierarchy-aware expansion is a pure OR-expansion: for every query/mode the "
    "post-change id set must be a superset of the baseline id set."
)


# ---------------------------------------------------------------------------
# Query set: each entry maps a stable name to the extra request params.
# `tasting_notes_query` is the default param; the one exception
# (`tasting_notes_only_fruity`) deliberately uses `query` +
# `tasting_notes_only=true` to capture the deprecated path.
# ---------------------------------------------------------------------------
QUERIES: list[dict] = [
    {"name": "literal_chocolate", "request": {"tasting_notes_query": "chocolate"}},
    {"name": "literal_caramel", "request": {"tasting_notes_query": "caramel"}},
    {"name": "literal_berry", "request": {"tasting_notes_query": "berry"}},
    {"name": "literal_peach", "request": {"tasting_notes_query": "peach"}},
    {"name": "substring_fruit", "request": {"tasting_notes_query": "fruit"}},
    {"name": "wildcard_fruit_star", "request": {"tasting_notes_query": "fruit*"}},
    {"name": "wildcard_choc_star", "request": {"tasting_notes_query": "choc*"}},
    {"name": "and_chocolate_caramel", "request": {"tasting_notes_query": "chocolate&caramel"}},
    {"name": "or_chocolate_caramel", "request": {"tasting_notes_query": "chocolate|caramel"}},
    {"name": "not_chocolate_bitter", "request": {"tasting_notes_query": "chocolate&!bitter"}},
    {"name": "group_berry_lemon_lime", "request": {"tasting_notes_query": "berry&(lemon|lime)"}},
    {"name": "exact_peach", "request": {"tasting_notes_query": '"Peach"'}},
    {"name": "exact_fruity", "request": {"tasting_notes_query": '"Fruity"'}},
    {"name": "family_fruity", "request": {"tasting_notes_query": "fruity"}},
    {"name": "family_citrus", "request": {"tasting_notes_query": "citrus"}},
    {"name": "family_nutty", "request": {"tasting_notes_query": "nutty"}},
    {"name": "family_floral", "request": {"tasting_notes_query": "floral"}},
    {"name": "multiword_phrase", "request": {"tasting_notes_query": "passion fruit"}},
    {"name": "rare_no_match", "request": {"tasting_notes_query": "zzzznotaflavour"}},
    {"name": "tasting_notes_only_fruity", "request": {"query": "fruity", "tasting_notes_only": True}},
]

# Queries whose current baselines are expected to be small/zero because the
# family term is matched literally instead of expanded through the hierarchy.
FAMILY_QUERIES = {
    "family_fruity",
    "family_citrus",
    "family_nutty",
    "family_floral",
    "substring_fruit",
}

# Modes captured for every query: (mode_label, sort_by, sort_order).
MODES = [
    ("strict", "name", "asc"),
    ("relevance", "relevance", "desc"),
]


def http_get_json(url: str, timeout: float = 60.0) -> tuple[int, object]:
    """GET `url` and return (status_code, parsed_json_or_body_snippet).

    Never raises on a non-2xx response; the caller records the status/detail.
    """
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return exc.code, raw[:500]
    except urllib.error.URLError as exc:
        return 0, f"connection error: {exc.reason}"

    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw[:500]


def build_url(api_base: str, path: str, params: dict) -> str:
    base = api_base.rstrip("/")
    query: list[tuple[str, str]] = []
    for key, value in params.items():
        if isinstance(value, list | tuple):
            for item in value:
                query.append((key, str(item)))
        else:
            query.append((key, str(value)))
    return f"{base}{path}?{urllib.parse.urlencode(query)}"


def extract_identifier(bean: dict) -> int | str | None:
    """Stable bean identifier: id, else bean_id, else clean_url_slug.

    Numeric identifiers are coerced to int so the committed ``ids`` arrays stay
    compact and compare cleanly. In practice every search result carries an
    integer ``id``, so the slug fallback is only a defensive last resort.
    """
    for key in ("id", "bean_id", "clean_url_slug"):
        value = bean.get(key)
        if value is None:
            continue
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return value
    return None


def capture_mode(
    api_base: str, request_params: dict, mode: str, sort_by: str, sort_order: str, per_page: int, max_pages: int
) -> dict:
    """Page through /v1/search for one query/mode and return the result record."""
    collected_ids: list = []
    total_items = None
    page = 1
    truncated = False

    while True:
        if page > max_pages:
            truncated = True
            break

        params = dict(request_params)
        params.update(
            {
                "per_page": per_page,
                "page": page,
                "sort_by": sort_by,
                "sort_order": sort_order,
            }
        )
        url = build_url(api_base, "/v1/search", params)
        status, payload = http_get_json(url)

        if status != 200 or not isinstance(payload, dict) or not payload.get("success", False):
            detail = payload if isinstance(payload, str) else json.dumps(payload)[:500]
            return {"error": status, "detail": detail}

        items = payload.get("data") or []
        pagination = payload.get("pagination") or {}
        if pagination.get("total_items") is not None:
            total_items = pagination["total_items"]

        for bean in items:
            if not isinstance(bean, dict):
                continue
            collected_ids.append(extract_identifier(bean))

        # Stop when the server says there is nothing more, or the final short
        # page arrived, or we've collected the advertised total.
        if len(items) < per_page:
            break
        if total_items is not None and len(collected_ids) >= total_items:
            break
        page += 1

    return {
        "total_items": total_items if total_items is not None else len(collected_ids),
        "returned_count": len(collected_ids),
        "truncated": truncated,
        "ids": collected_ids,
    }


def capture_category_reference(api_base: str) -> dict:
    """Capture the tasting-note hierarchy as {primary: [group, ...]}.

    Mirrors `data.categories` from /v1/tasting-note-categories so a later
    validator can compute "all notes under Fruity" independently of search.
    """
    status, payload = http_get_json(build_url(api_base, "/v1/tasting-note-categories", {}))
    if status != 200 or not isinstance(payload, dict):
        return {"error": status, "detail": payload if isinstance(payload, str) else json.dumps(payload)[:500]}
    return (payload.get("data") or {}).get("categories") or {}


def git_short_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def print_summary(dataset: dict) -> None:
    print()
    print(f"{'query':<28} {'mode':<10} {'total':>8} {'returned':>9} {'trunc':>6}")
    print("-" * 66)
    for entry in dataset["queries"]:
        for mode in ("strict", "relevance"):
            rec = entry.get(mode, {})
            if "error" in rec:
                print(f"{entry['name']:<28} {mode:<10} {'ERROR':>8} {rec['error']!s:>9}")
                continue
            print(
                f"{entry['name']:<28} {mode:<10} "
                f"{rec['total_items']:>8} {rec['returned_count']:>9} "
                f"{str(rec['truncated']):>6}"
            )

    print()
    print("family / substring baselines (the gap being fixed):")
    for entry in dataset["queries"]:
        if entry["name"] not in FAMILY_QUERIES:
            continue
        strict = entry.get("strict", {})
        total = strict.get("total_items", "ERR") if "error" not in strict else "ERR"
        print(f"  {entry['name']:<28} strict total_items = {total}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api-base", default="http://localhost:8000", help="Base URL of the running API")
    parser.add_argument(
        "--output",
        default="tests/fixtures/flavour_search_baseline.json",
        help="Path to write the captured dataset JSON",
    )
    parser.add_argument("--per-page", type=int, default=100, help="Items per page (API max 100)")
    parser.add_argument("--max-pages", type=int, default=60, help="Safety cap on pages per query/mode")
    args = parser.parse_args()

    # 1. Health check — fail fast with a clear message.
    health_status, health_payload = http_get_json(build_url(args.api_base, "/v1/health", {}))
    if health_status != 200:
        print(
            f"ERROR: API not reachable at {args.api_base} (GET /v1/health -> {health_status}: {health_payload!r})",
            file=sys.stderr,
        )
        return 2
    print(f"API healthy at {args.api_base} (GET /v1/health -> 200)")

    # 2. Capture one category reference (ground truth for expected expansion).
    print("Capturing /v1/tasting-note-categories reference ...")
    category_reference = capture_category_reference(args.api_base)

    # 3. Capture every query in both modes.
    query_records = []
    for spec in QUERIES:
        record = {"name": spec["name"], "request": spec["request"], "expect": "superset"}
        for mode, sort_by, sort_order in MODES:
            print(f"  {spec['name']:<28} [{mode}] ...", flush=True)
            record[mode] = capture_mode(
                args.api_base,
                spec["request"],
                mode,
                sort_by,
                sort_order,
                args.per_page,
                args.max_pages,
            )
        query_records.append(record)

    dataset = {
        "invariant": INVARIANT,
        "meta": {
            "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "api_base": args.api_base,
            "git_commit": git_short_commit(),
            "purpose": (
                "Baseline of tasting_notes_query matches before hierarchy-aware "
                "expansion; new results must be a superset of these id sets."
            ),
            "per_page": args.per_page,
            "max_pages": args.max_pages,
        },
        "queries": query_records,
        "category_reference": category_reference,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(dataset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {output_path} ({output_path.stat().st_size} bytes)")

    truncated = []
    for entry in query_records:
        for mode in ("strict", "relevance"):
            rec = entry.get(mode)
            if isinstance(rec, dict) and rec.get("truncated"):
                truncated.append((entry["name"], mode))
    if truncated:
        print(
            f"WARNING: {len(truncated)} query/mode(s) truncated at --max-pages "
            f"{args.max_pages}: {truncated}. Raise --max-pages for a complete baseline.",
            file=sys.stderr,
        )

    print_summary(dataset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
