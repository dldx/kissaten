#!/usr/bin/env python3
"""Curate personalised coffee recommendations for a Kissaten user.

Pipeline:
  1. Pull a user's data from frontend/local.db (saved beans + tasting sessions)
     and derive a taste profile. No keyword sentiment: the notes stay raw.
  2. Judge the tasted beans with gemini-3.5-flash-lite — it ranks the most
     preferred beans and rejects the ones whose notes read as criticism. The
     survivors seed recommendation calls to the Kissaten API, which are
     aggregated (bounded concurrency, 5 in flight).
  3. Ask gemini-3.8-flash (via pydantic-ai) to curate the final picks.

Usage:
  uv run python scripts/curate_recommendations.py --email durand@dldx.org
  uv run python scripts/curate_recommendations.py --email durand@dldx.org \
      --roaster-country Japan --origin Kenya,Ethiopia --budget 40 --picks 2 --exclude-known
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sqlite3
import sys
import uuid
from collections import Counter, defaultdict
from pathlib import Path

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModelSettings
from pydantic_ai.usage import RunUsage

load_dotenv()

logger = logging.getLogger("curate_recommendations")

DB_PATH = Path("frontend/local.db")
API_BASE = os.getenv("KISSATEN_API_BASE", "http://localhost:8000")
GEMINI_MODEL = "gemini-3.5-flash-lite"

# Cap on simultaneous in-flight API requests (recommendations, conversions).
MAX_CONCURRENT_REQUESTS = 5

# Gemini list prices (paid tier, global), USD per 1M tokens:
# model -> {input, cached_input, output}. gemini-3.8-flash is on intro
# pricing through Dec 31 2026 (doubles to 1.50/0.15/7.50 on Jan 1 2027).
# Sources: ai.google.dev/gemini-api/docs/pricing, cloud.google.com pricing.
GEMINI_PRICES: dict[str, dict[str, float]] = {
    GEMINI_MODEL: {"input": 0.75, "cached_input": 0.075, "output": 3.75},
    "gemini-3.5-flash-lite": {"input": 0.30, "cached_input": 0.03, "output": 2.50},
}

# Every LLM call made this run: (model name, token usage).
_llm_usage: list[tuple[str, RunUsage]] = []


def _record_usage(model: str, usage: RunUsage) -> None:
    """Remember one LLM call's token usage for the end-of-run cost report."""
    _llm_usage.append((model, usage))


def _estimate_cost(model: str, usage: RunUsage) -> float | None:
    """Estimated USD cost of one run; None if the model isn't in the price table.

    Cached tokens are billed at the cached_input rate and are assumed to be a
    subset of input_tokens (OpenAI-style accounting), so they're subtracted
    from the full-rate bucket.
    """
    prices = GEMINI_PRICES.get(model)
    if not prices:
        return None
    cached = usage.cache_read_tokens or 0
    fresh_input = max((usage.input_tokens or 0) - cached, 0)
    return (
        fresh_input * prices["input"]
        + cached * prices["cached_input"]
        + (usage.output_tokens or 0) * prices["output"]
    ) / 1_000_000


def render_cost_report() -> None:
    """Print per-model token totals and estimated cost for the whole run."""
    from rich.console import Console
    from rich.table import Table

    if not _llm_usage:
        return

    per_model: dict[str, RunUsage] = {}
    for model, usage in _llm_usage:
        agg = per_model.setdefault(model, RunUsage())
        agg.incr(usage)

    console = Console()
    table = Table(title="LLM usage & estimated cost", border_style="dim", show_lines=False)
    table.add_column("Model", style="cyan")
    table.add_column("Calls", justify="right")
    table.add_column("Input tok", justify="right")
    table.add_column("Cached tok", justify="right")
    table.add_column("Output tok", justify="right")
    table.add_column("Est. cost (USD)", justify="right", style="yellow")

    total_cost = 0.0
    all_priced = True
    for model, usage in per_model.items():
        cost = _estimate_cost(model, usage)
        total_cost += cost or 0.0
        all_priced &= cost is not None
        table.add_row(
            model,
            str(usage.requests or len([1 for m, _ in _llm_usage if m == model])),
            f"{usage.input_tokens or 0:,}",
            f"{usage.cache_read_tokens or 0:,}",
            f"{usage.output_tokens or 0:,}",
            f"${cost:.4f}" if cost is not None else "n/a",
        )

    if len(per_model) > 1 or all_priced:
        table.add_section()
        table.add_row(
            "Total", "", "", "",
            f"{sum(u.output_tokens or 0 for _, u in _llm_usage):,}",
            f"${total_cost:.4f}" if all_priced else "partial",
            style="bold",
        )
    console.print(table)
    if not all_priced:
        console.print("[dim]Unknown models have no entry in GEMINI_PRICES — add prices there for exact totals.[/dim]")

# --------------------------------------------------------------------------
# Step 1: user data from frontend/local.db
# --------------------------------------------------------------------------
# Sentiment is NOT inferred from keywords anywhere in this script. Every note
# (saved note or session remark) is handed to the seed judge (select_seeds),
# which returns both the beans with the strongest positive preference and the
# beans whose notes read as criticism. Those verdicts drive seed selection and
# the profile summary; see TasteProfile.verdicts.

class TasteProfile(BaseModel):
    user_id: str
    email: str
    tasted_beans: list[dict]         # [{path, note, source}] — saved notes + session remarks
    top_notes: list[tuple[str, int]]
    mouthfeel: dict
    brewing_habits: list[str] = []   # recent brewingNotes verbatim
    recently_tried: list[dict] = []  # last-tasted beans, newest first [{path, note, updatedAt}]
    # path -> "liked" / "excluded": the seed judge's verdicts, filled in after
    # select_seeds runs. Empty until then, which is fine — nothing depends on
    # sentiment keywords any more.
    verdicts: dict[str, str] = {}

    def summary(self, roaster_anonymizer=None) -> str:
        def ref(b: dict) -> str:
            path = b["path"]
            if roaster_anonymizer:
                roaster, _, bean = path.strip("/").partition("/")
                path = f"{roaster_anonymizer(roaster)}/{bean}"
            note = (b.get("note") or "").strip()
            return f"{path} ({note[:60]})" if note else path

        liked = [b for b in self.tasted_beans if self.verdicts.get(b["path"]) == "liked"]
        rejected = [b for b in self.tasted_beans if self.verdicts.get(b["path"]) == "excluded"]
        unjudged = [b for b in self.tasted_beans if b["path"] not in self.verdicts]
        habits = "; ".join(self.brewing_habits[:8])
        notes = ", ".join(f"{n}({c})" for n, c in self.top_notes[:10])
        brewing_line = (
            "Recent brewing habits verbatim (gear, grind, temps, pours — recipe remarks, "
            f"NOT bean verdicts): {habits or 'none recorded'}"
        )
        lines = [
            f"Tasting-note frequency (all sessions): {notes}",
            f"Mouthfeel preference: {self.mouthfeel}",
            brewing_line,
        ]
        if self.verdicts:
            lines.append(
                "Favourite beans (taste judge, strongest preference first): "
                + (", ".join(ref(b) for b in liked[:12]) or "none recorded")
            )
            lines.append(
                "Rejected beans (taste judge: negative or unenthusiastic evidence — never recommend anything similar): "
                + (", ".join(ref(b) for b in rejected[:8]) or "none recorded")
            )
        others = unjudged if self.verdicts else self.tasted_beans
        lines.append(
            "Other beans they have tasted, with their own notes: "
            + (", ".join(ref(b) for b in others[:12]) or "none recorded")
        )
        return "\n".join(lines)


def load_user_profile(email: str, db_path: Path = DB_PATH) -> TasteProfile:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    row = cur.execute("SELECT id, email FROM user WHERE email = ?", (email,)).fetchone()
    if not row:
        sys.exit(f"User {email!r} not found in {db_path}")
    uid = row["id"]

    saved_notes: dict[str, str] = {}
    for r in cur.execute(
        "SELECT bean_url_path, notes FROM saved_beans WHERE user_id = ?", (uid,)
    ).fetchall():
        path = r["bean_url_path"]
        if path and not path.startswith("/custom"):
            saved_notes.setdefault(path, (r["notes"] or "").strip())

    note_freq: Counter = Counter()
    mouthfeel = defaultdict(Counter)
    session_remarks: dict[str, dict] = {}           # path -> most recent session remark
    recently_tried: list[dict] = []                 # all tasted beans, recency-sorted later
    brewing_habits: list[tuple[int, str]] = []      # (updatedAt, brewingNotes)
    for r in cur.execute(
        "SELECT data FROM tasting_sessions WHERE user_id = ? AND deleted_at IS NULL",
        (uid,),
    ).fetchall():
        data = json.loads(r["data"])
        for n in data.get("selectedNotes") or []:
            note_freq[n] += 1
        for group in ("mouthfeel", "basics"):
            for k, v in (data.get(group) or {}).items():
                mouthfeel[f"{group}.{k}"][v] += 1

        # Track tasting recency (any session with a resolvable bean path)
        if data.get("beanUrlPath"):
            recently_tried.append({
                "path": data["beanUrlPath"],
                "note": (data.get("brewingNotes") or "")[:100],
                "updatedAt": data.get("updatedAt") or 0,
            })

        # Link sessions to beans, keeping the most recent remark. Whether it
        # reads as praise or criticism is the taste judge's call, not ours.
        path = data.get("beanUrlPath")
        remark = (data.get("brewingNotes") or "").strip()
        updated = data.get("updatedAt") or 0
        if path and remark and not path.startswith("/custom"):
            prev = session_remarks.get(path)
            if prev is None or updated >= prev["updatedAt"]:
                session_remarks[path] = {"path": path, "note": remark, "updatedAt": updated}
        if remark:
            brewing_habits.append((updated, remark[:120]))

    conn.close()
    brewing_habits.sort(key=lambda x: x[0], reverse=True)   # most recent first
    recently_tried.sort(key=lambda x: x["updatedAt"], reverse=True)
    recently_tried = [b for b in recently_tried if not b["path"].startswith("/custom")]

    # Every tasted bean, one entry each. A deliberate saved note outranks the
    # session remark when both exist.
    tasted_beans: list[dict] = [
        {"path": p, "note": note, "source": "saved_note"} for p, note in saved_notes.items()
    ]
    seen = set(saved_notes)
    tasted_beans += [
        {"path": p, "note": rem["note"], "source": "tasting_session"}
        for p, rem in session_remarks.items()
        if p not in seen
    ]

    return TasteProfile(
        user_id=uid,
        email=email,
        tasted_beans=tasted_beans,
        top_notes=note_freq.most_common(),
        mouthfeel={k: v.most_common(1)[0][0] for k, v in mouthfeel.items()},
        brewing_habits=[b for _, b in brewing_habits[:10]],
        recently_tried=recently_tried,
    )


# --------------------------------------------------------------------------
# Step 2: recommendations from the Kissaten API
# --------------------------------------------------------------------------

async def _get_with_retry(
    client: httpx.AsyncClient, sem: asyncio.Semaphore, url: str, params: dict,
    retries: int = 5, backoff: float = 5.0,
) -> httpx.Response:
    """GET with exponential backoff on transient 5xx errors.

    The semaphore is only held for the request itself, so a backing-off
    caller does not consume a concurrency slot.
    """
    last_err: httpx.HTTPError | None = None
    for attempt in range(retries):
        try:
            async with sem:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp
        except httpx.HTTPStatusError as e:
            if e.response.status_code < 500:
                raise  # 4xx: don't retry
            last_err = e
        except httpx.HTTPError as e:
            last_err = e
        await asyncio.sleep(backoff * (2 ** attempt))
    raise last_err


async def _fetch_recommendations_async(
    profile: TasteProfile,
    per_bean: int = 5,
    seed_pool: list[dict] | None = None,
    api_filters: dict | None = None,
    max_concurrency: int = MAX_CONCURRENT_REQUESTS,
) -> list[dict]:
    """Aggregate recommendations across the user's tasting history with
    EQUAL weighting per bean.

    A bean qualifies as a seed if the user has tasted it: saved-note beans and
    session-linked beans carry the same vote, `per_bean` recommendations each.
    Sentiment is not inferred here from keywords — the taste judge (see
    select_seeds) supplies the vetoes, and only its `excluded` verdicts are
    withheld from seeding.

    /custom/ beans are excluded (not resolvable in the API).

    If `seed_pool` is given, it replaces the derived seed list (used after
    LLM seed judging); entries still get de-duplicated and capped.

    `api_filters` is passed through as extra query params on every
    recommendations call (e.g. {"roaster_location": "Japan", "origin": ["KE"]})
    so constraints are applied server-side before candidates are fetched.
    """
    scores: dict[str, dict] = defaultdict(lambda: {"score": 0.0, "count": 0})

    if seed_pool is not None:
        seeds = [(b, per_bean) for b in seed_pool]
    else:
        # Every tasted bean seeds recommendations; only the taste judge's
        # rejections are withheld (populated when judging runs).
        rejected = {p for p, v in profile.verdicts.items() if v == "excluded"}
        seeds = [
            (b, per_bean)
            for b in profile.tasted_beans
            if b["path"] not in rejected and not b["path"].startswith("/custom")
        ]
    approved = sum(1 for b, _ in seeds if profile.verdicts.get(b["path"]) == "liked")
    logger.info("Seeding recommendations from %d beans (%d taste-judge approved + %d unjudged, equal weight)",
                len(seeds), approved, len(seeds) - approved)

    sem = asyncio.Semaphore(max_concurrency)

    async def fetch_one(client: httpx.AsyncClient, bean: dict, limit: int) -> None:
        roaster, slug = bean["path"].strip("/").split("/", 1)
        try:
            resp = await _get_with_retry(
                client,
                sem,
                f"/v1/beans/{roaster}/{slug}/recommendations",
                {"limit": limit, **(api_filters or {})},
            )
        except httpx.HTTPError as e:
            logger.warning("recommendations failed for %s: %s", bean["path"], e)
            return

        # Pure-CPU scoring below: no awaits, so mutating the shared `scores`
        # dict here is safe under single-threaded asyncio.
        for rec in resp.json().get("data") or []:
            path = rec.get("bean_url_path") or ""
            if not rec.get("in_stock"):
                continue
            entry = scores[path]
            entry["score"] += rec.get("score") or 0
            entry["count"] += 1
            entry["bean"] = _slim_bean(rec)

    async with httpx.AsyncClient(base_url=API_BASE, timeout=30, trust_env=False) as client:
        await asyncio.gather(*(fetch_one(client, bean, limit) for bean, limit in seeds))

    ranked = sorted(scores.values(), key=lambda e: (-e["score"], -e["count"]))
    return [e["bean"] | {"rec_score": round(e["score"], 2), "rec_count": e["count"]} for e in ranked]


def fetch_recommendations(
    profile: TasteProfile,
    per_bean: int = 5,
    seed_pool: list[dict] | None = None,
    api_filters: dict | None = None,
) -> list[dict]:
    """Sync entry point: fetch recommendations with bounded concurrency."""
    return asyncio.run(
        _fetch_recommendations_async(profile, per_bean=per_bean, seed_pool=seed_pool, api_filters=api_filters)
    )


def _slim_bean(rec: dict) -> dict:
    """Keep only the fields needed for filtering and LLM curation."""
    origins = rec.get("origins") or [{}]
    o = origins[0] if origins else {}
    return {
        "path": rec.get("bean_url_path"),
        "name": rec.get("name"),
        "roaster": rec.get("roaster"),
        "roaster_slug": (rec.get("bean_url_path") or "").split("/")[1] if rec.get("bean_url_path") else None,
        "country": o.get("country_full_name"),
        "variety": o.get("variety"),
        "process": o.get("process"),
        "tasting_notes": [n["note"] if isinstance(n, dict) else n for n in (rec.get("tasting_notes") or [])],
        "roast_level": rec.get("roast_level"),
        "roast_profile": rec.get("roast_profile"),
        "price": rec.get("price"),
        "currency": rec.get("currency"),
        "weight_g": rec.get("weight"),
        "is_decaf": rec.get("is_decaf"),
        "url": rec.get("url"),
    }


def filter_candidates(
    candidates: list[dict],
    budget: float | None = None,
    currency: str = "GBP",
) -> list[dict]:
    """Apply hard filters (price budget) before LLM curation.

    Roaster-location and origin filtering happen server-side via the
    recommendations endpoint's shared search filters (see api_filters).
    """
    out = candidates
    if budget is not None:
        converted = asyncio.run(_convert_all_prices(out, currency))
        out = [c for c in out if (p := converted.get(c["path"])) is not None and p <= budget]
        for c in out:
            c["price_converted"] = converted.get(c["path"])
    return out


def _roaster_names(slugs: list[str]) -> dict[str, str]:
    """Resolve roaster slugs to display names via the API."""
    try:
        resp = httpx.get(f"{API_BASE}/v1/roasters", timeout=30, trust_env=False)
        resp.raise_for_status()
        return {r["slug"]: r.get("name") or r["slug"] for r in resp.json().get("data", []) if r["slug"] in slugs}
    except httpx.HTTPError as e:
        logger.warning("could not fetch roaster names: %s", e)
        return {}


def resolve_location_code(value: str) -> str:
    """Resolve a roaster location name/code to a canonical location code.

    The API's roaster_location filter matches location codes (e.g. 'JP');
    names like 'Japan' are matched case-insensitively against
    /v1/roaster-locations. Unknown values are passed through as-is.
    """
    v = value.strip()
    if not v:
        return v
    if len(v) == 2 and v.isalpha():
        return v.upper()
    try:
        resp = httpx.get(f"{API_BASE}/v1/roaster-locations", timeout=30, trust_env=False)
        resp.raise_for_status()
        locations = resp.json().get("data", [])
    except httpx.HTTPError as e:
        logger.warning("could not fetch roaster locations: %s", e)
        return v
    for loc in locations:
        if (loc.get("location") or "").lower() == v.lower() or (loc.get("code") or "").upper() == v.upper():
            return loc["code"]
    logger.warning("roaster location %r not found — passing through as-is", v)
    return v


def resolve_origin_codes(values: list[str]) -> list[str]:
    """Resolve origin country names/ISO codes to alpha-2 codes via the API.

    The recommendations endpoint's origin filter matches `origins.country`,
    which stores alpha-2 codes, so 'Kenya,Ethiopia' must become ['KE', 'ET'].
    """
    values = [v for v in (v.strip() for v in values) if v]
    if not values:
        return []
    if all(len(v) == 2 and v.isalpha() for v in values):
        return [v.upper() for v in values]
    try:
        resp = httpx.get(f"{API_BASE}/v1/country-codes", timeout=30, trust_env=False)
        resp.raise_for_status()
        codes = resp.json().get("data", [])
    except httpx.HTTPError as e:
        logger.warning("could not fetch country codes: %s", e)
        return [v.upper() for v in values]
    lookup: dict[str, str] = {}
    for c in codes:
        for key in (c.get("name"), c.get("alpha_3")):
            if key:
                lookup[key.lower()] = c["alpha_2"]
    resolved = []
    for v in values:
        if len(v) == 2 and v.isalpha():
            resolved.append(v.upper())
        elif v.lower() in lookup:
            resolved.append(lookup[v.lower()])
        else:
            logger.warning("origin %r not found in country codes — passing through as-is", v)
            resolved.append(v.upper())
    return resolved


async def _convert_all_prices(
    beans: list[dict], currency: str, max_concurrency: int = MAX_CONCURRENT_REQUESTS,
) -> dict[str, float | None]:
    """Convert a batch of bean prices via the API's /v1/convert endpoint.

    Runs with bounded concurrency (semaphore) and returns path -> converted
    price, with None for beans that have no price or failed conversion.
    """
    sem = asyncio.Semaphore(max_concurrency)

    async def convert_one(client: httpx.AsyncClient, bean: dict) -> tuple[str, float | None]:
        if not bean.get("price") or not bean.get("currency"):
            return bean["path"], None
        try:
            async with sem:
                resp = await client.get(
                    "/v1/convert",
                    params={"amount": bean["price"], "from_currency": bean["currency"], "to_currency": currency},
                )
                resp.raise_for_status()
            data = resp.json().get("data") or {}
            return bean["path"], float(data.get("converted_amount"))
        except (httpx.HTTPError, TypeError, ValueError) as e:
            logger.warning("conversion failed for %s: %s", bean["path"], e)
            return bean["path"], None

    async with httpx.AsyncClient(base_url=API_BASE, timeout=15, trust_env=False) as client:
        return dict(await asyncio.gather(*(convert_one(client, b) for b in beans)))


# --------------------------------------------------------------------------
# Step 2.5: tasting-note judging / seed selection with gemini-3.5-flash-lite
# --------------------------------------------------------------------------

class SelectedSeeds(BaseModel):
    selected_ids: list[str] = Field(description="ids of the selected beans, in order of strongest positive preference")
    excluded_ids: list[str] = Field(
        default_factory=list,
        description=(
            "ids of beans whose notes carry negative or clearly unenthusiastic evidence; "
            "these are vetoed as seeds"
        ),
    )
    selection_rationale: str = Field(description="Brief notes on why these beans best represent the user's positive preferences")


def build_seed_pool(profile: TasteProfile) -> list[dict]:
    """Every bean the user has tasted (saved note or session remark).

    No keyword sentiment filtering: the seed judge reads the notes and returns
    its rejections as `excluded_ids`, which are then dropped from the pool.
    """
    return list(profile.tasted_beans)


def build_seed_selector_agent() -> Agent:
    if not os.getenv("GOOGLE_API_KEY"):
        sys.exit("Google API key required. Set GOOGLE_API_KEY in the environment or .env")
    return Agent(
        "gemini-3.5-flash-lite",
        output_type=SelectedSeeds,
        system_prompt=(
            "You are a coffee-taste analyst. Given a user's taste profile and a list "
            "of beans they have tasted (with the notes they left), judge each bean "
            "from the evidence in its note. Rules:\n"
            "- Roaster identities are anonymized as random refs; judge only on the evidence given.\n"
            "- Strong praise (e.g. 'amazing', 'super tasty', repeated enjoyment) ranks highest.\n"
            "- Beans whose notes align with the user's favourite flavour notes and "
            "mouthfeel rank next.\n"
            "- Put every bean whose note carries negative or clearly unenthusiastic "
            "evidence in excluded_ids; those are vetoed and never seed recommendations.\n"
            "- Brew/recipe remarks (grind, temps, ratio, pours) are neutral: they say "
            "nothing about whether the bean was enjoyed, so never reject a bean for them.\n"
            "- Return exactly the requested number of selected ids, ranked by preference "
            "strength, plus every rejected bean id in excluded_ids."
        ),
        model_settings=GeminiModelSettings(gemini_thinking_config={"thinking_budget": 0}),
    )


async def select_seeds(
    agent: Agent,
    profile: TasteProfile,
    pool: list[dict],
    keep: int = 15,
    guidance: str | None = None,
) -> tuple[list[dict], list[dict], str, dict[str, str]]:
    """Ask gemini-3.5-flash-lite to judge the user's notes on every tasted bean.

    The model both ranks the `keep` most-preferred beans and reports the beans
    whose notes read as criticism (`excluded_ids`), so it is the single source
    of taste sentiment — no keyword heuristics. If a bean is somehow returned
    in both lists, the rejection wins (safer veto).

    If `guidance` is given, the judge biases its preference ranking toward
    beans relevant to that direction, so the surviving seed pool produces
    recommendations that match the requester's intent.

    Returns (selected entries, rejected entries, rationale, roaster uuid->name map).
    Roaster refs are anonymized during judging to avoid brand bias.
    """
    roaster_ids: dict[str, str] = {}

    def rid(path: str) -> str:
        slug = path.strip("/").split("/")[0]
        if slug not in roaster_ids:
            roaster_ids[slug] = uuid.uuid4().hex[:8]
        return f"roaster-{roaster_ids[slug]}"

    def anon(b: dict) -> str:
        return f"{rid(b['path'])}/{b['path'].strip('/').split('/', 1)[1]}"

    anon_pool = []
    pool_by_id: dict[str, dict] = {}
    for b in pool:
        sid = uuid.uuid4().hex[:8]
        anon_pool.append({
            "id": sid,
            "bean_ref": anon(b),
            "source": b["source"],
            "note": (b.get("note") or "").strip() or "(no note left)",
        })
        pool_by_id[sid] = b   # anon id -> real pool entry

    guidance_block = (
        "Additional guidance from the requester: when ranking preference strength, "
        "weight beans that fit this direction higher, so the selected seeds lead to "
        "relevant recommendations (the user's logged dislikes still veto):\n"
        f"{guidance}"
        if guidance
        else ""
    )

    prompt = f"""User taste profile:
{profile.summary(roaster_anonymizer=rid)}

Beans the user has tasted (evidence = their own notes for that bean):
{json.dumps(anon_pool, indent=1, default=str)}

{guidance_block}
Select exactly {keep} beans the user has the HIGHEST positive preference for,
ranked strongest first, and list every bean with negative or unenthusiastic
evidence in excluded_ids. Return their ids.
"""
    result = await agent.run(prompt)
    _record_usage("gemini-3.5-flash-lite", result.usage)
    rejected_ids = {i for i in result.output.excluded_ids if i in pool_by_id}
    overlaps = rejected_ids & set(result.output.selected_ids)
    if overlaps:
        logger.warning("taste judge both selected and rejected %d bean(s): %s — treating as rejected",
                       len(overlaps), ", ".join(sorted(overlaps)))
    selected = [pool_by_id[i] for i in result.output.selected_ids if i in pool_by_id and i not in rejected_ids]
    rejected = [pool_by_id[i] for i in rejected_ids]
    if len(selected) < keep:
        logger.warning("seed selector returned only %d of %d requested beans", len(selected), keep)
    return selected, rejected, result.output.selection_rationale, roaster_ids


# --------------------------------------------------------------------------
# Step 3: LLM curation with gemini-3.8-flash
# --------------------------------------------------------------------------

class CuratedPick(BaseModel):
    bean_id: str = Field(description="the 'id' of the chosen coffee, exactly as given in the candidates")
    title: str = Field(description="Short catchy title for the recommendation")
    why: str = Field(description="2-3 sentences tying this bean to the user's likes, notes and dislikes")
    caveat: str | None = Field(default=None, description="Any honest caveat (price, roast profile, flavour risk)")


class CuratedPicks(BaseModel):
    picks: list[CuratedPick]
    profile_summary: str = Field(description="One-sentence summary of the user's taste profile")
    reasoning_notes: str = Field(description="Brief notes on how candidates were narrowed down")


def build_curator_agent() -> Agent:
    if not os.getenv("GOOGLE_API_KEY"):
        sys.exit("Google API key required. Set GOOGLE_API_KEY in the environment or .env")
    return Agent(
        GEMINI_MODEL,
        output_type=CuratedPicks,
        system_prompt=(
            "You are a specialty-coffee buyer's assistant for the Kissaten app. "
            "Given a user's taste profile and a ranked list of candidate coffees "
            "(with similarity scores from a recommendation engine), curate the "
            "final couple of recommendations. Rules:\n"
            "- Roaster identities are anonymized as random refs (e.g. roaster-a1b2c3d4) to prevent brand-popularity bias. "
            "Judge beans purely on their logged attributes; never guess or invent real roaster names.\n"
            "- Only recommend beans present in the candidate list, by their exact bean_url_path.\n"
            "- Treat the user's disliked flavour patterns (artificial/flavoured ferments) as hard vetoes.\n"
            "- If a budget is given, the total price of the picks must not exceed it.\n"
            "- Prefer diversity across picks (e.g. one filter and one omni/espresso) when possible.\n"
            "- Explain each pick through the user's own logged notes and preferences."
        ),
        model_settings=GeminiModelSettings(gemini_thinking_config={"thinking_budget": 0}),
    )


async def curate(
    agent: Agent,
    profile: TasteProfile,
    candidates: list[dict],
    picks: int = 2,
    budget: float | None = None,
    currency: str = "GBP",
    guidance: str | None = None,
) -> CuratedPicks:
    budget_line = (
        f"The combined price must not exceed {budget} {currency}." if budget else "No budget constraint."
    )
    guidance_block = (
        "Additional guidance from the requester (follow it, but hard vetoes from the profile still win):\n"
        f"{guidance}"
        if guidance
        else ""
    )

    # Anonymize roaster identities (fresh random ids per run) so the model
    # cannot be swayed by brand fame; consistent per roaster so 'same roaster
    # as a loved bean' signal survives without revealing which brand it is.
    roaster_ids: dict[str, str] = {}

    def rid(slug: str | None) -> str:
        slug = slug or "unknown"
        if slug not in roaster_ids:
            roaster_ids[slug] = uuid.uuid4().hex[:8]
        return roaster_ids[slug]

    anon_candidates = []
    bean_by_id: dict[str, dict] = {}
    for c in candidates[:30]:
        cid = uuid.uuid4().hex[:8]
        bean_by_id[cid] = c
        anon_candidates.append({
            "id": cid,
            "roaster_ref": f"roaster-{rid(c.get('roaster_slug'))}",
            "name": c.get("name"),
            "country": c.get("country"),
            "variety": c.get("variety"),
            "process": c.get("process"),
            "tasting_notes": c.get("tasting_notes"),
            "roast_level": c.get("roast_level"),
            "roast_profile": c.get("roast_profile"),
            "price": c.get("price"),
            "currency": c.get("currency"),
            "weight_g": c.get("weight_g"),
            "is_decaf": c.get("is_decaf"),
            "rec_score": c.get("rec_score"),
            "rec_count": c.get("rec_count"),
        })

    prompt = f"""User taste profile:
{profile.summary(roaster_anonymizer=lambda slug: f"roaster-{rid(slug)}")}

Candidate coffees (ranked by aggregate recommendation score, in stock; roaster identities anonymized):
{json.dumps(anon_candidates, indent=1, default=str)}

Curate exactly {picks} recommendation(s).
{budget_line}
{guidance_block}
"""
    result = await agent.run(prompt)
    _record_usage(GEMINI_MODEL, result.usage)
    return result.output, bean_by_id, roaster_ids


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def render_report(
    email: str,
    result: CuratedPicks,
    candidates: list[dict],
    currency: str = "GBP",
    seed_rationale: str | None = None,
) -> None:
    """Render the final recommendations with rich."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.padding import Padding
    from rich.table import Table
    from rich.text import Text

    console = Console()

    console.print(Panel(
        f"[bold]{result.profile_summary}[/bold]",
        title=f"☕ Coffee recommendations for [cyan]{email}[/cyan]",
        subtitle=f"{len(result.picks)} curated pick(s)",
        border_style="magenta",
    ))

    for i, pick in enumerate(result.picks, 1):
        bag = next((c for c in candidates if c["path"] == pick.bean_id), {})

        roast = bag.get("roast_level") or bag.get("roast_profile") or "—"
        price = bag.get("price_converted") or bag.get("price") or "?"
        cur = currency if bag.get("price_converted") else (bag.get("currency") or "")
        weight = bag.get("weight_g") or "?"
        notes = ", ".join(bag.get("tasting_notes", [])[:6]) or "—"

        detail = Table.grid(padding=(0, 2))
        detail.add_column(style="dim", justify="right")
        detail.add_column(style="white")
        detail.add_row("Roaster", f"[cyan]{bag.get('roaster', '—')}[/cyan] ({bag.get('country', '—')})")
        detail.add_row("Variety", bag.get("variety") or "—")
        detail.add_row("Process", bag.get("process") or "—")
        detail.add_row("Roast", str(roast))
        detail.add_row("Notes", f"[green]{notes}[/green]")
        detail.add_row("Price", f"[yellow]{price} {cur}[/yellow] / {weight}g")
        detail.add_row("Why", pick.why)
        if pick.caveat:
            detail.add_row("Caveat", f"[orange3]⚠ {pick.caveat}[/orange3]")
        link = bag.get('url') or API_BASE + '/v1/beans/' + pick.bean_id.strip('/')
        detail.add_row("Link", f"[link={link}]{link}[/link]")

        console.print(Padding(
            Panel(detail, title=f"[bold]{i}. {pick.title}[/bold]", border_style="cyan"),
            (1, 0),
        ))

    console.print(Panel(
        Text(result.reasoning_notes),
        title="[dim]Curator notes[/dim]",
        border_style="dim",
    ))
    if seed_rationale:
        console.print(Panel(
            Text(seed_rationale),
            title="[dim]Taste-judge notes (gemini-3.5-flash-lite)[/dim]",
            border_style="dim",
        ))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="User email in frontend/local.db")
    parser.add_argument("--db", default=str(DB_PATH), help="Path to the SQLite DB")
    parser.add_argument("--per-bean", type=int, default=5, help="Recommendations to fetch per favourite bean")
    parser.add_argument("--picks", type=int, default=2, help="Number of curated recommendations")
    parser.add_argument(
        "--roaster-country",
        help="Hard filter: roaster country/location (e.g. 'Japan', 'United Kingdom') — applied server-side",
    )
    parser.add_argument(
        "--origin",
        help=(
            "Hard filter: bean origin countries (comma-separated names or ISO codes, "
            "e.g. 'Kenya,Ethiopia' or 'KE,ET') — applied server-side"
        ),
    )
    parser.add_argument("--budget", type=float, help="Max total price for the picks")
    parser.add_argument("--currency", default="GBP", help="Currency for budget conversion")
    parser.add_argument("--exclude-known", action="store_true", help="Exclude roasters the user already ordered from")
    parser.add_argument(
        "--keep-seeds",
        type=int,
        default=15,
        help=(
            "Judge the tasted beans with gemini-3.5-flash-lite: keep the N most-preferred "
            "beans and veto the rejected ones (0 disables judging, so no bean is vetoed)"
        ),
    )

    parser.add_argument(
        "--guidance",
        help=(
            "Custom prompt steering the curation AND seed judging "
            "(e.g. 'one filter and one omni bean from the same roaster')"
        ),
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")
    from rich.logging import RichHandler
    logging.getLogger().handlers = [RichHandler(rich_tracebacks=True, show_path=False)]

    # 1. user profile
    profile = load_user_profile(args.email, Path(args.db))
    by_source = Counter(b["source"] for b in profile.tasted_beans)
    logger.info(
        "Loaded profile for %s: %d tasted beans (%d saved notes, %d session-linked)",
        args.email, len(profile.tasted_beans),
        by_source.get("saved_note", 0), by_source.get("tasting_session", 0),
    )
    if not profile.tasted_beans:
        sys.exit("No tasted beans found — nothing to anchor recommendations on.")

    # 2. seed judging (optional) then recommendations. Judging is what supplies
    #    the taste verdicts, so it runs whenever there is anything to judge —
    #    including pools smaller than --keep-seeds, where it still vetoes.
    pool = build_seed_pool(profile)
    seed_rationale = None
    if args.keep_seeds and pool:
        from rich.console import Console
        _console = Console()
        selector = build_seed_selector_agent()
        keep = min(args.keep_seeds, len(pool))
        with _console.status(f"[magenta]Judging {len(pool)} tasted beans with gemini-3.5-flash-lite…[/magenta]"):
            selected, rejected, seed_rationale, _sel_ids = asyncio.run(
                select_seeds(selector, profile, pool, keep=keep, guidance=args.guidance)
            )
        profile.verdicts = {b["path"]: "liked" for b in selected}
        profile.verdicts.update({b["path"]: "excluded" for b in rejected})
        logger.info(
            "Taste judge: %d approved as seeds, %d vetoed, %d left unjudged "
            "(outside the top %d, neither vetoed nor seeded)",
            len(selected), len(rejected), len(pool) - len(selected) - len(rejected), keep,
        )
        pool = selected
    else:
        logger.info("Seed pool: %d beans (judging disabled — no beans vetoed)", len(pool))

    # Server-side filters (same wire params as /v1/search)
    api_filters: dict = {}
    if args.roaster_country:
        api_filters["roaster_location"] = resolve_location_code(args.roaster_country)
    if args.origin:
        api_filters["origin"] = resolve_origin_codes(args.origin.split(","))
    if api_filters:
        logger.info("Server-side recommendation filters: %s", api_filters)

    candidates = fetch_recommendations(
        profile, per_bean=args.per_bean, seed_pool=pool, api_filters=api_filters,
    )
    logger.info("Aggregated %d in-stock candidate beans", len(candidates))
    candidates = filter_candidates(candidates, args.budget, args.currency)
    logger.info("%d candidates after budget filtering (budget=%s %s)",
                len(candidates), args.budget, args.currency)
    if not candidates:
        sys.exit("No candidates survived filtering — relax --roaster-country, --origin or --budget.")

    # 3. LLM curation
    from rich.console import Console
    from rich.status import Status

    console = Console()
    agent = build_curator_agent()
    with console.status("[magenta]Curating with gemini-3.8-flash…[/magenta]"):
        result, bean_by_id, roaster_ids = asyncio.run(curate(agent, profile, candidates, picks=args.picks, budget=args.budget, currency=args.currency, guidance=args.guidance))

    # De-anonymize: map pick ids back to real beans and replace roaster uuid
    # refs in the LLM prose with real roaster names for display. The model
    # may cite ids bare (e.g. "b96717c4") or prefixed ("roaster-b96717c4"),
    # and may reference profile roasters that are not in the candidate list,
    # so resolve names for every roaster seen this run.
    slug_to_name = {c["roaster_slug"]: c["roaster"] for c in candidates if c.get("roaster_slug") and c.get("roaster")}
    unresolved = [s for s in roaster_ids if s not in slug_to_name]
    if unresolved:
        slug_to_name.update(_roaster_names(unresolved))
    uuid_to_name = {u: slug_to_name[slug] for slug, u in roaster_ids.items() if slug_to_name.get(slug)}

    def deanonymize(text: str | None) -> str | None:
        if not text:
            return text
        for u, name in uuid_to_name.items():
            text = re.sub(rf"\broaster-{u}\b|\b{u}\b", name, text)
        return text

    for pick in result.picks:
        bean = bean_by_id.get(pick.bean_id, {})
        pick.bean_id = bean.get("path", pick.bean_id)   # restore real path
        pick.why = deanonymize(pick.why)
        pick.caveat = deanonymize(pick.caveat)
    result.profile_summary = deanonymize(result.profile_summary) or result.profile_summary
    result.reasoning_notes = deanonymize(result.reasoning_notes) or result.reasoning_notes

    render_report(args.email, result, candidates, currency=args.currency, seed_rationale=seed_rationale)
    render_cost_report()


if __name__ == "__main__":
    main()
