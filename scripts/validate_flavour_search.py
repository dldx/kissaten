#!/usr/bin/env python3
"""Validate post-change flavour-search results against the captured baseline.

The hierarchy-aware change to ``tasting_notes_query`` is a pure OR-expansion, so
for most queries the new result id set must be a SUPERSET of the baseline
captured by ``scripts/capture_flavour_search_baseline.py``. Queries whose terms
cannot collide with any tasting-note category display name instead carry
``"expect": "equal"`` in the baseline and must match the baseline id set exactly.

Each query/mode is re-fetched with the same pagination logic. The default page
cap is 300 (at per_page=100, enough for the ~13,150-row expanded "fruit"
families). If a record still truncates at the cap its comparison is
INCONCLUSIVE: a WARNING is printed to stderr and the record is counted neither
as a pass nor a failure. The script exits non-zero only on real superset
violations or equality violations.

``--expect-equal <glob>`` is an override/complement to the per-query ``expect``
field: it additionally requires EXACT set equality for query names matching the
glob, regardless of their ``expect`` value. Use it only for terms that cannot
collide with any tasting-note category display name (e.g. ``"Peach"``).

Usage
-----
  python scripts/validate_flavour_search.py
  python scripts/validate_flavour_search.py --api-base http://localhost:8001
  python scripts/validate_flavour_search.py --expect-equal 'exact_*'
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Same mode definitions as the capture script: (mode_label, sort_by, sort_order).
MODES = [
    ("strict", "name", "asc"),
    ("relevance", "relevance", "desc"),
]

# How many missing ids to print per violation before truncating the sample.
MISSING_SAMPLE_CAP = 20


def http_get_json(url: str, timeout: float = 60.0) -> tuple[int, object]:
    """GET `url` and return (status_code, parsed_json_or_body_snippet)."""
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
    """Stable bean identifier: id, else bean_id, else clean_url_slug."""
    for key in ("id", "bean_id", "clean_url_slug"):
        value = bean.get(key)
        if value is None:
            continue
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return value
    return None


def fetch_ids(
    api_base: str, request_params: dict, sort_by: str, sort_order: str, per_page: int, max_pages: int
) -> tuple[set, bool, int | None] | dict:
    """Page through /v1/search for one query/mode.

    Returns ``(ids, truncated, total_items)`` on success, or an error dict
    ``{"error": status, "detail": ...}`` on failure.
    """
    ids: set = set()
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
            if isinstance(bean, dict):
                ids.add(extract_identifier(bean))

        if len(items) < per_page:
            break
        if total_items is not None and len(ids) >= total_items:
            break
        page += 1

    return ids, truncated, total_items


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--baseline", default="tests/fixtures/flavour_search_baseline.json", help="Baseline JSON path")
    parser.add_argument("--api-base", default="http://localhost:8000", help="Base URL of the running API")
    parser.add_argument("--per-page", type=int, default=100, help="Items per page (default: 100)")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=300,
        help="Safety cap on pages; a record truncated at this cap is reported inconclusive (default: 300)",
    )
    parser.add_argument(
        "--expect-equal",
        default=None,
        metavar="GLOB",
        help=(
            "Override/complement the per-query expect field: require exact set equality "
            "for query names matching this glob (only safe for terms that cannot collide "
            "with a category display name)."
        ),
    )
    args = parser.parse_args()

    baseline_path = Path(args.baseline)
    if not baseline_path.exists():
        print(f"ERROR: baseline not found: {baseline_path}", file=sys.stderr)
        return 2
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    per_page = args.per_page
    max_pages = args.max_pages

    health_status, health_payload = http_get_json(build_url(args.api_base, "/v1/health", {}))
    if health_status != 200:
        print(
            f"ERROR: API not reachable at {args.api_base} (GET /v1/health -> {health_status}: {health_payload!r})",
            file=sys.stderr,
        )
        return 2
    print(f"Validating against {args.api_base} (baseline {baseline_path}, per_page={per_page}, max_pages={max_pages})")
    if args.expect_equal:
        print(f"  --expect-equal glob: {args.expect_equal!r}")

    violations = 0
    warnings = 0
    checked = 0
    eq_checked = 0
    failures: list[str] = []
    inconclusive: list[str] = []

    print()
    print(f"{'query':<28} {'mode':<10} {'baseline':>9} {'new':>7} {'missing':>8} {'result':>8}")
    print("-" * 76)

    for entry in baseline.get("queries", []):
        name = entry["name"]
        request_params = entry.get("request", {})
        # Per-query `expect` field drives equality; --expect-equal is an override/complement.
        require_equal = entry.get("expect", "superset") == "equal"
        if args.expect_equal and fnmatch.fnmatch(name, args.expect_equal):
            require_equal = True

        for mode, sort_by, sort_order in MODES:
            baseline_rec = entry.get(mode)
            if not isinstance(baseline_rec, dict) or "error" in baseline_rec:
                print(f"{name:<28} {mode:<10} {'SKIP (baseline error)':>44}")
                continue

            baseline_ids = set(baseline_rec.get("ids", []))
            result = fetch_ids(args.api_base, request_params, sort_by, sort_order, per_page, max_pages)

            if isinstance(result, dict):  # request error
                violations += 1
                failures.append(f"{name}[{mode}]: request failed ({result['error']})")
                print(f"{name:<28} {mode:<10} {len(baseline_ids):>9} {'ERR':>7} {'-':>8} {'FAIL':>8}")
                continue

            new_ids, truncated, total = result

            if truncated:
                # Still hit the page cap: the comparison is inconclusive, not a pass/fail.
                warnings += 1
                msg = (
                    f"{name}[{mode}]: TRUNCATED at max_pages={max_pages} "
                    f"({len(new_ids)} ids fetched, total_items={total}); comparison inconclusive"
                )
                inconclusive.append(msg)
                print(f"WARNING: {msg}", file=sys.stderr)
                print(f"{name:<28} {mode:<10} {len(baseline_ids):>9} {len(new_ids):>7} {'-':>8} {'WARN':>8}")
                continue

            checked += 1
            missing = baseline_ids - new_ids

            if missing:
                violations += 1
                sample = sorted(missing)[:MISSING_SAMPLE_CAP]
                suffix = "" if len(missing) <= MISSING_SAMPLE_CAP else f" (+{len(missing) - MISSING_SAMPLE_CAP} more)"
                failures.append(f"{name}[{mode}]: {len(missing)} baseline id(s) missing, e.g. {sample}{suffix}")
                print(f"{name:<28} {mode:<10} {len(baseline_ids):>9} {len(new_ids):>7} {len(missing):>8} {'FAIL':>8}")
            elif require_equal and new_ids != baseline_ids:
                violations += 1
                extra = sorted(new_ids - baseline_ids)[:MISSING_SAMPLE_CAP]
                failures.append(
                    f"{name}[{mode}]: expected equal but {len(new_ids - baseline_ids)} extra id(s), e.g. {extra}"
                )
                print(f"{name:<28} {mode:<10} {len(baseline_ids):>9} {len(new_ids):>7} {'0':>8} {'NEQ':>8}")
            else:
                if require_equal:
                    eq_checked += 1
                    label = "EQ-OK"
                else:
                    label = "OK"
                print(f"{name:<28} {mode:<10} {len(baseline_ids):>9} {len(new_ids):>7} {'0':>8} {label:>8}")

    print()
    if inconclusive:
        print(
            f"WARN: {warnings} query/mode(s) inconclusive (truncated at max_pages={max_pages}); "
            "increase --max-pages to compare fully:",
            file=sys.stderr,
        )
        for line in inconclusive:
            print(f"  - {line}", file=sys.stderr)
    if failures:
        print(f"FAIL: {violations} violation(s) across {checked} checked query/mode(s):")
        for line in failures:
            print(f"  - {line}")
        return 1

    eq_note = f", {eq_checked} exact-equality" if eq_checked else ""
    warn_note = f" ({warnings} truncated/inconclusive)" if warnings else ""
    print(f"PASS: all {checked} checked query/mode(s) satisfy the superset invariant{eq_note}{warn_note}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
