#!/usr/bin/env python3
"""Curate personalised coffee recommendations for a Kissaten user.

Pipeline:
  1. Pull a user's data from frontend/local.db (saved beans + tasting sessions)
     and derive a taste profile with sentiment.
  2. For each positively-rated saved bean, fetch recommendations from the
     Kissaten API and aggregate the results.
  3. Ask gemini-3.8-flash (via pydantic-ai) to curate the final picks.

Usage:
  uv run python scripts/curate_recommendations.py --email durand@dldx.org
  uv run python scripts/curate_recommendations.py --email durand@dldx.org \
      --roaster-country Japan --budget 40 --picks 2 --exclude-known
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
import time
import uuid
from collections import Counter, defaultdict
from pathlib import Path

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModelSettings

load_dotenv()

logger = logging.getLogger("curate_recommendations")

DB_PATH = Path("frontend/local.db")
API_BASE = os.getenv("KISSATEN_API_BASE", "http://localhost:8000")
GEMINI_MODEL = "gemini-3.8-flash"

# Sentiment buckets for saved-bean tasting notes.
# Weighted scoring: strong praise outweighs mild criticism, so mixed notes
# ("a bit sour but overall very tasty") land on the right side.
STRONG_POSITIVE_KEYWORDS = [
    "super tasty", "very tasty", "amazing", "delicious", "love", "super juicy",
]
WEAK_POSITIVE_KEYWORDS = [
    "great", "clean", "juicy", "complex", "fruity", "floral", "sweet",
    "true to", "surprisingly good", "tasty", "very tasty!", "very clear",
    "interesting flavour", "drinkable",
]
# Bean-level criticisms (the coffee itself, not how it was brewed)
STRONG_NEGATIVE_KEYWORDS = [
    "not good", "artificial", "not particularly exciting", "doesn't really taste",
    "not much fruity", "no berry notes", "vinegary", "muted acidity",
]
WEAK_NEGATIVE_KEYWORDS = [
    "boring", "disappointing", "too clean", "a bit sour", "can't taste",
    "cannot taste", "cuts through with milk",
]
# Recipe/extraction remarks — about the user's brewing, NOT a bean verdict
BREW_KEYWORDS = [
    "grind finer", "grind coarser", "clicks", "pours", "brew cooler",
    "brew hotter", "brew to ", "overextract", "underextract", "bloom",
    "ratio", "temperature", "iced", "flat white", "espresso", "cold brew",
    "aeropress", "orea", "v60", "switch", "picolo", "as a ",
]


def classify_sentiment(note: str) -> str:
    """Classify a saved-bean note.

    Returns one of: "positive", "negative", "brew_note", "neutral".
    - Recipe-only remarks (grind/brew advice with no bean criticism) are
      "brew_note" — they say nothing about whether the bean is good.
    - Mixed notes are resolved by weighted scoring, so "a bit sour but
      overall very tasty" counts as positive.
    """
    n = (note or "").lower()
    pos = 2 * sum(k in n for k in STRONG_POSITIVE_KEYWORDS) + sum(k in n for k in WEAK_POSITIVE_KEYWORDS)
    neg = 2 * sum(k in n for k in STRONG_NEGATIVE_KEYWORDS) + sum(k in n for k in WEAK_NEGATIVE_KEYWORDS)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    if pos == 0 and neg == 0 and any(k in n for k in BREW_KEYWORDS):
        return "brew_note"
    if pos == neg and pos > 0:
        # Genuine tie: bean-level criticism is the safer read
        return "negative"
    return "neutral"


# --------------------------------------------------------------------------
# Step 1: user data from frontend/local.db
# --------------------------------------------------------------------------

class TasteProfile(BaseModel):
    user_id: str
    email: str
    positive_beans: list[dict]   # [{path, note}]
    negative_beans: list[dict]   # bean-level dislikes
    brew_notes: list[dict]       # recipe remarks — not bean verdicts
    neutral_beans: list[dict] = []  # tasted/saved without a clear verdict
    top_notes: list[tuple[str, int]]
    mouthfeel: dict
    session_bean_sentiments: list[dict] = []  # from tasting sessions [{path, note}]
    brewing_habits: list[str] = []            # recent brewingNotes verbatim
    recently_tried: list[dict] = []           # last-tasted beans, newest first [{path, note, tasted_at}]

    def summary(self, roaster_anonymizer=None) -> str:
        def ref(b: dict) -> str:
            path = b["path"]
            if roaster_anonymizer:
                roaster, _, bean = path.strip("/").partition("/")
                path = f"{roaster_anonymizer(roaster)}/{bean}"
            return f"{path} ({b['note'][:60]})"

        liked = ", ".join(ref(b) for b in self.positive_beans[:12])
        disliked = ", ".join(ref(b) for b in self.negative_beans[:8])
        brew = ", ".join(ref(b) for b in self.brew_notes[:6])
        sessions = ", ".join(ref(s) for s in self.session_bean_sentiments[:8])
        habits = "; ".join(self.brewing_habits[:8])
        notes = ", ".join(f"{n}({c})" for n, c in self.top_notes[:10])
        return (
            f"Tasting-note frequency (all sessions): {notes}\n"
            f"Mouthfeel preference: {self.mouthfeel}\n"
            f"Beans they LOVED (saved with praise): {liked}\n"
            f"Beans they DISLIKED (bean-level criticism): {disliked or 'none recorded'}\n"
            f"Brewing lessons (recipe adjustments the user logged — NOT bean verdicts, do not use to veto beans): {brew or 'none recorded'}\n"
            f"Tasting-session remarks per bean (live cupping notes with sentiment): {sessions or 'none recorded'}\n"
            f"Recent brewing setup/habits verbatim (gear, grind, temps, pours): {habits or 'none recorded'}"
        )


def load_user_profile(email: str, db_path: Path = DB_PATH) -> TasteProfile:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    row = cur.execute("SELECT id, email FROM user WHERE email = ?", (email,)).fetchone()
    if not row:
        sys.exit(f"User {email!r} not found in {db_path}")
    uid = row["id"]

    positive, negative, brew_notes, neutral = [], [], [], []
    for r in cur.execute(
        "SELECT bean_url_path, notes FROM saved_beans WHERE user_id = ?", (uid,)
    ).fetchall():
        note = r["notes"] or ""
        sentiment = classify_sentiment(note)
        bean = {"path": r["bean_url_path"], "note": note}
        if sentiment == "positive":
            positive.append(bean)
        elif sentiment == "negative":
            negative.append(bean)
        elif sentiment == "brew_note":
            brew_notes.append(bean)
        else:
            neutral.append(bean)

    note_freq: Counter = Counter()
    mouthfeel = defaultdict(Counter)
    session_bean_sentiments: dict[str, dict] = {}   # path -> most informative remark
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

        # Link sessions to beans and keep the most sentiment-bearing remark
        path = data.get("beanUrlPath")
        remark = (data.get("brewingNotes") or "").strip()
        if path and remark:
            existing = session_bean_sentiments.get(path)
            # prefer the remark with the strongest (absolute) signal
            def strength(text: str) -> int:
                t = text.lower()
                return (2 * sum(k in t for k in STRONG_POSITIVE_KEYWORDS) + sum(k in t for k in WEAK_POSITIVE_KEYWORDS)
                        + 2 * sum(k in t for k in STRONG_NEGATIVE_KEYWORDS) + sum(k in t for k in WEAK_NEGATIVE_KEYWORDS))
            if path not in session_bean_sentiments or strength(remark) >= strength(existing["note"]):
                session_bean_sentiments[path] = {"path": path, "note": remark}
        if remark:
            brewing_habits.append((data.get("updatedAt") or 0, remark[:120]))

    conn.close()
    brewing_habits.sort(key=lambda x: x[0], reverse=True)   # most recent first
    recently_tried.sort(key=lambda x: x["updatedAt"], reverse=True)
    recently_tried = [b for b in recently_tried if not b["path"].startswith("/custom")]
    return TasteProfile(
        user_id=uid,
        email=email,
        positive_beans=positive,
        negative_beans=negative,
        brew_notes=brew_notes,
        neutral_beans=neutral,
        top_notes=note_freq.most_common(),
        mouthfeel={k: v.most_common(1)[0][0] for k, v in mouthfeel.items()},
        session_bean_sentiments=list(session_bean_sentiments.values()),
        brewing_habits=[b for _, b in brewing_habits[:10]],
        recently_tried=recently_tried,
    )


# --------------------------------------------------------------------------
# Step 2: recommendations from the Kissaten API
# --------------------------------------------------------------------------

def _get_with_retry(
    client: httpx.Client, url: str, params: dict,
    retries: int = 5, backoff: float = 5.0,
) -> httpx.Response:
    """GET with exponential backoff on transient 5xx errors."""
    last_err: httpx.HTTPError | None = None
    for attempt in range(retries):
        try:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as e:
            if e.response.status_code < 500:
                raise  # 4xx: don't retry
            last_err = e
        except httpx.HTTPError as e:
            last_err = e
        time.sleep(backoff * (2 ** attempt))
    raise last_err


def fetch_recommendations(
    profile: TasteProfile,
    per_bean: int = 5,
    seed_pool: list[dict] | None = None,
) -> list[dict]:
    """Aggregate recommendations across the user's tasting history with
    EQUAL weighting per bean.

    A bean qualifies as a seed if the user has any positive signal for it:
      - a positively-annotated saved bean, OR
      - a tasting session linked to it (selected tasting notes / brew remarks)
    Every qualifying bean contributes the same number of recommendations
    (`per_bean`), regardless of whether its signal comes from a saved note or
    a tasting session — so session-only beans carry the same vote as anchors.

    Excluded from seeding: explicitly disliked beans (their similarity space
    is unwelcome) and /custom/ beans (not resolvable in the API).

    If `seed_pool` is given, it replaces the derived seed list (used after
    LLM seed-pruning); entries still get de-duplicated and capped.
    """
    scores: dict[str, dict] = defaultdict(lambda: {"score": 0.0, "count": 0})
    request_delay = float(os.getenv("RECOMMENDATION_REQUEST_DELAY", "2.5"))

    if seed_pool is not None:
        seeds = [(b, per_bean) for b in seed_pool]
    else:
        # Union of positive saved beans and session-linked beans; one vote each.
        seed_map: dict[str, dict] = {}
        for b in profile.positive_beans:
            seed_map.setdefault(b["path"], b)
        for b in profile.session_bean_sentiments:
            seed_map.setdefault(b["path"], b)
        negative_paths = {b["path"] for b in profile.negative_beans}
        seeds = [
            (b, per_bean)
            for p, b in seed_map.items()
            if p not in negative_paths and not p.startswith("/custom")
        ]
    pos_paths = {b["path"] for b in profile.positive_beans}
    n_pos = sum(1 for b, _ in seeds if b["path"] in pos_paths)
    logger.info("Seeding recommendations from %d beans (%d saved-note anchors + %d session-only, equal weight)",
                len(seeds), n_pos, len(seeds) - n_pos)

    with httpx.Client(base_url=API_BASE, timeout=30, trust_env=False) as client:
        for bean, limit in seeds:
            roaster, slug = bean["path"].strip("/").split("/", 1)
            try:
                resp = _get_with_retry(
                    client,
                    f"/v1/beans/{roaster}/{slug}/recommendations",
                    {"limit": limit},
                )
            except httpx.HTTPError as e:
                logger.warning("recommendations failed for %s: %s", bean["path"], e)
                continue
            finally:
                time.sleep(request_delay)

            for rec in resp.json().get("data") or []:
                path = rec.get("bean_url_path") or ""
                if not rec.get("in_stock"):
                    continue
                entry = scores[path]
                entry["score"] += rec.get("score") or 0
                entry["count"] += 1
                entry["bean"] = _slim_bean(rec)

    ranked = sorted(scores.values(), key=lambda e: (-e["score"], -e["count"]))
    return [e["bean"] | {"rec_score": round(e["score"], 2), "rec_count": e["count"]} for e in ranked]


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
    roaster_country: str | None = None,
    budget: float | None = None,
    currency: str = "GBP",
) -> list[dict]:
    """Apply hard filters (roaster country, price budget) before LLM curation."""
    out = candidates
    if roaster_country:
        slugs = list({c["roaster_slug"] for c in out if c.get("roaster_slug")})
        country_by_slug = _roaster_countries(slugs)
        out = [c for c in out if country_by_slug.get(c["roaster_slug"], "").lower() == roaster_country.lower()]
    if budget is not None:
        converted = {c["path"]: _price_in(c, currency) for c in out}
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


def _roaster_countries(slugs: list[str]) -> dict[str, str]:
    try:
        resp = httpx.get(f"{API_BASE}/v1/roasters", timeout=30, trust_env=False)
        resp.raise_for_status()
        return {r["slug"]: r.get("location") or "" for r in resp.json().get("data", []) if r["slug"] in slugs}
    except httpx.HTTPError as e:
        logger.warning("could not fetch roaster locations: %s", e)
        return {}


def _price_in(bean: dict, currency: str) -> float | None:
    """Convert a bean's price via the API's /v1/convert endpoint."""
    if not bean.get("price") or not bean.get("currency"):
        return None
    try:
        resp = httpx.get(
            f"{API_BASE}/v1/convert", trust_env=False,
            params={"amount": bean["price"], "from_currency": bean["currency"], "to_currency": currency},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("data") or {}
        return float(data.get("converted_amount"))
    except (httpx.HTTPError, TypeError, ValueError) as e:
        logger.warning("conversion failed for %s: %s", bean["path"], e)
        return None


# --------------------------------------------------------------------------
# Step 2.5: seed pruning with gemini-3.5-flash-lite
# --------------------------------------------------------------------------

class SelectedSeeds(BaseModel):
    selected_ids: list[str] = Field(description="ids of the selected beans, in order of strongest positive preference")
    selection_rationale: str = Field(description="Brief notes on why these beans best represent the user's positive preferences")


def build_seed_pool(profile: TasteProfile) -> list[dict]:
    """Every tasted bean with a positive-or-unknown verdict: saved-note beans
    plus session-linked beans. Negatives and custom beans excluded."""
    pool: dict[str, dict] = {}
    for b in profile.positive_beans:
        pool.setdefault(b["path"], {**b, "source": "saved_note"})
    for b in profile.session_bean_sentiments:
        pool.setdefault(b["path"], {**b, "source": "tasting_session"})
    negative_paths = {b["path"] for b in profile.negative_beans}
    return [v for v in pool.values() if v["path"] not in negative_paths and not v["path"].startswith("/custom")]


def build_seed_selector_agent() -> Agent:
    if not os.getenv("GOOGLE_API_KEY"):
        sys.exit("Google API key required. Set GOOGLE_API_KEY in the environment or .env")
    return Agent(
        "gemini-3.5-flash-lite",
        output_type=SelectedSeeds,
        system_prompt=(
            "You are a coffee-taste analyst. Given a user's taste profile and a list "
            "of beans they have tasted (with the notes they left), select the beans "
            "the user has the HIGHEST positive preference for. Rules:\n"
            "- Roaster identities are anonymized as random refs; judge only on the evidence given.\n"
            "- Strong praise (e.g. 'amazing', 'super tasty', repeated enjoyment) ranks highest.\n"
            "- Beans whose tasting-session notes align with the user's favourite flavour "
            "notes and mouthfeel rank next.\n"
            "- Exclude anything with negative or clearly unenthusiastic evidence.\n"
            "- Return exactly the requested number of ids, ranked by preference strength."
        ),
        model_settings=GeminiModelSettings(gemini_thinking_config={"thinking_budget": 0}),
    )


async def select_seeds(
    agent: Agent,
    profile: TasteProfile,
    pool: list[dict],
    keep: int = 15,
) -> tuple[list[dict], str, dict[str, str]]:
    """Ask gemini-3.5-flash-lite to pick the `keep` most-preferred beans.

    Returns (selected pool entries, rationale, roaster uuid->name map).
    Roaster refs are anonymized during selection to avoid brand bias.
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

    prompt = f"""User taste profile:
{profile.summary(roaster_anonymizer=rid)}

Beans the user has tasted (evidence = their own notes for that bean):
{json.dumps(anon_pool, indent=1, default=str)}

Select exactly {keep} beans the user has the HIGHEST positive preference for,
ranked strongest first. Return their ids.
"""
    result = await agent.run(prompt)
    selected = [pool_by_id[i] for i in result.output.selected_ids if i in pool_by_id]
    if len(selected) < keep:
        logger.warning("seed selector returned only %d of %d requested beans", len(selected), keep)
    return selected, result.output.selection_rationale, roaster_ids


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
            title="[dim]Seed-pruning notes (gemini-3.5-flash-lite)[/dim]",
            border_style="dim",
        ))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="User email in frontend/local.db")
    parser.add_argument("--db", default=str(DB_PATH), help="Path to the SQLite DB")
    parser.add_argument("--per-bean", type=int, default=5, help="Recommendations to fetch per favourite bean")
    parser.add_argument("--picks", type=int, default=2, help="Number of curated recommendations")
    parser.add_argument("--roaster-country", help="Hard filter: roaster country (e.g. 'Japan', 'United Kingdom')")
    parser.add_argument("--budget", type=float, help="Max total price for the picks")
    parser.add_argument("--currency", default="GBP", help="Currency for budget conversion")
    parser.add_argument("--exclude-known", action="store_true", help="Exclude roasters the user already ordered from")
    parser.add_argument("--keep-seeds", type=int, default=15, help="Prune the seed pool to the N most-preferred beans via gemini-3.5-flash-lite (0 disables pruning)")

    parser.add_argument("--guidance", help="Custom prompt guiding the LLM curator (e.g. 'one filter and one omni bean from the same roaster')")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")
    from rich.logging import RichHandler
    logging.getLogger().handlers = [RichHandler(rich_tracebacks=True, show_path=False)]

    # 1. user profile
    profile = load_user_profile(args.email, Path(args.db))
    logger.info(
        "Loaded profile for %s: %d liked / %d disliked / %d brew-only notes",
        args.email, len(profile.positive_beans), len(profile.negative_beans), len(profile.brew_notes),
    )
    if not profile.positive_beans:
        sys.exit("No positively-rated saved beans found — nothing to anchor recommendations on.")

    # 2. seed pruning (optional) then recommendations
    pool = build_seed_pool(profile)
    seed_rationale = None
    if args.keep_seeds and len(pool) > args.keep_seeds:
        from rich.console import Console
        from rich.status import Status
        _console = Console()
        selector = build_seed_selector_agent()
        with _console.status(f"[magenta]Pruning {len(pool)} seed beans to {args.keep_seeds} with gemini-3.5-flash-lite…[/magenta]"):
            selected, seed_rationale, _sel_ids = asyncio.run(select_seeds(selector, profile, pool, keep=args.keep_seeds))
        logger.info("Seed pool pruned: %d -> %d beans", len(pool), len(selected))
        pool = selected
    else:
        logger.info("Seed pool: %d beans (no pruning needed)", len(pool))

    candidates = fetch_recommendations(
        profile, per_bean=args.per_bean, seed_pool=pool,
    )
    logger.info("Aggregated %d in-stock candidate beans", len(candidates))
    candidates = filter_candidates(candidates, args.roaster_country, args.budget, args.currency)
    logger.info("%d candidates after filtering (country=%s, budget=%s %s)",
                len(candidates), args.roaster_country, args.budget, args.currency)
    if not candidates:
        sys.exit("No candidates survived filtering — relax --roaster-country or --budget.")

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


if __name__ == "__main__":
    main()
