#!/usr/bin/env python3
"""Analyze rw_kissaten.duckdb for roasters with potential scraping issues.

Categorizes roasters into issue types:
  - Stale: not scraped recently
  - SPA URLs: products share base URLs with fragment-only differences
  - Duplicates: many rows per unique URL (re-scrapes without dedup)
  - All OOS: every bean shows out of stock (scraper in_stock bug)
  - Missing data: critical fields (price/image/roast/weight) not extracted

Outputs a rich-formatted report and ends with a prioritized checklist.
"""

import os
from collections import defaultdict
from pathlib import Path

import duckdb
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

DB_PATH = Path(__file__).parent.parent / "data" / "rw_kissaten.duckdb"

# Thresholds
STALE_DAYS = 14
MIN_BEANS_FOR_DUPES = 20
DUPE_PCT_THRESHOLD = 10.0
ALL_OOS_MIN_BEANS = 5
MIN_BEANS_FOR_MISSING = 20
MISSING_PCT_THRESHOLD = 30.0
SPA_URL_MIN_BEANS = 5


def get_conn() -> duckdb.DuckDBPyConnection:
    """Connect to rw_kissaten.duckdb with external access enabled."""
    return duckdb.connect(str(DB_PATH), config={"enable_external_access": True})


def find_stale_roasters(conn) -> list[dict]:
    """Roasters not scraped in the last STALE_DAYS days."""
    rows = conn.execute(
        """
        SELECT
            roaster,
            COUNT(*) as bean_count,
            MAX(scraped_at) as last_scrape,
            CAST(CURRENT_TIMESTAMP AS DATE) - CAST(MAX(scraped_at) AS DATE) as days_old
        FROM coffee_beans
        GROUP BY roaster
        HAVING days_old > ?
        ORDER BY days_old DESC
        """,
        [STALE_DAYS],
    ).fetchall()
    return [
        {"roaster": r[0], "beans": r[1], "last_scrape": r[2], "days_old": r[3]}
        for r in rows
    ]


def find_spa_roasters(conn) -> list[dict]:
    """Roasters where many beans use fragment-only URLs (SPA pattern)."""
    rows = conn.execute(
        """
        SELECT
            roaster,
            COUNT(*) as bean_count,
            SUM(CASE WHEN url LIKE '%#%' THEN 1 ELSE 0 END) as fragment_urls,
            ROUND(100.0 * SUM(CASE WHEN url LIKE '%#%' THEN 1 ELSE 0 END) / COUNT(*), 1) as pct_fragment
        FROM coffee_beans
        GROUP BY roaster
        HAVING COUNT(*) >= ? AND SUM(CASE WHEN url LIKE '%#%' THEN 1 ELSE 0 END) > 0
        ORDER BY fragment_urls DESC
        """,
        [SPA_URL_MIN_BEANS],
    ).fetchall()
    return [
        {"roaster": r[0], "beans": r[1], "fragment_urls": r[2], "pct_fragment": r[3]}
        for r in rows
    ]


def find_duplicate_roasters(conn) -> list[dict]:
    """Roasters with many rows per unique URL (excess duplication)."""
    rows = conn.execute(
        """
        SELECT
            roaster,
            COUNT(*) as total_rows,
            COUNT(DISTINCT url) as unique_urls,
            COUNT(*) - COUNT(DISTINCT url) as dupes,
            ROUND(100.0 * (COUNT(*) - COUNT(DISTINCT url)) / COUNT(*), 1) as pct_dupe
        FROM coffee_beans
        GROUP BY roaster
        HAVING COUNT(*) >= ? AND ROUND(100.0 * (COUNT(*) - COUNT(DISTINCT url)) / COUNT(*), 1) >= ?
        ORDER BY dupes DESC
        """,
        [MIN_BEANS_FOR_DUPES, DUPE_PCT_THRESHOLD],
    ).fetchall()
    return [
        {
            "roaster": r[0],
            "total_rows": r[1],
            "unique_urls": r[2],
            "dupes": r[3],
            "pct_dupe": r[4],
        }
        for r in rows
    ]


def find_all_oos_roasters(conn) -> list[dict]:
    """Roasters where every bean is out of stock (potential scraper bug)."""
    rows = conn.execute(
        """
        SELECT
            roaster,
            COUNT(*) as total,
            SUM(CASE WHEN in_stock = TRUE THEN 1 ELSE 0 END) as in_stock,
            SUM(CASE WHEN in_stock = FALSE THEN 1 ELSE 0 END) as oos
        FROM coffee_beans
        GROUP BY roaster
        HAVING COUNT(*) >= ?
          AND SUM(CASE WHEN in_stock = TRUE THEN 1 ELSE 0 END) = 0
        ORDER BY total DESC
        """,
        [ALL_OOS_MIN_BEANS],
    ).fetchall()
    return [{"roaster": r[0], "total": r[1], "oos": r[2]} for r in rows]


# roast_level is omitted: it's optional on most source sites (~60-100% missing
# industry-wide), so it's a poor signal of scraper health.
MISSING_FIELDS = ["price", "image", "desc", "weight"]


def find_missing_data_roasters(conn) -> list[dict]:
    """Roasters with high rates of missing price/image/description/weight.

    roast_level is intentionally excluded: it is missing on most roasters across
    the dataset (typically optional on the source site), so it's not a reliable
    signal of scraper breakage.
    """
    rows = conn.execute(
        """
        SELECT
            roaster,
            COUNT(*) as total,
            ROUND(100.0 * SUM(CASE WHEN price IS NULL OR price = 0 THEN 1 ELSE 0 END) / COUNT(*), 1) as pct_no_price,
            ROUND(100.0 * SUM(CASE WHEN image_url IS NULL OR image_url = '' THEN 1 ELSE 0 END) / COUNT(*), 1) as pct_no_image,
            ROUND(100.0 * SUM(CASE WHEN description IS NULL OR description = '' THEN 1 ELSE 0 END) / COUNT(*), 1) as pct_no_desc,
            ROUND(100.0 * SUM(CASE WHEN weight IS NULL OR weight = 0 THEN 1 ELSE 0 END) / COUNT(*), 1) as pct_no_weight
        FROM coffee_beans
        GROUP BY roaster
        HAVING COUNT(*) >= ?
        """,
        [MIN_BEANS_FOR_MISSING],
    ).fetchall()

    results = []
    for r in rows:
        roaster = r[0]
        fields = dict(zip(MISSING_FIELDS, [r[2], r[3], r[4], r[5]]))
        bad = {k: v for k, v in fields.items() if v >= MISSING_PCT_THRESHOLD}
        if bad:
            results.append({"roaster": roaster, "total": r[1], "bad_fields": bad})
    results.sort(key=lambda x: sum(x["bad_fields"].values()), reverse=True)
    return results


def render_stale_table(data: list[dict]) -> Table:
    table = Table(title="Stale Scrapes", title_style="bold red")
    table.add_column("Roaster", style="cyan")
    table.add_column("Beans", justify="right")
    table.add_column("Last Scrape")
    table.add_column("Days Old", justify="right", style="red")
    for d in data:
        table.add_row(d["roaster"], str(d["beans"]), str(d["last_scrape"])[:19], str(d["days_old"]))
    return table


def render_spa_table(data: list[dict]) -> Table:
    table = Table(title="SPA / Fragment-Only URLs", title_style="bold yellow")
    table.add_column("Roaster", style="cyan")
    table.add_column("Beans", justify="right")
    table.add_column("Fragment URLs", justify="right")
    table.add_column("% Fragment", justify="right", style="yellow")
    for d in data:
        table.add_row(d["roaster"], str(d["beans"]), str(d["fragment_urls"]), f"{d['pct_fragment']}%")
    return table


def render_dupe_table(data: list[dict]) -> Table:
    table = Table(title="Duplicate URL Rows", title_style="bold magenta")
    table.add_column("Roaster", style="cyan")
    table.add_column("Rows", justify="right")
    table.add_column("Unique URLs", justify="right")
    table.add_column("Dupes", justify="right")
    table.add_column("% Dupe", justify="right", style="magenta")
    for d in data:
        table.add_row(
            d["roaster"],
            str(d["total_rows"]),
            str(d["unique_urls"]),
            str(d["dupes"]),
            f"{d['pct_dupe']}%",
        )
    return table


def render_oos_table(data: list[dict]) -> Table:
    table = Table(title="Always Out-of-Stock", title_style="bold orange1")
    table.add_column("Roaster", style="cyan")
    table.add_column("Beans", justify="right")
    table.add_column("In Stock", justify="right")
    table.add_column("Out of Stock", justify="right", style="orange1")
    for d in data:
        table.add_row(d["roaster"], str(d["total"]), "0", str(d["oos"]))
    return table


def render_missing_table(data: list[dict]) -> Table:
    table = Table(title="Missing Critical Fields", title_style="bold blue")
    table.add_column("Roaster", style="cyan")
    table.add_column("Beans", justify="right")
    table.add_column("Top Missing Fields")
    for d in data:
        top_fields = ", ".join(f"{k}={v}%" for k, v in d["bad_fields"].items())
        table.add_row(d["roaster"], str(d["total"]), top_fields)
    return table


def build_priority_checklist(
    stale, spa, dupes, all_oos, missing
) -> list[tuple[str, str, str]]:
    """Build a deduplicated, prioritized list of roasters to investigate.

    Priority order:
      P0: Stale + duplicates + all-OOS (likely completely broken)
      P1: SPA URLs (scraping architecture mismatch)
      P2: Missing data (extraction broken)
    """
    issues_by_roaster: dict[str, set[str]] = defaultdict(set)
    priority_map: dict[str, str] = {}

    for d in stale:
        issues_by_roaster[d["roaster"]].add("stale")
        priority_map[d["roaster"]] = "P0"
    for d in dupes:
        issues_by_roaster[d["roaster"]].add("duplicates")
        priority_map[d["roaster"]] = "P0"
    for d in all_oos:
        issues_by_roaster[d["roaster"]].add("all-OOS")
        priority_map[d["roaster"]] = "P0"
    for d in spa:
        issues_by_roaster[d["roaster"]].add("SPA")
        priority_map.setdefault(d["roaster"], "P1")
    for d in missing:
        issues_by_roaster[d["roaster"]].add("missing-data")
        priority_map.setdefault(d["roaster"], "P2")

    # Stable priority sort: P0 < P1 < P2, then alphabetical
    priority_order = {"P0": 0, "P1": 1, "P2": 2}
    sorted_roasters = sorted(
        issues_by_roaster.items(),
        key=lambda x: (priority_order[priority_map[x[0]]], x[0]),
    )

    return [(r, priority_map[r], ", ".join(sorted(issues))) for r, issues in sorted_roasters]


def render_priority_table(checklist: list[tuple[str, str, str]]) -> Table:
    table = Table(title="Priority Checklist", title_style="bold white", header_style="bold")
    table.add_column("Priority", justify="center")
    table.add_column("Roaster", style="cyan")
    table.add_column("Issues", style="white")
    style_map = {"P0": "red", "P1": "yellow", "P2": "blue"}
    for roaster, priority, issues in checklist:
        table.add_row(
            f"[{style_map[priority]}]{priority}[/{style_map[priority]}]",
            roaster,
            issues,
        )
    return table


def main() -> None:
    if not DB_PATH.exists():
        console.print(f"[red]Database not found:[/red] {DB_PATH}")
        raise SystemExit(1)

    console.print(
        Panel.fit(
            f"[bold]Scraping Issue Analysis[/bold]\n"
            f"Database: [cyan]{DB_PATH.name}[/cyan]\n"
            f"Thresholds: stale>{STALE_DAYS}d | dupes>{DUPE_PCT_THRESHOLD}% | missing>{MISSING_PCT_THRESHOLD}%",
            border_style="blue",
        )
    )

    conn = get_conn()
    try:
        console.print("\n[bold]Analyzing database...[/bold]\n")

        stale = find_stale_roasters(conn)
        spa = find_spa_roasters(conn)
        dupes = find_duplicate_roasters(conn)
        all_oos = find_all_oos_roasters(conn)
        missing = find_missing_data_roasters(conn)

        # Render category tables
        if stale:
            console.print(render_stale_table(stale))
        if spa:
            console.print(render_spa_table(spa))
        if dupes:
            console.print(render_dupe_table(dupes))
        if all_oos:
            console.print(render_oos_table(all_oos))
        if missing:
            console.print(render_missing_table(missing))

        # Build and render priority checklist
        checklist = build_priority_checklist(stale, spa, dupes, all_oos, missing)
        if checklist:
            console.print()
            console.print(
                Panel(
                    render_priority_table(checklist),
                    title="[bold white]Roasters to Investigate (Priority Order)[/bold white]",
                    border_style="white",
                )
            )

            # Summary counts
            p0 = sum(1 for _, p, _ in checklist if p == "P0")
            p1 = sum(1 for _, p, _ in checklist if p == "P1")
            p2 = sum(1 for _, p, _ in checklist if p == "P2")
            console.print(
                f"\n[bold]Summary:[/bold] {len(checklist)} roasters flagged "
                f"([red]P0: {p0}[/red], [yellow]P1: {p1}[/yellow], [blue]P2: {p2}[/blue])\n"
            )
        else:
            console.print("[green]No roasters flagged with scraping issues![/green]\n")
    finally:
        conn.close()


if __name__ == "__main__":
    main()