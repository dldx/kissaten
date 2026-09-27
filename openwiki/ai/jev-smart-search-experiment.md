---
type: "Experiment"
title: "Jev Smart-Search Prototype"
description: "Standalone prototype replacing the Gemini smart-search translator with TypeSafe's Jev System One model (choice/noul/score primitives) plus deterministic regex extraction — with a hybrid split where a general LLM (Gemini) composes the wildcard tasting-note expression — benchmarked field-for-field against the golden examples."
---

# Jev Smart-Search Prototype

## Goal

Prove that the smart-search translator in `src/kissaten/ai/search_agent.py`
(`AISearchAgent.translate_query`, powered by `gemini-2.5-flash-lite`) can be
replaced with TypeSafe's **Jev** System One model while producing the **same
structured output** (`SearchParameters` / `AISearchResponse` / `search_url`).
The prototype is hybrid, not all-Jev: Jev keeps every structured/enumerated
field (origin, variety, roast level, price/weight/elevation gates, sort, …),
while the **wildcard-grammar field `tasting_notes_search` is outsourced back to
Gemini** (`gemini-2.5-flash-lite`, the same model the production agent uses),
because Jev can only pick DB note labels while the golden expects curated
wildcard patterns (`pineapple&coconut`, `fruit*|berry*`, …).

The prototype is intentionally standalone — `scripts/jev_native_prototype.py` +
`tests/unit/test_jev_common.py` only. No existing source file is modified;
existing modules (`AISearchAgent` helpers, `ai_search` schemas) are imported
and reused as-is. The pure/deterministic logic shared between the prototype and
its tests lives in `scripts/jev_common.py`.

## Design: native adapter vs Gemini

| | Gemini (current) | Jev (prototype) |
|---|---|---|
| Interface | Free-form JSON from a PydanticAI structured output agent | Structured primitive questions (`choice` / `noul` / `score`) answered in one batched request via pydantic-ai's TypeSafe adapter |
| Judgment | LLM writes every field, including prices/dates | LLM judges *semantics only* (which roaster/origin/flavour); numbers/weights/elevation are extracted by deterministic regex in Python |
| Reasoning | LLM prose | Deterministic one-liner listing the non-default fields |
| Prompt | ~10 kB system prompt + context sections + 20 examples | ~40 small questions with option criteria |

The Jev request payload for one query is roughly 3.5–5.8 k input tokens (the
country choice alone carries ~79 options); Gemini's prompt is larger. Both are
fast (~0.9 s Jev, see benchmark).

### Hybrid split: Jev for structured/enumerated fields, Gemini for regex fields

The one field Jev structurally cannot get right is the wildcard-grammar
`tasting_notes_search`: Jev can only pick from the DB's stored note labels
("Pinacolada", "Citruses|Citrícos|Citrusy", "Acidity"), while the golden and
the search backend expect curated wildcard expressions ("pineapple&coconut",
"citrus*|lemon*|orange*|tangerine*|lime*", "wine*|acidic*").  So the prototype
runs a **hybrid**: after the Jev run, a second small Gemini agent
(`gemini-2.5-flash-lite`, the same model the production agent uses) composes
the wildcard expression straight from the raw query.  When it returns a
`tasting_notes_search` expression it **overrides** the Jev candidate expression
in `compose_search_params` (`regex_fields=`); when it returns `null` (no
flavour preference) or the LLM is disabled/fails, the Jev candidate path is
used unchanged.  When the regex LLM is enabled, the tasting-note questions are
dropped from the Jev model entirely (`include_tasting_notes=False`), so Jev is
never asked about notes.

**The Jev gate (`needs_tasting_notes`).**  Before Gemini is asked anything, Jev
itself answers one more noul question — `needs_tasting_notes` — deciding whether
the query has any taste intent worth searching tasting notes for.  When Jev says
**no** (e.g. `"Standout ture waji"`, whose only salient words are the roaster
`Standout Coffee AB` and the producer `Ture Waji`, or `"koke violet"`, which
names the Koke producer/washing station + the Violet lot), the regex-field LLM
is **skipped entirely** — no Gemini call, `regex_fields = {}` — and, because the
tasting-note questions were dropped from the model, `compose_search_params`
finds no candidates and emits `tasting_notes_search = None`.  This kills the
false positives Gemini produced on pure product/producer/bean lookups (it
emitted `"turmeric"` for `"Standout ture waji"`, `"idido"` for `"idido"`,
`"yuan yi yan"` for `"something similar to yuan yi yan"`).  The gate field is
present in the Jev model in **both** modes (it is a plain `_FIELD_QUESTIONS`
bool), but it only gates the LLM call: under `--no-regex-llm` it is ignored and
the Jev candidate notes are used as before.

`REGEX_FIELDS = ("tasting_notes_search",)` in the prototype is the **extension
point** for moving other wildcard-capable fields (region, variety, roast_level)
to the regex LLM next.  `compose_search_params` stays pure: it just accepts an
optional `regex_fields` dict and prefers its values when present.

**Regex-LLM output sanitiser.**  `run_regex_fields` runs every emitted value
through `sanitize_regex_value` (in `jev_common.py`) before returning: `None` ->
`None`, non-strings are stringified, whitespace is stripped, and the null-ish /
sentinel strings `""`, `"null"`, `"none"`, `"n/a"`, `"na"`, `"nil"`, `"*"`
(case-insensitive) all become `None`.  The regex LLM occasionally answers with
the literal string `"null"` (observed: `"Moby dick sl9"` -> `tasting_notes_search
"null"` reached the search URL as `tasting_notes_query=null`); the sanitiser
guarantees such values can never reach `compose_search_params`.

### Why hybrid judgment + code

Per the TypeSafe docs guidance, exact numeric/date extraction belongs in
deterministic code and Jev should only make semantic judgments. This makes the
prototype's price/weight/elevation parsing **unit-testable and stable** (no
model can misparse "under £25"), while Jev's noul gates decide *whether* a
bound exists and Jev's choices decide *which* entity the query refers to.

## Architecture

```
scripts/jev_native_prototype.py
├─ Agent('typesafe:jev-latest', output_type=<per-query pydantic model>)
│    ONE request, ~45 questions (see question set below)
│    output model built per-query with pydantic.create_model
│    meta maps question ids → human values (e.g. note_<slug> → note name)
│    (tasting-note questions dropped when the regex LLM is enabled)
│    needs_tasting_notes noul = the gate deciding whether Gemini is needed
│    needs_origin noul = the gate deciding whether params.origin is composed
│    needs_region / needs_variety / needs_farm nouls = the gates deciding
│      whether params.region / params.variety / params.farm are composed
├─ run_regex_fields(query, ...)   Gemini gemini-2.5-flash-lite → regex_fields
│    composes tasting_notes_search wildcard expression (hybrid split)
│    SKIPPED when the needs_tasting_notes gate is closed (wants_tasting_notes)
│    every emitted value passes through sanitize_regex_value
├─ compose_search_params(query, answers, context, filtered, meta, regex_fields)   PURE, no network/DB (in jev_common.py)
│    interprets answers + regex extraction → validated SearchParameters
│    regex_fields['tasting_notes_search'] wins over the Jev candidate expression
│    params.origin composed ONLY when the needs_origin gate is open (wants_origin)
│    params.region / params.variety / params.farm composed ONLY when their
│      needs_* gate is open (wants_region / wants_variety / wants_farm)
├─ run_native / run_benchmark / main (argparse CLI)
```

Reused unchanged from the production agent: `resolve_canonical_roasters`
(accent/case canonicalization, via `strip_accents`), `generate_search_url`, and
the `SearchContext` SQL (`build_search_context`, replicating `get_search_context`
so the script runs without a Gemini key).  `filter_context_by_query` (candidate
lists) mirrors the production helper's n-gram substring matching and adds
**Jaro-Winkler typo recall** on top (see the fuzzy-recall section below); the
production agent itself has no fuzzy matching.

### Question set (one `systemone` batch)

| Question id | Type | Options / meaning |
|---|---|---|
| `roaster` | choice | filtered roasters + `none` |
| `origin_country` | choice | all ~79 DB country codes + `none` |
| `origin_group` | choice | 8 continents + `specific_country` + `none` |
| `variety` | choice | filtered varietals + `none` |
| `variety_spelling_variant` | noul | geisha/gesha fuzzy case → emits `Ge*sha` |
| `process` | choice | filtered processes + `none` |
| `process_excludes_anaerobic` | noul | → `Natural&!Anaerobic` |
| `roast_level` | choice | the **emitted wildcard strings** (`Light`, `Light\|Medium-Light\|Medium`, …) + `none` |
| `roaster_location` | choice | codes parsed from `GB (United Kingdom)` style entries + `none`; option keys stay codes but descriptions are human-readable (`United Kingdom (GB)`, `Europe — all roasters in Europe (XE)`) |
| `region` / `producer` / `farm` | choice | filtered lists + `none` |
| `is_flavour_query` | noul | → `use_tasting_notes_only` |
| `needs_tasting_notes` | noul | **the Jev gate** in front of the regex-field Gemini call: does the query have any taste intent worth searching tasting notes for? `no` → Gemini is skipped entirely (see hybrid-split section) |
| `needs_origin` | noul | **the Jev gate** in front of `params.origin` composition: does the query name the coffee's ORIGIN (country/region/continent)? A named coffee-origin country/region **always opens the gate**, even alongside a roaster/farm/varietal (`'Calico panama geisha kotowa'` → yes); only roaster-location / availability-shipping place words (`'uk roasters'`, `'available in the US'`) and origin-free entity-name queries close it. `no` → no origin filter is composed even if `origin_group`/`origin_country` picked something |
| `needs_region` | noul | **the Jev gate** in front of `params.region` composition: does the query name a SUB-NATIONAL region (`'Huila'`, `'Nariño'`, `'Yirgacheffe'`)? A whole country is the coffee's origin, not a region (`'El Salvador'` → no); a farm/estate name is not a region even when it appears in the regions list (`'Kotowa'` is the Kotowa estate → no). `no` → no region filter is composed even if the `region` choice picked a candidate |
| `needs_variety` | noul | **the Jev gate** in front of `params.variety` composition: does the query name a VARIETAL (`'Pink Bourbon'`, `'geisha'`, `'Laurina'`, `'Sudan Rume'`)? A name introduced by an estate word (`'Finca el paraiso'` → the farm `'El Paraiso'`, not the `'Paraiso'` varietal) is a farm name → no. `no` → no variety filter is composed even if the `variety` choice picked a candidate |
| `needs_farm` | noul | **the Jev gate** in front of `params.farm` composition: does the query name a FARM/estate (`'Kotowa'`, `'Finca El Paraiso'`)? Roaster/producer/varietal/bean/region/country names → no. `no` → no farm filter is composed even if the `farm` choice picked a candidate |
| `note_<slug>` × 8 | noul | "does the query request flavour X?" |
| `exclude_<slug>` × 8 | noul | "does the query explicitly exclude X?" |
| `notes_disjunctive` | noul | OR (`\|`) vs AND (`&`) joining |
| `has_max_price` / `has_min_price` | noul | gates regex price extraction |
| `has_large_bag` | noul | gates weight extraction |
| `high_altitude` | noul | "high altitude" no-number → `min_elevation=1500` |
| `is_decaf` / `in_stock_only` | noul | booleans (`None`/`False` defaults preserved) |
| `is_single_origin` | choice | tri-state `single_origin` / `blend` / `none` — `none` (not mentioned) → `None`; only an explicit ask sets `True`/`False` |
| `sort_by` / `sort_order` | choice | `date_added, price, price_large, name, cupping_score, relevance, default` / `asc, desc, default` — `default` keeps the schema default (`date_added`/`desc`) and is **omitted** from the search URL |
| `query_specificity` | score | 0–2 → `confidence = min(0.95, 0.7 + 0.125·score)` |

Choice primitive caps at 255 options. The real DB has 79 countries (< 200, so
the full list is used), but **453 roasters / 977 processes / 6917 tasting
notes** exceed the cap — those use the n-gram-filtered candidates (≤ 20) plus
a `none` option, exactly as the production agent feeds its prompt.

### Tasting-note candidate selection (design decision)

`filter_context_by_query` returns n-gram substring matches sorted by match
length (plus Jaro-Winkler fuzzy recall for unmatched n-grams — see the
fuzzy-recall section below), and its alphabetical tiebreak lets long compound
labels ("70% Dark Chocolate") crowd out the plain canonical notes ("Chocolate",
"Bitter"). The
prototype therefore:
1. **augments** the filtered pool with simple (≤ 2-word) notes from the full
   list that relate to a content word (substring **or token-prefix** match, so
   "chocolatey" still surfaces "Chocolate");
2. **ranks** simpler notes first;
3. **dedupes** near-duplicates at composition time (keeps the most specific
   term: "Choc" → "Chocolate", "Bitter" → "Bitterness"), and
4. **parenthesizes** any emitted term containing a wildcard operator char
   (`&|!()*?`) so a stored label like "Bright & Fruity" stays a single
   alternative instead of corrupting the expression grammar.

### Deterministic composition rationale

- **Prices**: `under|below|max|less than|cheaper than|no more than` →
  `max_price`; `over|above|at least|more than` → `min_price`; `£ $ €` and bare
  numbers handled; only applied when the matching noul is true.
- **Weights**: `1kg/1000g → 1000`, `500g → 500`, `2kg → 2000` →
  `min_large_weight` (when `has_large_bag`); no-number bulk → 1000, "large
  bag" → 500 (matches the golden examples); explicit gram amounts →
  `min_weight`/`max_weight`.
- **Elevation**: `NNNN m|masl|meters` with `above` → `min_elevation`,
  `below` → `max_elevation`; clamped to the schema's 0–3000.
- **Origin**: continent expansion (south_america/asia lists copied verbatim
  from the Gemini prompt) or the chosen country code, then the same
  post-processing as the original: full-name→code fixup, drop codes not in the
  DB, empty→`None`.
- **Sort**: `default` (or a missing answer) keeps the schema defaults
  `date_added`/`desc`.  `generate_search_url` **omits** `sort_by`/`sort_order`
  when they equal the server default, so an unrequested sort never appears in
  the URL — an explicit non-default sort is the only thing emitted.
- **Booleans**: `is_decaf` is `True` or `None`; `is_single_origin` is a
  tri-state choice (`single_origin` → `True`, `blend` → `False`, `none`/missing
  → `None`) — a query that does not mention single-origin or blends stays
  `None` instead of guessing; `in_stock_only` is a plain `bool`.

### The regex-field LLM (prompt + flags)

`run_regex_fields` builds a tiny pydantic-ai agent per call: `GoogleModel(
"gemini-2.5-flash-lite", provider=GoogleProvider(...))` with a dynamic
`create_model("RegexFields", tasting_notes_search=(str | None, Field(None)))`
output type, `instructions=REGEX_INSTRUCTIONS`, wrapped in a `jev.regex`
logfire span.  `GOOGLE_API_KEY` comes from `.env` (already loaded); when it is
missing the function warns on stderr and returns `{}` (the Jev candidate path
takes over).  The output `regex_fields` dict is returned to the caller and
passed to `compose_search_params`.

```
REGEX_INSTRUCTIONS:
You convert the TASTE/FLAVOUR intent of a coffee-search query into a single
tasting-note search expression. Return null when the query expresses no
flavour/taste preference at all (e.g. it is about origin, roast level, price,
bag size, process, or variety only).

WILDCARD SYNTAX (search backend):
- `*` any suffix, `?` one character; `|` OR; `&` AND; `!` NOT; `()` grouping.
- a bare term matches case-insensitively as a substring.

RULES:
- Decompose a conceptual flavour into its constituent notes joined with `&`.
- Use `|` for synonyms/variants where any one suffices.
- Use wildcard adjective stems so word forms match (e.g. use `acidic*` for
  "acidity", `wine*` for "wine-like", `berry*` for "berry/berries").
- Flavour can be signalled by "notes", "flavours", "tasting like", or
  "with X notes" even when the query ALSO constrains origin/roast/process.
- Never invent notes; use common coffee vocabulary.
- Do NOT emit origin, roaster, process or roast information.

EXAMPLES:
- "taste like a pina colada" -> pineapple&coconut
- "chocolate but not bitter" -> chocolate&!bitter
- "fruity Ethiopian coffee" -> fruit*|berry*
- "citrus flavors" -> citrus*|lemon*|orange*|tangerine*|lime*
- "not chocolatey" -> !chocolate&!cocoa
- "light roast with berry notes" -> berry*
- "wine-like acidity" -> wine*|acidic*
- "light roast pink bourbon" -> null
- "coffee from uk roasters" -> null
- "cheapest bulk options" -> null
```

CLI flags:

- `--no-regex-llm` — disable the Gemini regex-field LLM; the tasting-note
  questions go back into the Jev model and the Jev candidate expression is
  used (the pre-hybrid behavior).
- `--regex-model` (default `gemini-2.5-flash-lite`) — swap the Gemini model.

The Gemini call is gated by the Jev `needs_tasting_notes` answer: `run_native`
reads it via `jev_common.wants_tasting_notes(answers)` and only calls
`run_regex_fields` when `use_regex_llm AND needs_tasting_notes`.  The result
dict records both `needs_tasting_notes` and `regex_llm_called` (True even when
the gated-on call later fails and falls back to `{}`), and both keys are
exposed in the CLI `--json` output, the `--serve` API response, and the
inspector's "REGEX LLM (Gemini)" section ("Jev gate: taste intent — Gemini
called" vs "Jev gate: no taste intent — Gemini skipped").

## Golden-set benchmark (23 queries, live run 2026-09-26)

Queries and expected fields are copied verbatim from the `EXAMPLE_QUERIES`
block in `search_agent.py`. Confidence is scored within ±0.15; `origin`
expectations are normalized through DB availability (the original's own
post-processing drops unknown codes).  The denominator grew from 95 to 100:
the five non-flavour queries (`#02 light roast pink bourbon`, `#07 uk
roasters`, `#11 geisha variety`, `#13 south america`, `#15 cheapest bulk`)
now also assert `"tasting_notes_search": None`, so an invented flavour
expression on those fails the benchmark.  With the `needs_origin` gate the
denominator grew again from 100 to **104**: the four queries that never name a
coffee origin (`#02 light roast pink bourbon`, `#11 any geisha variety with
light to medium roast`, `#19 single origin coffees`, `#20 blends only`) now
also assert `"origin": None` (joining `#07`/`#08`), so an origin expansion on a
non-origin query fails the benchmark — the `origin` row is now **15/15**.  With
the `needs_region` / `needs_variety` / `needs_farm` gates the denominator grew
again from 104 to **108**: `"region": None` on `#02`/`#03`, `"variety": None`
on `#04`, and `"farm": None` on `#03` measure the new gates (`farm` joined
`TRACKED_FIELDS` so it is actually scored).

### Hybrid (regex LLM ON — the default)

```
total: 97/108 fields across 23 queries; avg Jev latency 432 ms; total input
tokens 262286; total output tokens 44946; wall time 32.6 s

field                  matched  total   rate
search_text                 0      2    0/2
tasting_notes_search       12     13   12/13
use_tasting_notes_only     14     18   14/18
roaster                     2      2    2/2
variety                     6      6    6/6
process                     0      2    0/2
origin                     15     15   15/15
region                      2      3    2/3
farm                        1      1    1/1
roast_level                 3      3    3/3
roaster_location            2      2    2/2
min_price                   0      0       -
max_price                   2      2    2/2
min_weight                  0      0       -
max_weight                  0      0       -
min_large_weight            4      4    4/4
min_elevation               1      1    1/1
max_elevation               0      0       -
is_decaf                    0      0       -
is_single_origin            8      8    8/8
in_stock_only               0      0       -
sort_by                     4      4    4/4
sort_order                  4      4    4/4
confidence                 17     18   17/18
```

### Jev-only (`--no-regex-llm` — the pre-hybrid behavior)

```
total: 92/108 fields across 23 queries; avg Jev latency 465 ms; total input
tokens 341756; total output tokens 53926; wall time 17.1 s

field                  matched  total   rate
search_text                 0      2    0/2
tasting_notes_search        6     13    6/13
use_tasting_notes_only     15     18   15/18
roaster                     2      2    2/2
variety                     6      6    6/6
process                     0      2    0/2
origin                     15     15   15/15
region                      2      3    2/3
farm                        1      1    1/1
roast_level                 3      3    3/3
roaster_location            2      2    2/2
min_price                   0      0       -
max_price                   2      2    2/2
min_weight                  0      0       -
max_weight                  0      0       -
min_large_weight            4      4    4/4
min_elevation               1      1    1/1
max_elevation               0      0       -
is_decaf                    0      0       -
is_single_origin            8      8    8/8
in_stock_only               0      0       -
sort_by                     4      4    4/4
sort_order                  4      4    4/4
confidence                 17     18   17/18
```

**`tasting_notes_search` is the headline: 0/8 → 12/13 (hybrid) vs 6/13
(Jev-only).**  The Jev-only 6/13 is entirely the 5 new absence assertions
(Jev emits no notes for the non-flavour queries) plus `#04`; every golden
wildcard string still misses (`Pinacolada`, `Fruity`,
`Chocolate&!Bitterness`, `Citruses|Citrícos|Citrusy`, `Berry-Like`,
`Acidity`, `!Chocolatey`).  The regex LLM fixes all of them plus the
absences.  The single remaining hybrid miss is `#04 cartwheel … chocolate
notes` → `chocolate*` vs the golden `chocolate` (the LLM applies the
wildcard-stem rule to the noun); semantically equivalent, string differs —
left as-is rather than churn the validated prompt.  `tasting_notes_search`
now also lands the two prompt-tuned misses from the earlier spike:
`#08 light roast from european roasters with berry notes` → `berry*` and
`#09 Kenyan AA with wine-like acidity` → `wine*|acidic*`.

**The `needs_tasting_notes` gate does not change the golden benchmark** (run
2026-09-25, hybrid): it opens on all 8 flavour golden queries
(including `#04`/`#08`/`#09`, whose flavour words ride along with an
origin/roast constraint) and closes on all 5 absence golden queries, so Gemini
is only actually called on 8 of the 23 golden queries.  On real queries the
gate's effect is dramatic: `"Standout ture waji"` (previously → `"turmeric"`),
`"idido"` (→ `"idido"`), `"agena"` (→ `"agena"`), `"something similar to yuan
yi yan"` (→ `"yuan yi yan"`), `"Moby dick sl9"` (→ the literal string `"null"`
in the URL), `"donna daisy"`, `"koke violet"` and `"el salvador"` all now emit
`tasting_notes_search = None` with `regex_llm_called = False`, while true
flavour queries (`"Strawberry notes"` → `strawberry*`, `"Mellow"` → `mellow`,
`"violet"` → `violet*`/`violet`) still open the gate and call Gemini.

(The Jev-only total fluctuates 82–92/108 between runs — `use_tasting_notes_only`
and `variety` are borderline for a non-deterministic model; the hybrid total is
97–98/108 across the runs above.)  Jev-side token usage also drops in hybrid
mode, because dropping the tasting-note questions shrinks the per-query model:
~270.8 k vs ~341.8 k input tokens across the benchmark.

### Don't-guess-if-not-asked rule (is_single_origin tri-state + sort defaults)

The prototype now refuses to invent filters or sorts the query never states:

- **`is_single_origin` is a tri-state Choice**, not a bool.  `is_single_origin`
  (`Literal['single_origin', 'blend', 'none']`) maps to `True` only for an
  explicit single-origin ask, `False` only for an explicit blends ask, and
  `None` for everything else.  Six golden queries that never mention
  single-origin/blends now assert **`"is_single_origin": None`** (`#01 pina
  colada`, `#02 light roast pink bourbon`, `#07 uk roasters`, `#09 Kenyan AA`,
  `#13 south america`, `#15 cheapest bulk`) and two new queries pin the
  positive/negative sides (`#19 single origin coffees` → `True`,
  `#20 blends only` → `False`).  The field row goes from **unmeasured (0/0)**
  to **8/8** and the denominator from 87 to 95.
- **Sorts** are only emitted when asked.  `sort_by`/`sort_order` questions say
  "answer `default` unless the query explicitly requests a sort/direction" and
  explicitly counter-example a **price filter** (`'under £30'`), a **bag size**
  (`'large bag'`, `'1kg'`) or `'bulk'` on its own — those are NOT sort requests
  and answer `'default'`.  `generate_search_url` omits `sort_by`/`sort_order`
  when they equal the server default (`date_added`/`desc`) — an unrequested sort
  never reaches the URL.  `field_matches` normalizes an expected `"default"` to
  `date_added`/`desc` so the benchmark scores the omission as a match.  `#17
  large bag options under £30` asserts `"sort_by": "default", "sort_order":
  "default"` (a price filter + bag size alone does not request a sort), while
  `#15`/`#16`/`#18` keep their explicit `price_large`/`asc` (those do).
- **Result**: `sort_by` and `sort_order` both improve to **4/4**.  The
  non-example fixed `#17 large bag options under £30` → `default`/`default`
  (previously Jev inferred `price_large` from "large bag options"), and adding
  `'sorted by price'` to the ascending direction mapping fixed `#16 1kg bags
  sorted by price` → `price_large`/`asc` (5/5, previously the `sort_order: desc`
  diff).  `#15 cheapest bulk options` → 6/6 and `#18 best value large bags` →
  5/5 continue to match.

### Origin-vs-roaster-location conflation (fixed, now measured)

The origin questions were tightened so the model cannot confuse the **coffee's
origin** with the **roaster's location**: `origin_group` / `origin_country`
are explicitly about "which origin group/country is the COFFEE from" and carry
the counterexample that `'european roasters'` / `'uk roasters'` describe the
roaster (→ `roaster_location`, pick `none` for origin); `roaster_location` is
explicitly "about the roaster, not the coffee's origin"; and `INSTRUCTIONS`
gains the same "distinguish origin from roaster location" sentence. The two
roaster-location golden entries (`#07 coffee from uk roasters`, `#08 light
roast from european roasters with berry notes`) now also assert **`"origin":
None`**, so an origin expansion on a roaster-location query fails the
benchmark instead of silently passing. Before the fix `#07/#08` composed an
`origin=europe` expansion (nine `origin=` params); after it they compose
`roaster_location` only. The conflation fix plus the new assertions take the
`origin` row to 11/11 and the denominator to 87.

### The `needs_origin` gate (origin only composed when the query names one)

The conflation fix stopped `origin_group`/`origin_country` from *answering* for
the roaster's location, but on real queries Jev still **leaked a country list
when the query never asked for an origin at all**: `"Standout ture waji"` (a
roaster + producer lookup) matched "waji"/African context, so Jev picked
`origin_group=africa` and `compose_search_params` expanded it to the full
African country-code list even though the query is not about origin.  Mirroring
the `needs_tasting_notes` gate, a new **`needs_origin`** noul now sits in front
of origin composition:

- the question asks whether the query names the coffee's **ORIGIN** — the
  country/region/continent the coffee comes from (`'Colombian coffee'`,
  `'Kenyan AA'`, `'Ethiopian'`, `'coffees from south america'`).  A country or
  region the coffee comes from **always opens the gate**, even when the query
  also names a roaster / producer / farm / varietal: `'Calico panama geisha
  kotowa'` → **yes** (Panama is the coffee's origin, even though Calico is the
  roaster and Kotowa the farm).  It answers **no** when the only place words
  describe the roaster's location (`'coffee from uk roasters'`, `'european
  roasters'`) or where it is available/shipped (`'available in the US'`), and
  **no** when the query only names a roaster / producer / farm / varietal /
  bean / process / roast / price / bag size without naming the coffee's origin
  country/region (`'Standout ture waji'`, `'Finca el paraiso'`, `'idido'`);
- `compose_search_params` wraps the whole origin block in `if
  noul("needs_origin"): ... else: params.origin = None` — so a closed gate
  produces **no** `origin` filter even if `origin_group`/`origin_country`
  picked a continent/country (that pick is still recorded, just not composed);
- `run_native` exposes `needs_origin` (via the pure helper
  `jev_common.wants_origin`, mirroring `wants_tasting_notes`) in the result
  dict, the CLI `--json` output, and the `--serve` API response; the inspector
  shows the decision ("origin gate: origin named" / "origin gate: no origin
  named") above the composed params.

On real queries the effect is exactly the intended one: `"Standout ture waji"`
→ `origin=None` (previously `origin=[ET, KE, RW, UG, …]` — the African
expansion), `"Calico panama geisha kotowa"` → `origin=['PA']` (the country the
coffee comes from opens the gate even though Calico is the roaster, geisha the
varietal and Kotowa the farm — a gate false-negative closed it before, reading
"panama" as the geisha variety's provenance descriptor), and `"Cheapest bag
available in the US light roast filter"` → `origin=None` ("available in the
US" is availability, not origin), while `"el salvador"` → `origin=['SV']` and
`"Yirgacheffe colombia"` → `origin=['CO']` (the named country) still open the
gate.

The golden set now **measures** the gate: the four queries that never name a
coffee origin — `#02 light roast pink bourbon`, `#11 any geisha variety with
light to medium roast`, `#19 single origin coffees`, `#20 blends only` — assert
`"origin": None` (joining the two roaster-location entries `#07`/`#08`), taking
the `origin` row from 11/11 to **15/15** and the field denominator from 100 to
104.

### The `needs_region` / `needs_variety` / `needs_farm` gates (candidate fields only composed when the query names one)

`region`, `variety` and `farm` were the last candidate-choice fields without a
gate: they were composed whenever Jev picked a candidate, and on real queries
the candidate lists over-fired — `"el salvador"` composed `region='El Salvador'`
(a country, not a sub-national region), `"Skylark Colombia laurina"` composed
`region='Colombia'`, `"Finca el paraiso"` composed `variety='Paraiso'` (a farm
name), and `"Calico panama geisha kotowa"` composed `region='Kotowa'` (the
Kotowa estate).  Mirroring `needs_origin` / `needs_tasting_notes`, three new
nouls now sit in front of each composition:

- **`needs_region`** — does the query name a SUB-NATIONAL region?  A whole
  country (`'El Salvador'`, `'Colombia'`, `'Kenya'`) is the coffee's origin,
  handled separately, **not** a region → no; a farm/estate name is not a
  region even when it appears in the regions list (`'Kotowa'` is the Kotowa
  estate in Panama → no); roaster/producer/farm/varietal/bean/process/roast/
  price/bag-size names → no.
- **`needs_variety`** — does the query name a VARIETAL (`'Pink Bourbon'`,
  `'geisha'`/`'gesha'`, `'Laurina'`, `'Sudan Rume'`, `'SL9'`)?  A name
  introduced by an estate word (`'Finca'`, `'Fazenda'`, `'Hacienda'`) is a
  farm name, not a varietal: `'Finca el paraiso'` names the farm `'El
  Paraiso'`, not the `'Paraiso'` varietal → no; roaster/producer/farm/bean/
  product/origin names → no.
- **`needs_farm`** — does the query name a FARM/estate (`'Kotowa'`, `'Finca El
  Paraiso'`, `'Gara Agena'`)?  Roaster/producer/varietal/bean/region/country
  names → no.

`compose_search_params` wraps each block in `if noul("needs_<field>"):` — a
closed gate produces **no** filter even if the `region`/`variety`/`farm`
choice picked a candidate (that pick is still recorded in the answers, just not
composed).  The existing variety spelling-variant / geisha logic stays inside
the `needs_variety` block.  `producer` is **deliberately left ungated** — it is
the same class of candidate-choice field and shows the same over-fire pattern
(`"Finca el paraiso"` → `producer='Finca El Paraiso'` is actually the desired
result, since the query names the farm-as-producer), but it is out of scope for
this change and is a possible follow-up.  `run_native` exposes
`needs_region` / `needs_variety` / `needs_farm` (via the pure helpers
`jev_common.wants_region` / `wants_variety` / `wants_farm`, mirroring
`wants_origin`) in the result dict, the CLI `--json` output, and the `--serve`
API response; the inspector shows all three decisions ("region gate: …" /
"variety gate: …" / "farm gate: …") above the composed params.

On real queries the effect is exactly the intended one:

| query | before | after |
|---|---|---|
| `"el salvador"` | `region='El Salvador'` (a country) | `region=None`, `origin=['SV']` |
| `"Skylark Colombia laurina"` | `region='Colombia'` (a country) | `region=None`, `variety='Laurina'`, `origin=['CO']` |
| `"Finca el paraiso"` | `variety='Paraiso'` (a farm name) | `variety=None`, `farm='Finca El Paraiso'` |
| `"Calico panama geisha kotowa"` | `region='Kotowa'` (the estate) | `region=None`, `variety='Ge*sha'`, `farm='Kotowa'`, `origin=['PA']` |
| `"Standout ture waji"` | (ungated producer) | `producer='Ture Waji'` unchanged, `origin=None` |

`"Yirgacheffe colombia"` → `region='Gedeb, Yirgacheffe'` (a genuine region)
still opens the gate, so the tuning only suppresses estate/country misreads,
not legitimate regions.

The golden set now **measures** the gates with absence assertions (no query that
legitimately names the field is touched): `"region": None` on `#02 light roast
pink bourbon` and `#03 fruity Ethiopian coffee under £25`, `"variety": None` on
`#04 cartwheel natural process with chocolate notes`, and `"farm": None` on
`#03` — taking the field denominator from 104 to **108**, the `region` row to
2/3 (the `#10` miss is the pre-existing single-choice gap: Jev can only emit
one region, not `Huila|Nariño`), `variety` to 6/6 and a new `farm` row to 1/1.
`origin` stays **15/15**.

### Candidate-pool frequency cutoff + region country-name guard

Scraper extraction errors inflate the `region` / `farm` / `producer` candidate
pools with one-off junk: at the raw `SELECT DISTINCT` level **77–85 % of
distinct values appear fewer than 3 times**.  `build_search_context` now applies
a frequency cutoff (`MIN_ENTITY_MENTIONS`, default **2**, overridable with
`KISSATEN_MIN_ENTITY_MENTIONS`) to those three queries (`GROUP BY … HAVING
COUNT(*) >= …`), shrinking the pools:

| pool | raw distinct | `>=2` after cutoff |
|---|---|---|
| region | 2983 | 1082 |
| farm | 3588 | 1241 |
| producer | 5331 | 1597 |

A separate guard drops any `region` whose accent/case-normalised value equals a
`country_codes` name (`is_country_name`).  The "country mislabeled as region"
case is **frequent**, not rare — `region='Panama'` 57, `'Colombia'` 34,
`'Ethiopia'` 6, `'El Salvador'`/`'Kenya'` 3 — so a frequency cutoff alone would
*not* remove it; the `needs_region` gate plus this guard are what kill it.

Verified on the real-query set: all country-mislabeled regions are gone, the
spurious `region='El Salvador'` / `'Colombia'` / `'Kotowa'` picks disappear, and
genuine low-frequency entities survive at `>=2` (`farm 'Idido'` 2, `'Dona
Daisy'` 2, `'Gara Agena'` 3).  A `>=3` threshold culled `'Idido'` and `'Dona
Daisy'` (both 2) and split otherwise-identical queries, which is why the default
is 2; only true singletons (`'Yuan Yi Yuan'` / `'Yuan Yin Yuan Coffee Farm'`, 1
each) are dropped.  The golden benchmark is unchanged (97–98/108, within Jev
run-to-run variance).

### Jaro-Winkler typo recall in the candidate lists

`filter_context_by_query` now catches misspelled entity names algorithmically.
For each candidate list it keeps the existing n-gram **substring** matches
(sorted by longest match, then alphabetically) and adds a **per-ngram
fallback**: only n-grams that matched *no* item are run through `rapidfuzz`
(`process.extract` with `JaroWinkler.normalized_similarity`, the same
`rapidfuzz` the repo already depends on via `kissaten.dedup.matcher`), and each
returned item records its best Jaro-Winkler score across those unmatched
n-grams.  An item survives when it has a substring match **or** a fuzzy score
`>= NAME_FUZZY_MIN` (0.82); the list is sorted by `(-best_len, -fuzzy_score,
item)` so exact/n-gram matches always rank above fuzzy-only matches, then capped
at 20.  `roast_levels`, `countries` and `roaster_locations` stay unfiltered
(all options) exactly as before.

The 0.82 threshold is tuned on the measured typo/false-positive split:

| query n-gram | candidate | Jaro-Winkler |
|---|---|---|
| `larina` | `Laurina` | 0.85 (keep) |
| `giesha` | `Gesha` | 0.82 (keep) |
| `borbon` | `Bourbon` | 0.85 (keep) |
| `pacamar` | `Pacamara` | 0.87 (keep) |
| `maragogype` | `Maragogipe` | 0.87 (keep) |
| `typicca` | `Typica` | 0.85 (keep) |
| `berry` | `Peaberry` | 0.81 (reject < 0.82) |
| `natural` | `Caturra` | 0.81 (reject < 0.82) |

`"larina"` → `varietals=['Laurina']`, `"giesha pink borbon"` → `varietals`
contains `Bourbon`/`Gesha`/`Pink Bourbon`, and `"natrual process"` → `processes`
ranks `Natural, XO Process` first (the fuzzy 2-gram `"natrual process"` matches
it and boosts it above the other substring hits); the bare `'Natural'` (fuzzy
0.849) is correctly recalled but stays outside the top-20 because >20 process
names contain the substring `"process"`.

The **country-name guard is reused**: the same `is_country_name` check that
`build_search_context` already applies to `regions` is now applied in
`filter_context_by_query` to the `varietals`, `farms`, `producers` and `regions`
lists, using the accent/case-normalised `country_full_name`s of
`context.available_countries`.  Country names that leak into the DB as
"varieties" (`Ethiopia` 0.92, `Kenya` 0.87, `Colombia` 0.92 — all comfortably
above the fuzzy threshold, exactly the junk that must never be offered) are
dropped even when they fuzzy-match.  The guard is **not** applied to
`roasters`, `processes` or `tasting_notes`.

Note the **original Gemini pipeline has no fuzzy matching at all**: it relies
purely on the LLM's world knowledge (`Ge*sha` wildcard) plus
`varietal_mappings.json` / `variety_canonical` accent variants.  This change
adds deterministic algorithmic recall on top of those, so a typo like
`"larina"` no longer depends on the model guessing the canonical spelling.

The golden benchmark is unaffected (97/108 on the primary run — `variety` 6/6,
all asserted-field rows identical to the pre-change candidate lists; the
`use_tasting_notes_only` row fluctuates 14–15/18 between runs exactly as
documented, and is not candidate-dependent).  Real-query spot checks are stable:
`idido` → `farm='Idido'`, `donna daisy` → `farm='Dona Daisy'`, `Skylark
Colombia laurina` → `variety='Laurina'`, `el salvador` → `origin=['SV']` only.

**The deterministic + choice half of the design is essentially perfect**:
origin 15/15, variety 6/6 (including `Ge*sha` and canonical "Sudan Rume"),
roast_level 3/3, max_price 2/2, min_large_weight 4/4, min_elevation 1/1,
roaster 2/2, is_single_origin 8/8. Per-query highlights:

- `#13/#14 coffees from south america / asia` → 4/4, 3/3 ✓ (continent expansion)
- `#19/#20/#21 single origin coffees / blends only / panama geisha` → all ✓
  (`is_single_origin` tri-state True/False/None absence)
- `#07 coffee from uk roasters` → 5/5 ✓ (also asserts `origin: None` and
  `is_single_origin: None`)
- `#08 european roasters` → `roaster_location` + `origin: None` both pass
  (also catches the curated `XE` code; the only remaining diff is the
  `use_tasting_notes_only` false-positive)
- `#15 cheapest bulk options` → 6/6 ✓; `#16 1kg bags sorted by price` →
  5/5 ✓ (`price_large` + `asc`); `#17 large bag options under £30` → 6/6 ✓
  (`default`/`default` — a price filter + bag size alone no longer implies a
  sort); `#18 best value large bags` → 5/5 ✓

The deterministic half (origin 15/15, variety 6/6, roast_level 3/3, max_price
2/2, min_large_weight 4/4, min_elevation 1/1, roaster 2/2, is_single_origin
8/8, confidence 17/18) is the same shape as the production agent's own behavior
on these fields.

## Observed gaps vs the Gemini agent

1. **`tasting_notes_search` exact strings never matched the golden when left to
   Jev (0/8).**  Jev can only pick from the DB's stored note labels ("Citrus
   Oil|Citruses|…", "Chocolate&!Bitterness"), while Gemini emits curated
   wildcard patterns ("fruit*|berry*", "chocolate&!bitter").  **Fixed by the
   hybrid split**: the regex-field LLM now composes the wildcard expression
   (12/13, the one miss being `chocolate*` vs `chocolate` on `#04`).  The
   pre-hybrid Jev-only behavior is still reachable via `--no-regex-llm`.  The
   **`needs_tasting_notes` gate** additionally fixes Gemini's false positives
   on pure product/producer/bean lookups (see the hybrid-split section):
   queries whose only salient words are roaster/producer/farm/bean names now
   skip Gemini entirely and emit `tasting_notes_search = None`.
2. **No `search_text` question** — the question set has no free-text field, so
   "Kenyan AA…" → `search_text:"AA"` is impossible (0/2). Jev has no prose
   output; adding a short "extract a search phrase" question would cover it.
3. **Single-choice process/region** — "natural or honey process" needs
   `process: "Natural|Honey"` and "Huila or Nariño" needs
   `region: "Huila|Nariño"`, but a choice answers exactly one option.
4. **Noise on unconstrained queries**: Jev sometimes invents low-confidence
   choices (e.g. `variety="Ethiopian Varieties"` @ 0.29, `roaster_location=GB`
   @ 0.53, `sort_by=relevance` @ 0.52 for "fruity Ethiopian coffee under
   £25"). No confidence floor is applied to choices; Gemini is more
   conservative.
5. **`use_tasting_notes_only` false-positives (14/18)**: Jev's `is_flavour_query`
   fires true for queries Gemini flags as broader searches ("light roast pink
   bourbon", "high altitude Colombian…", "light roast from european roasters
   with berry notes").
6. **`roaster_location=EU` vs `XE`** for "european roasters": both codes exist
   in the DB list; Jev picked the plain "EU" code. XE is the curated
   "Europe (non-EU)"/unassigned grouping the Gemini prompt knows to prefer.
7. **Token usage** is high relative to value: ~10.2 k input + ~2.3 k output
   tokens per query for ~45 questions. The noul-per-note questions (16 for 8
   notes) and the 79-option country choice dominate. In hybrid mode the
   tasting-note questions are dropped, cutting Jev input tokens by ~24%
   (~227.9 k vs ~298.8 k across the benchmark).

## Version requirement (the repo is still on 1.x)

The repo pins `pydantic-ai>=1.107.1,<2` in `pyproject.toml`.  The native path
needs **pydantic-ai ≥ 2.45** (verified on 2.48.0 + typesafe-sdk 0.7.1, Python
3.10).  The working invocations layer 2.x via `uv run --with` **without
modifying `pyproject.toml`**:

```bash
# Preferred — project env + 2.x overlay (duckdb/dotenv come from the project):
PYTHONPATH=src uv run --with "pydantic-ai[typesafe]>=2.45" \
    python scripts/jev_native_prototype.py "fruity Ethiopian coffee under £25" --json

# Fully isolated (no project env at all):
PYTHONPATH=src uv run --no-project --with "pydantic-ai[typesafe]>=2.45" \
    --with python-dotenv --with duckdb \
    python scripts/jev_native_prototype.py "fruity Ethiopian coffee under £25" --json

# Golden-set benchmark:
PYTHONPATH=src uv run --with "pydantic-ai[typesafe]>=2.45" \
    python scripts/jev_native_prototype.py --benchmark
```

Both commands resolve `pydantic-ai 2.48.0`.  A subtlety: under 2.x,
`PYTHONPATH=src` alone is NOT enough to `import kissaten.schemas.ai_search` —
`kissaten/__init__.py` eagerly imports `.ai` → `extractor.py` →
`pydantic_ai.models.gemini`, which was removed in 2.x.  `jev_common.py`
therefore tries the package import first and, when it fails, loads the single
`ai_search.py` module standalone via importlib (it only depends on pydantic).
Under the repo env (1.x) the package import succeeds and the classes stay the
same objects the rest of the codebase uses.

## `Choices(...)` dynamic candidates

`from pydantic_ai import Choices; Choices({name: desc, ...}, name=..., description=...)`
returns a TYPE usable as a field annotation (or per-run `output_type=`).  For
every query the prototype builds fresh candidate sets from the filtered
context (roasters, varieties, processes, countries, locations, regions,
producers, farms — capped at 20) plus an explicit `"none"` member.  The
adapter requires a Choice to have ≥ 2 options, so when a query yields an
**empty** candidate list the field is omitted from the model —
`compose_search_params` treats a missing answer identically to a `"none"` pick.

Tasting notes use the dynamic multi-select form `list[Choices(...)]` (proven
live: one Noul per option, output = the selected note names), which mirrors
the per-note `note_<slug>`/`exclude_<slug>` nouls conceptually.  The adapter
rejects a list whose `Choices` has < 2 options, so with 0–1 note candidates the
prototype falls back to per-candidate `bool` fields `note_<slug>`/`exclude_<slug>`
(equivalent output, any count).  Both branches are exercised by the benchmark:
queries with no flavour words in the n-gram match (e.g. "cheapest bulk options",
0 candidates) and single matches ("sudan rume", 1 candidate) use the bool
fallback; the rest (e.g. "killbean panama geisha", 8 candidates) use the
`list[Choices]` path.

## Adapter → primitive mapping

| pydantic type | Jev primitive |
|---|---|
| `bool` | Noul |
| `Literal[str, ...]` / `Enum` of strings | Choice |
| `float = Field(ge=0, le=1)` | probability |
| `IntEnum` (0..n-1, per-member docstrings, `UseEnumMemberDocstrings`) | Score |
| `list[Literal/Enum/Choices]` | one Noul per option (multi-select) |
| `Optional[Literal]` | Choice with auto-added `None` |
| nested model fields | dotted question paths |

Unsupported (raise `UserError`): `str`, unbounded int/float, `dict`,
`list[str]`, `Optional[bool]`, native tools, files.

State is derived from the **user message**: the prompt is the query plus a text
rendering of the filtered context using the same section labels as the Gemini
prompt (`MATCHED TASTING NOTES:`, `MATCHED VARIETALS (canonical names — use
these directly):`, …, `COFFEE ORIGIN COUNTRIES:`, `ROASTER LOCATIONS:`).
`instructions=` becomes shared framing inside each question; each field's
`description` IS the question (identical wording to the question set above).
There is no way to pass a structured `state=` JSON object through the adapter.

Adapter → answers conversion (in `native_to_answers`): Choice/Literal fields →
`{"type": "choice", "choice": <key>}`; bool fields → `{"type": "noul", "noul":
1.0|0.0}` (the adapter already thresholded the raw noul at 0.5 via
`TypeSafeModelSettings(typesafe_boolean_threshold=0.5)`, so mapping the output
boolean is deterministic); note multi-selects → per-slug nouls; the
`query_specificity` IntEnum → `{"type": "score", "score": float}`.

## What the adapter handles vs. what stays deterministic

The pydantic-ai TypeSafe adapter handles the transport and question encoding:
`Agent(...)` / `await agent.run(...)` replaces any hand-rolled request layer,
the per-query pydantic model encodes the ~45 questions, `Choices(...)` types
carry the candidate lists, `result.response.model_name` resolves the pinned
model (`jev-latest` → `jev-1.13.0`), `result.response.provider_details` carries
`probabilities`/`scores`/`confidence`, and `result.usage` is a **property** in
2.x (not a method).

Still **deterministic**: price/weight/elevation regex extraction,
continent→code expansion, canonical-roaster fixup, tasting-note dedupe /
parenthesization, sort mapping, confidence formula, reasoning one-liner, and
`generate_search_url`.  All of that lives in `scripts/jev_common.py`, shared by
the prototype and its unit tests (no network, no DB).  The one field that is
*not* deterministic and *not* Jev is `tasting_notes_search`, which the
regex-field LLM composes (see the hybrid-split section) — the LLM's output
enters `compose_search_params` as the optional `regex_fields` argument and wins
over the Jev candidate expression.  Jev does decide *whether* that LLM runs at
all via the `needs_tasting_notes` gate (`jev_common.wants_tasting_notes`, pure
and unit-tested), and `jev_common.sanitize_regex_value` normalises whatever
the LLM emits before it can reach composition.  Jev also decides *whether*
`params.origin` is composed at all via the `needs_origin` gate
(`jev_common.wants_origin`, pure and unit-tested): `compose_search_params`
only expands `origin_group`/`origin_country` when the gate is open.  The same
pattern gates the three remaining candidate fields: `params.region` only
composes when `needs_region` is open (`jev_common.wants_region`),
`params.variety` only when `needs_variety` is open (`jev_common.wants_variety`,
with the spelling-variant / geisha logic inside), and `params.farm` only when
`needs_farm` is open (`jev_common.wants_farm`) — each pure and unit-tested.
`producer` remains ungated.

The **remaining gaps** are properties of the question set + candidate
selection, not the transport: no `search_text` field (0/2), single-choice
process/region (`#10 Huila or Nariño` region is 2/3 — the two gate absences
pass, but Jev can only emit one region, not `Huila|Nariño`).  `tasting_notes_search`
is **fixed** by the hybrid
split (12/13 vs 0/8 pre-hybrid).  `sort_by`/`sort_order` are 4/4 — `#17 large
bag options under £30` no longer guesses `price_large` from "large bag
options" (a price filter / bag size alone is not a sort request).

Tradeoffs of the native path: token input is high because the prompt embeds
the full filtered-context text (79-country list etc.) instead of only the
per-question criteria (mitigated in hybrid mode by dropping the tasting-note
questions); latency is low per query but wall time is higher (per-query
`Agent` construction inside one event loop, plus a second Gemini call per query
for the regex fields).  The native adapter also imposes the ≥ 2-option Choices
constraint, which requires the empty-candidate omission trick above.

## Next steps

- Gate the **`producer`** field like `needs_origin` / `needs_region` /
  `needs_variety` / `needs_farm` (a `needs_producer` noul deciding whether the
  query *names* the producer before `compose_search_params` composes it).  It
  is the last candidate-choice field without a gate and shows the same over-fire
  pattern on real queries (`"Calico panama geisha kotowa"` → `producer='Kotowa'`
  is the estate name; `"Finca el paraiso"` → `producer='Finca El Paraiso'` is a
  farm, though arguably the desired result there since the farm is the
  producer), but it was deliberately left ungated in the region/variety/farm
  gate change.
- Move **more wildcard-capable fields** onto the regex LLM by extending
  `REGEX_FIELDS` (e.g. `region` → `Huila|Nariño`, `variety` → `Ge*sha`,
  `roast_level` → `Light|Medium-Light|Medium`), closing gaps 3/6 for those
  fields while keeping the structured fields on Jev.
- Add a `search_text` free-text question (single short string via a choice of
  n-gram candidates or a low-token noul set) to close gap 2.
- Support **disjunctive process/region** via a second question (e.g. a
  "second process?" noul + choice, or an `any_of` composite question).
- Apply a **choice confidence floor** (e.g. ignore choices below 0.5) or ask
  Jev a follow-up "is this genuinely in the query?" noul for each tentative
  pick to reduce gap 4.
- Consider trimming the country choice to n-gram candidates when the query
  names no country, to cut token usage (gap 7).

## Run it

```bash
PYTHONPATH=src uv run --with "pydantic-ai[typesafe]>=2.45" \
    python scripts/jev_native_prototype.py "fruity Ethiopian coffee under £25" --json
PYTHONPATH=src uv run --with "pydantic-ai[typesafe]>=2.45" \
    python scripts/jev_native_prototype.py "chocolate coffee that's not bitter" --json
PYTHONPATH=src uv run --with "pydantic-ai[typesafe]>=2.45" \
    python scripts/jev_native_prototype.py --benchmark            # golden set (hybrid, regex LLM on)
PYTHONPATH=src uv run --with "pydantic-ai[typesafe]>=2.45" \
    python scripts/jev_native_prototype.py --benchmark --no-regex-llm   # Jev-only baseline
uv run pytest tests/unit/test_jev_common.py -q                   # 89 pure-logic tests (incl. fuzzy-recall tests)
```

## Inspector (`--serve`)

A self-contained **FastAPI + PicoCSS** inspector (no templates dir, no static
files, no JS framework — PicoCSS via CDN + small inline JS) exposes every
model call a translation makes.  Open the page, type a query, and it shows:

- **Prompt structure (questions sent to Jev)** — the parsed question table
  (`id`, `type`, `instructions`/`question`/`goal`/`background`,
  `criteria`/options), derived from the captured `request.questions`.
- **LLM calls** — every captured model call, in order, each in its own
  `<details>` block (open for the Jev call, collapsed for the others) with a
  kind badge (`[jev]` / `[gemini]`), the request URL, the per-call latency,
  and the literal raw request and raw response payloads: the Jev
  `/v1/systemone` payload (`state`, `model`, per-question
  `instructions`/`criteria`/`type`) and the Gemini `generateContent`
  request/response (shown raw when the streaming response is not JSON).
- **Composed search parameters** — the full `SearchParameters.model_dump()`
  plus the composed `search_url`, resolved model, input/output tokens, and
  processing time.
- **REGEX LLM (Gemini)** — the **Jev gate decision** ("Jev gate: taste intent —
  Gemini called" vs "Jev gate: no taste intent — Gemini skipped"), the
  regex-field model, the structured `regex_fields` output, and a note when the
  LLM's `tasting_notes_search` overrode the Jev candidate path (or "disabled"
  under `--no-regex-llm`).  The `calls` list only contains the Gemini
  `generateContent` wire capture when the gate was open and the call actually
  happened.

```bash
PYTHONPATH=src uv run --with "pydantic-ai[typesafe]>=2.45" \
    python scripts/jev_native_prototype.py --serve --port 8765
# open http://127.0.0.1:8765/  (--host/--port override the 127.0.0.1:8765 default)
```

Routes: `GET /` (the page), `POST /api/translate` (`{"query": "..."}` returns
`request`, `response`, `question_table`, `calls`, `search_params`,
`search_url`, `resolved_model`, `regex_fields`, `needs_tasting_notes`,
`regex_llm_called`, `needs_origin`, `needs_region`, `needs_variety`,
`needs_farm`, `input_tokens`, `output_tokens`,
`processing_time_ms`), `GET /api/presets` (the golden-set queries for the
preset buttons).  The agent is built per request inside the async handler (the
pydantic-ai 2.x one-loop-per- client rule), reusing the exact same pipeline as
the CLI (`run_for_demo` → `filter_context_by_query` / `build_native_model` /
`run_native` / `compose_search_params`); Logfire spans (`jev.translate`,
mode=`serve`) are emitted as usual.  fastapi/uvicorn/httpx2 are imported only
inside the serve path, so normal CLI and `--benchmark` runs are byte-for-byte
unchanged.

**Wire capture (mechanism a)**: the TypeSafe provider is given a custom
`httpx2.AsyncClient` whose transport subclasses `httpx2.AsyncHTTPTransport`
and records every request/response body it carries, with a per-call
`duration_ms` (the SDK's `AsyncTypeSafeClient` honors the passed
`http_client`).  When the hybrid regex LLM is on, the **same** capture client
is also handed to `GoogleProvider`, so the Gemini `generateContent` request is
recorded too.  `_extract_capture` returns the full `calls` list — one entry
per recorded call, in order, each with `kind` (`jev` / `gemini` / `other` by
URL), `url`, `duration_ms`, and parsed-or-raw `request`/`response` — while the
legacy `request`/`response`/`question_table` keys still prefer the last
`/v1/systemone` call (falling back to the last non-Google call) so the Jev
question-table view keeps showing Jev.  A fresh (transport, client) pair is
created per translate request, so concurrent calls never clobber each other's
capture; the last recorded call (identical request body on retries) is
displayed.  No monkeypatching of the HTTP stack.

One environment note: the project pins `fastapi[all]>=0.100.0` (no upper
bound) while pydantic-ai 2.x requires `starlette>=1.3.1`, so the overlay can
resolve an older fastapi that does not support starlette 1.x (fastapi 0.116.x
+ starlette 1.7.x breaks `Router(on_startup=...)` and `FastAPI`'s `Request`
injection).  The serve path detects that mismatch and applies a two-spot
guarded compat shim (`Router.__init__` accepting the removed kwargs;
`max_body_size` defaulting) so the command above just works; a compatible pair
(resolve one with `--with fastapi`, or the project later pinning a newer
fastapi) is left untouched.

## Observability (Logfire)

Logfire tracing is **on by default** for single-query runs (token from
`LOGFIRE_TOKEN` in `.env`; `.env` is loaded via python-dotenv before
`logfire.configure(scrubbing=False)`).

**Compatible version combination** (established 2026-09-24): the project-pinned
**logfire 4.39.0** works with **pydantic-ai 2.x** out of the box —
`logfire.instrument_pydantic_ai()` succeeds because pydantic-ai 2.x still ships
`pydantic_ai.agent.InstrumentationSettings` (and `pydantic_ai.models.Model` /
`pydantic_ai.models.instrumented.InstrumentedModel`). In fact pydantic-ai 2.x
itself declares `logfire[httpx]>=4.39.0` as a dependency, so **4.39.0 is the
minimum compatible logfire** — no `--with logfire` overlay is needed (newer
logfire, e.g. 5.1.0, also works). The script still wraps
`instrument_pydantic_ai()` in try/except so a future logfire whose integration
drops the 1.x-era `InstrumentationSettings` import would only warn and fall back
to manual spans.

**What is traced** (only in the single-query path; `--benchmark` is not traced):

- `jev.translate` span wrapping context filtering + agent run + composition,
  with `query`, `backend="native"`, and the requested `model` pin as attributes.
- Span attributes set once known: resolved `model_name` (e.g. `jev-1.13.0`),
  `input_tokens`, `output_tokens`, `processing_time_ms`, `success`,
  `filtered_candidates` (sum of filtered candidate lists), and `search_url`.
- `jev.result` info event with the **non-default** `SearchParameters` fields
  (same field scan as `_synthesize_reasoning`, raw values).
- `jev.confidences` info event with the per-field confidences from
  `provider_details["confidence"]`.
- `jev.translate failed` error event (`error`, `error_type`, `query`) when the
  run raises; the span carries `success=false`.
- The pydantic-ai auto-instrumentation nests `agent run → chat <model>` spans
  under `jev.translate`.

The logfire console sink is routed to **stderr**
(`ConsoleOptions(output=sys.stderr)`), so `--json` stdout stays
machine-readable (`python -m json.tool` passes).

**Disabling tracing**: pass `--no-logfire`, or set `LOGFIRE_DISABLED=1` in the
environment. Both skip `configure` + `instrument_pydantic_ai` and the spans.
If logfire is not importable at all (e.g. a fully-isolated `--no-project` env
without logfire — unlikely in practice since pydantic-ai 2.x pulls it in), the
script prints a one-line warning to stderr and runs untraced; it never crashes
because of telemetry.

## Recommendation / next steps toward a repo-wide 2.x upgrade (Path B)

The native adapter is viable and removes any hand-rolled request/retry layer
entirely.  A repo-wide upgrade to pydantic-ai 2.x (Path B) should note these
API deltas discovered here:

- **`result.usage` is a property**, not a method (`result.usage()` → `result.usage`).
- **One event loop per client** — build the `Agent` (and thus the TypeSafe
  provider/client) *inside* the async function that runs it; constructing it at
  import time or in one loop and running in another fails.
- **Module moves**: `pydantic_ai.models.gemini` (GeminiModelSettings) is gone —
  `kissaten/ai/extractor.py` and `tasting_note_splitter.py` /
  `region_selector.py` / `podcast_tagger.py` import it and must migrate
  (likely `pydantic_ai.models.vertexai`/`pydantic_ai.providers.google` or the
  new `Agent(..., model_settings=...)` shape).  `TypeSafeModelSettings` lives at
  `pydantic_ai.models.typesafe`.
- **`kissaten/__init__.py` eagerly imports `.ai`** → any `import kissaten.*`
  breaks until the gemini imports are migrated; `jev_common` already contains
  the standalone-schema fallback that makes this harmless for the prototype.
- `list[Choices(...)]` multi-select and per-run `output_type=` overrides are
  supported in 2.48.0 — the dynamic-candidate pattern the native prototype uses
  can be carried straight into the production agent.
- The native prototype stays runnable via `uv run --with` while Path B is
  planned; no `pyproject.toml` change is required for it.

## Integration into the app

The prototype is now the production `jev` engine behind a runtime switch.

**Layout.** The pure/deterministic logic moved out of the script into
`src/kissaten/ai/jev/common.py` (`compose_search_params`, regex extraction,
gates, context filtering, benchmark data).  `src/kissaten/ai/jev/agent.py` holds
the Jev adapter (`run_native`, `build_native_model`, the regex-field LLM) and
the first-class application agent `JevSearchAgent`.  `src/kissaten/ai/search_engine.py`
is the switch/facade.  `scripts/jev_native_prototype.py` stays as the dev harness
(CLI, `--benchmark`, `--serve` inspector), reusing the same modules.

**The switch.** `KISSATEN_AI_SEARCH_ENGINE` (`llm` default | `jev`) is read at
import time into `search_engine.AI_SEARCH_ENGINE` (construction re-reads the env
so tests can monkeypatch the module attr).  `get_search_translator(conn)` returns
the `SearchTranslator` facade: text queries go to Jev when it is the configured
engine, image queries and any Jev init failure fall back to `AISearchAgent`.
Both engines share **one** `AISearchCache` instance (`_llm.cache` is passed to
Jev), since two DuckDB connections to the same cache file would contend.

**`BaseSearchTranslator` split.** `search_agent.py` now exposes an
engine-agnostic base owning orchestration — context acquisition, n-gram
filtering, origin/roaster normalization, search-URL generation, caching, rate
limiting — with a single engine hook `_produce_search_params`.  `AISearchAgent`
implements the Gemini-specific hook; `JevSearchAgent` implements the hybrid Jev
hook.  The facade is the only place that knows both engines exist.

**pydantic-ai 2.x.** `pyproject.toml` pins `pydantic-ai[typesafe]>=2.45,<3`; the
`1.x → 2.x` migration was required because the TypeSafe adapter and
`Choices(...)` dynamic candidates the Jev engine depends on (`result.usage` as a
property, `pydantic_ai.models.typesafe.TypeSafeModelSettings`) only exist in
2.x — the adapter is not available on 1.x.  `TypeSafeModelSettings` now takes
`decision_boolean_threshold` (the older `typesafe_boolean_threshold` is a
deprecated alias and emits `PydanticAIDeprecationWarning`).

**Benchmark status.** Hybrid golden run is **97/108** (origin **15/15**,
variety **6/6**), unchanged from the pre-integration prototype.  Live smoke on
`"fruity Ethiopian coffee under £25"`: `success=True`, `origin=['ET']`,
`tasting_notes_query=fruit*|berry*`, `max_price=25`.

**Known follow-ups.**

- The two `generate_search_url` implementations diverge: the app uses the base
  `BaseSearchTranslator._generate_search_url` (via `JevSearchAgent`'s inherited
  orchestration), while `jev_common.generate_search_url` omits the sort defaults
  and is **benchmark-only** — it is what `run_native` returns as `url` and what
  the harness scores.
- `use_regex_llm` is hard-coded `True` in `JevSearchAgent`; the
  `--no-regex-llm` Jev-only baseline is reachable only from the dev harness.
