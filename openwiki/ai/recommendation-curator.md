---
type: "Reference"
title: "User Recommendation Curator"
description: "Standalone script (scripts/curate_recommendations.py) that builds a per-user taste profile from frontend/local.db, aggregates API recommendations across tasted beans, and curates final picks with a two-stage Gemini pipeline."
---

# User Recommendation Curator

## Overview

`scripts/curate_recommendations.py` is a standalone CLI that produces
personalised coffee recommendations for a Kissaten user. It is a reporting/
analysis tool, not part of the served API: it reads the frontend auth SQLite
database directly, queries the read-only API on `localhost:8000`, and calls
two Gemini agents via PydanticAI.

```bash
uv run python scripts/curate_recommendations.py --email <user@example.org>
uv run python scripts/curate_recommendations.py --email <user@example.org> \
    --roaster-country Japan --budget 40 --picks 2 --exclude-known \
    --guidance "one filter and one omni/espresso bean"
```

## Pipeline

```
frontend/local.db ──► TasteProfile ──► seed pool ──► [flash-lite pruning]
                                                      │ 47 → 15 seeds
                                                      ▼
              recommendations API (5 recs/seed) ──► 75 candidates
                                                      │
                                     filters (country/budget/FX)
                                                      ▼
                                     [gemini-3.8-flash curation]
                                                      ▼
                                       rich-rendered CuratedPicks
```

### 1. User profile (`load_user_profile`)

Reads `frontend/local.db` (better-sqlite3/drizzle schema used by the
frontend auth). Two tables matter:

- `saved_beans` — `bean_url_path` + free-text `notes`
- `tasting_sessions` — JSON `data` blobs with `selectedNotes` (flavour
  frequencies), `mouthfeel`/`basics` (body/texture/acidity/sweetness),
  `brewingNotes` (gear, grind, temps, pour structure), `beanUrlPath` (link
  to the tasted bean), and `updatedAt`

Saved-bean notes are classified by keyword-weighted sentiment
(`classify_sentiment`): strong praise (2 pts) beats mild criticism (1 pt), so
mixed notes like *"a bit sour but overall very tasty"* land positive.
Recipe-only remarks (grind/clicks/pours/temps with no bean criticism) are
bucketed separately as **brew notes** — they describe how the user brews,
not whether the bean is good — and must never veto beans.

Resulting `TasteProfile`:

| Field | Source | Use |
|---|---|---|
| `positive_beans` / `negative_beans` / `brew_notes` / `neutral_beans` | saved_beans + sentiment | seeds / vetoes / brew guidance |
| `session_bean_sentiments` | tasting_sessions linked by `beanUrlPath` (strongest remark per bean) | seeds + LLM context |
| `top_notes`, `mouthfeel` | session `selectedNotes` / `mouthfeel` / `basics` | flavour frequencies in prompt |
| `brewing_habits` | 10 most recent `brewingNotes` verbatim | brew-advice context (ZP6, Orea, temps) |
| `recently_tried` | all session beans by `updatedAt` | recency info (not separately seeded) |

Custom beans (`/custom/...` paths) exist only in the frontend DB and 404 on
the API, so they are excluded from seeding.

### 2. Seed pruning (`gemini-3.5-flash-lite`)

`build_seed_pool` unions positive saved beans and session-linked beans
(negatives and customs excluded) → e.g. 47 seeds. When the pool exceeds
`--keep-seeds` (default 15), a flash-lite agent ranks the pool by the
user's strength of positive preference (enthusiastic praise first, then
alignment with favourite notes/mouthfeel) and the top 15 become the seeds.
Rationale is shown in the report as "Seed-pruning notes". `--keep-seeds 0`
disables pruning.

### 2. Recommendations (`fetch_recommendations`)

Each seed calls
`GET /v1/beans/{roaster}/{bean}/recommendations?limit=5` and the results are
aggregated by summing the engine's `score` and counting appearances.
**Equal weighting per bean**: a saved-note anchor and a session-only bean
each contribute the same 5 recommendations. Only in-stock beans are kept;
explicitly disliked beans are never seeded. Calls are paced (default 2.5 s,
`RECOMMENDATION_REQUEST_DELAY`) and retried with exponential backoff on 5xx.

Hard filters before LLM curation: `--roaster-country` (roaster location via
`/v1/roasters`) and `--budget` (price conversion via `/v1/convert`).

### 3. LLM curation (`gemini-3.8-flash`)

A PydanticAI agent with structured output (`CuratedPicks`) picks the final
N beans and explains each through the user's own logged history. `--guidance`
injects requester instructions that steer the selection but cannot override
profile vetoes.

## Design invariants

### Roaster anonymization (brand-bias prevention)

The curator must judge beans on attributes, not brand fame:

- Every roaster gets a **fresh random 8-hex ref per run** (`roaster-a1b2c3d4`)
- Candidate payloads sent to Gemini **strip roaster name, slug and URL**
- The profile's liked/disliked/session paths are anonymized the same way, so
  "same roaster as a loved bean" survives without revealing the brand
- After selection, picks are mapped back to real `bean_url_path`s and any
  `roaster-<uuid>` (or bare `<uuid>`) refs in the prose are replaced with
  real names via regex + a slug→name map covering profile-only roasters

Note: bean *names* stay visible (needed for profile matching), so a
determined model could infer some roasters — but the brand-fame signal is gone.

### Recipe-vs-bean sentiment split

Brewing remarks ("overextracted on orea with 30 clicks") are about the
user's recipe, not the bean. They live in `brew_notes`/`brewing_habits` and
are explicitly labelled *"NOT bean verdicts"* in the prompt. Mixed notes are
resolved by weighted scoring with bean-level criticism winning ties.

### Proxy pitfall (503 debugging story)

`.env` sets `HTTP_PROXY`/`HTTPS_PROXY` for scraper egress. `load_dotenv()`
plus httpx's default `trust_env=True` tunnels **localhost** API calls through
that proxy, which fails with 407/503 before reaching uvicorn (curl and
non-dotenv clients work — classic red herring; uvicorn's access log shows the
requests never arrive). All API calls here use `trust_env=False`. Never send
localhost Kissaten traffic through the outbound proxy.

## Output

Rich-rendered panels: profile summary header, one card per pick (roaster,
variety/process, roast, notes, converted price, LLM "why", caveat with shop
link), curator notes, and seed-pruning notes. Spinner during each LLM call;
`RichHandler` for logs.

## CLI flags

| Flag | Meaning |
|---|---|
| `--email` (required) | user looked up in `frontend/local.db` |
| `--per-bean` | recommendations fetched per seed (default 5) |
| `--picks` | final curated recommendations (default 2) |
| `--keep-seeds` | prune pool to N most-preferred seeds; 0 disables (default 15) |
| `--roaster-country` | hard filter on roaster location (e.g. `Japan`) |
| `--budget` / `--currency` | max total price, converted via `/v1/convert` (default GBP) |
| `--exclude-known` | drop candidates at roasters already saved by the user |
| `--guidance` | free-text steering for the curator |

## AI model reference

| Stage | Model | Role |
|---|---|---|
| Seed pruning | Gemini 3.5 Flash Lite | rank tasted beans by positive preference, keep top N |
| Final curation | Gemini 3.8 Flash | pick final beans, write justifications/caveats |

Both agents use `thinking_budget=0` and structured Pydantic outputs,
following the conventions in [ai-pipeline.md](ai-pipeline.md).
