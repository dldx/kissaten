"""TypeSafe Jev smart-search translator — native pydantic-ai TypeSafe adapter.

Single implementation of the Jev adapter, shared by the dev harness
(``scripts/jev_native_prototype.py``) and the application.  It uses pydantic-ai's
TypeSafe adapter (``Agent('typesafe:jev-latest', output_type=<pydantic model>)``)
to run TypeSafe's Jev System One model.  The output model is built per-query with
``pydantic.create_model`` — static ``Literal``/``bool`` fields plus dynamic
``Choices(...)`` candidate sets — and the adapter's primitive mapping guarantees
the model answers with structured semantics:

    pydantic type                        Jev primitive
    ---------------------------------    --------------
    bool                                 Noul
    Literal[str, ...] / Enum             Choice
    float = Field(ge=0, le=1)            probability
    IntEnum + UseEnumMemberDocstrings    Score
    list[Literal/Enum/Choices]           one Noul per option (multi-select)
    nested model fields                  dotted question paths
    Optional[Literal]                    Choice with auto-added ``None``

``Choices({name: desc, ...}, name=..., description=...)`` returns a TYPE usable
as a field annotation, so per-query candidate lists (roasters, varieties,
countries, ...) become per-run ``output_type=`` models.  State is derived from
the *user message* (the query + filtered-context text); ``instructions=``
becomes shared framing inside each question; per-field ``description`` IS the
question.

Then the SAME pure composition (``common.compose_search_params`` + deterministic
regex extraction) turns the answers into an identical
``SearchParameters``/``search_url``.  The pure/deterministic logic and the
benchmark data (``GOLDEN_SET``/``TRACKED_FIELDS``) live in
``kissaten.ai.jev.common``.

Hybrid split: by default the wildcard-grammar ``tasting_notes_search`` field is
composed by a second small Gemini agent (``gemini-2.5-flash-lite``, the same
model the production ``AISearchAgent`` uses) instead of being derived from Jev
candidate picks — pass ``use_regex_llm=False`` to disable the LLM and fall back
to the Jev note candidates, or ``regex_model=<name>`` to swap the model.  A Jev
``needs_tasting_notes`` noul gates that second call: when Jev says the query has
no taste intent (e.g. 'Standout ture waji', a roaster + producer lookup) Gemini
is skipped entirely and ``tasting_notes_search`` stays ``None``.

Candidate-choice gates: like ``needs_origin`` (in front of ``params.origin``),
three more nouls — ``needs_region`` / ``needs_variety`` / ``needs_farm`` — sit
in front of ``params.region`` / ``params.variety`` / ``params.farm`` composition
in ``compose_search_params``.  Each only composes the field when the query
*names* it: a whole country ('el salvador') is the coffee's origin, not a
region; a farm/estate name ('Kotowa', 'Finca el paraiso' -> 'Paraiso') is not a
region/variety.  ``producer`` stays ungated.

Requires ``TYPESAFE_API_KEY`` (and ``GOOGLE_API_KEY`` when the regex LLM is on)
in the environment; the harness loads them via python-dotenv.
"""

from __future__ import annotations

import os
import re
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from enum import IntEnum
from typing import Any, Literal

from pydantic import Field, create_model
from pydantic_ai import Agent, Choices, UseEnumMemberDocstrings
from pydantic_ai.models.typesafe import TypeSafeModelSettings

# Shared composition logic lives in the same package.
from kissaten.ai.jev.common import (
    NONE_OPTION,
    ORIGIN_GROUP_OPTIONS,
    ROAST_LEVEL_OPTIONS,
    SORT_FIELDS,
    SORT_ORDERS,
    _build_meta,
    _select_countries,
    _select_note_candidates,
    build_search_context,
    compose_search_params,
    filter_context_by_query,
    generate_search_url,
    sanitize_regex_value,
    wants_farm,
    wants_origin,
    wants_region,
    wants_tasting_notes,
    wants_variety,
)

from ..search_agent import BaseSearchTranslator

MODEL_PIN_DEFAULT = "jev-latest"
MODEL_PIN_ALT = "jev-1.13.0"

# Hybrid split: the wildcard-grammar fields (``tasting_notes_search`` today)
# are outsourced to a general LLM instead of being derived from Jev candidate
# picks.  Jev keeps every structured/enumerated field; Gemini composes the
# wildcard expression from the raw query.  ``REGEX_FIELDS`` is the extension
# point for moving other wildcard-capable fields (region / variety /
# roast_level) over later.
REGEX_MODEL_DEFAULT = "gemini-2.5-flash-lite"
REGEX_FIELDS = ("tasting_notes_search",)

REGEX_INSTRUCTIONS = """\
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
"""


# ---------------------------------------------------------------------------
# Logfire tracing (optional — never breaks --json output)
# ---------------------------------------------------------------------------
# Lazily imported so the module still works when logfire is absent (e.g. the
# fully-isolated `--no-project` variant without `--with logfire`).  The harness
# configures logfire (console sink routed to stderr so the JSON result on
# stdout stays machine-readable) and toggles ``LOGFIRE_ENABLED`` via
# ``set_logfire_enabled``; tracing decisions never break the pipeline itself.

try:
    import logfire as _logfire
except ImportError:  # pragma: no cover - exercised in the --no-project variant
    _logfire = None

# Module-level tracing flag.  The harness sets this from ``_setup_logfire``
# (which owns ``--no-logfire`` / ``LOGFIRE_DISABLED`` parsing and the
# ``logfire.configure`` / ``instrument_pydantic_ai`` calls).  Defaults to True
# so app callers that configure logfire themselves get spans.
LOGFIRE_ENABLED = True


def set_logfire_enabled(enabled: bool) -> None:
    """Enable/disable the manual spans emitted by this module (harness hook)."""
    global LOGFIRE_ENABLED
    LOGFIRE_ENABLED = enabled


@contextmanager
def _optional_span(name: str, **attributes: Any) -> Iterator[Any]:
    """``logfire.span`` that yields ``None`` when tracing is off (no-op)."""
    if not (LOGFIRE_ENABLED and _logfire is not None):
        yield None
        return
    with _logfire.span(name, **attributes) as span:
        yield span


def _logfire_info(message: str, **attributes: Any) -> None:
    """Emit a logfire info event when logfire is importable (no-op otherwise)."""
    if _logfire is not None:
        _logfire.info(message, **attributes)


def _logfire_error(message: str, **attributes: Any) -> None:
    """Emit a logfire error event when logfire is importable (no-op otherwise)."""
    if _logfire is not None:
        _logfire.error(message, **attributes)


def _non_default_params(params: Any) -> dict[str, Any]:
    """Non-default ``SearchParameters`` fields for the ``jev.result`` event.

    Mirrors the deterministic ``_synthesize_reasoning`` field scan but keeps the
    raw values instead of rendering them to text.
    """
    model = type(params)
    defaults = model()
    out: dict[str, Any] = {}
    for name in model.model_fields:
        if name in ("reasoning", "confidence"):
            continue
        value = getattr(params, name)
        if value != getattr(defaults, name):
            out[name] = value
    return out


# ---------------------------------------------------------------------------
# Static field option lists (same emitted strings as compose_search_params)
# ---------------------------------------------------------------------------

# ``SORT_FIELDS`` / ``SORT_ORDERS`` / ``ORIGIN_GROUP_OPTIONS`` are shared with
# the composition logic and imported from ``common`` above.
SINGLE_ORIGIN_OPTIONS = ["single_origin", "blend", NONE_OPTION]


def _literal_of(values: list[str]) -> Any:
    """Build ``Literal[<each value>]`` at runtime (no star-unpack on py3.10)."""
    return Literal.__getitem__(tuple(values))


class QuerySpecificity(UseEnumMemberDocstrings, IntEnum):
    """How specific is the query?"""

    NO_PREFERENCE = 0
    """No meaningful preference."""
    BROAD = 1
    """One broad preference."""
    CONCRETE = 2
    """Several concrete constraints."""


# Question text per field — becomes each field's ``description`` in the model.
_FIELD_QUESTIONS: dict[str, str] = {
    "roast_level": "Which roast level does the query ask for? Options are the exact emitted wildcard strings.",
    "sort_by": (
        "Which field should results be sorted by? Answer 'default' unless the query explicitly requests a sort "
        "(e.g. 'sorted by price', 'cheapest', 'best value', 'newest'). A price filter ('under £30'), a bag "
        "size ('large bag', '1kg'), or 'bulk' on its own is NOT a request to sort — answer 'default' for "
        "those. Only a clear ordering signal selects a field: 'cheapest'/'best value'/'sorted by price' on a "
        "bulk/1kg/large-bag query -> 'price_large', ordinary price sorting -> 'price', 'newest' -> "
        "'date_added'. Never guess a sort the query did not ask for."
    ),
    "sort_order": (
        "Which direction should results be sorted? Answer 'default' unless the query explicitly requests a "
        "direction. A price filter ('under £30'), a bag size ('large bag', '1kg'), or 'bulk' on its own is "
        "NOT a direction signal — answer 'default'. 'cheapest'/'lowest'/'best value' -> asc; 'newest'/'most "
        "expensive' -> desc; an explicit 'sorted by price'-style ordering phrase with no direction word "
        "also means asc (cheapest first). Never guess a direction the query did not ask for."
    ),
    "origin_group": (
        "Which broad origin group is the COFFEE from? Pick specific_country when a specific country is "
        "named, otherwise the continent it comes from (e.g. 'coffees from South America', 'African coffee'). "
        "Do NOT answer for the roaster's location: 'European roasters' / 'UK roasters' describe where the "
        "ROASTER is based — pick 'none' here and use roaster_location instead."
    ),
    "needs_origin": (
        "Does the query name the coffee's ORIGIN — the country, region, or continent the "
        "coffee comes from (e.g. 'Colombian coffee', 'Kenyan AA', 'Ethiopian', 'coffees from "
        "south america', 'coffees from asia', 'Indonesian coffee')? A country or region the "
        "coffee comes from ALWAYS opens the gate, even when the query also names a roaster, "
        "producer, farm, or varietal — e.g. 'Calico panama geisha kotowa' -> yes (Panama is "
        "the coffee's origin, even though Calico is the roaster and Kotowa the farm). Answer "
        "no when the only place words describe the ROASTER's location ('coffee from uk "
        "roasters', 'european roasters') or where it is available/shipped ('available in the "
        "US'), and no when the query only names a roaster, producer, farm, varietal, bean, "
        "process, roast level, price, or bag size without naming the coffee's origin "
        "country/region (e.g. 'Standout ture waji', 'Finca el paraiso', 'idido'). The "
        "coffee's origin is not the roaster's location."
    ),
    "needs_region": (
        "Does the query name a SUB-NATIONAL coffee region (e.g. 'Huila', 'Nariño', 'Yirgacheffe', 'Gedeb')? "
        "Answer no for a whole country ('Colombia', 'El Salvador', 'Kenya') — a country is the coffee's "
        "origin, handled separately, not a region — and no when the query only names a roaster, producer, "
        "farm, varietal, bean/lot, process, roast level, price, or bag size. A farm/estate name is NOT a "
        "region even when it also appears in the regions list: 'Calico panama geisha kotowa' names the "
        "Kotowa estate (a farm) in Panama — no sub-national region is named — answer no."
    ),
    "needs_variety": (
        "Does the query name a coffee VARIETAL (e.g. 'Pink Bourbon', 'geisha'/'gesha', 'Laurina', "
        "'Sudan Rume', 'SL9')? Answer no when the name is a roaster, producer, farm, bean/lot, product "
        "name, or origin rather than a varietal. In particular a name introduced by an estate word "
        "('Finca', 'Fazenda', 'Hacienda') is a FARM name, not a varietal: 'Finca el paraiso' names the "
        "farm/estate 'El Paraiso', not the 'Paraiso' varietal — answer no."
    ),
    "needs_farm": (
        "Does the query name a FARM or estate (e.g. 'Kotowa', 'Finca El Paraiso', 'Gara Agena')? "
        "Answer no when the name is a roaster, producer, varietal, bean/lot, region, or country."
    ),
    "is_flavour_query": "Is the query primarily a flavour/taste search (rather than a broader coffee search)?",
    "needs_tasting_notes": (
        "Does the query mention any specific taste, flavour, or tasting note worth searching "
        "tasting notes for (e.g. 'berry notes', 'taste like a pina colada', 'chocolate', "
        "'fruity', 'citrus', 'not bitter', 'mellow', 'complex tasting notes')? Answer no when "
        "the query is naming a bean/lot/product from the matched context lists — a roaster, "
        "producer, farm, varietal, region, or bean name — even when a flavour-looking word "
        "appears inside that name ('koke violet' = Koke producer/washing station + Violet "
        "lot, 'donna daisy' = producer, 'moby dick sl9' = roaster + lot), or when the query "
        "is only about origin, roast level, process, price, or bag size. Answer no for e.g. "
        "'Standout ture waji', 'Calico panama geisha kotowa', 'Finca el paraiso', 'idido', "
        "'donna daisy', 'koke violet', 'el salvador'."
    ),
    "notes_disjunctive": "Does the query want ANY of the mentioned flavours (OR) rather than ALL of them (AND)?",
    "has_max_price": "Does the query specify a maximum price (e.g. 'under £25')?",
    "has_min_price": "Does the query specify a minimum price (e.g. 'over $40')?",
    "has_large_bag": "Does the query ask for large bags / bulk options (1kg+ or 500g+ bags)?",
    "high_altitude": "Does the query ask for high-altitude coffee (e.g. 'high altitude', 'above 1800m')?",
    "is_decaf": "Does the query ask for decaffeinated coffee?",
    "is_single_origin": (
        "Does the query ask for single-origin or blend coffee? Answer 'single_origin' only if it asks for "
        "single-origin, 'blend' only if it asks for blends, and 'none' if the query does not mention "
        "single-origin or blends — never guess."
    ),
    "in_stock_only": "Does the query ask for in-stock coffee only?",
    "variety_spelling_variant": (
        "Does the query ask for a variety using an alternative spelling (e.g. geisha vs gesha)?"
    ),
    "process_excludes_anaerobic": (
        "Does the query explicitly exclude anaerobic processing (e.g. 'natural but not anaerobic')?"
    ),
}

_CHOICE_QUESTIONS: dict[str, str] = {
    "roaster": "Which roaster does the query ask for?",
    "origin_country": (
        "Which single origin country is the COFFEE from? Use only when the query names the coffee's country "
        "of origin (e.g. 'Ethiopian coffee', 'from Colombia'). Never use it for the roaster's location "
        "('european roasters', 'uk roasters') — that belongs to roaster_location."
    ),
    "variety": "Which coffee variety does the query ask for?",
    "process": "Which processing method does the query ask for?",
    "roaster_location": (
        "Which roaster location does the query ask for? Use when the query says where the ROASTER is based "
        "(e.g. 'uk roasters' -> United Kingdom, 'european roasters' -> Europe). This is about the roaster, "
        "not the coffee's origin."
    ),
    "region": "Which sub-national region does the query ask for?",
    "producer": "Which producer does the query ask for?",
    "farm": "Which farm does the query ask for?",
}

INSTRUCTIONS = (
    "You translate a natural-language coffee-search query into structured search "
    "parameters. The text under judgement is the query; judge only what it asks for. "
    "Pick the most specific candidate option that matches, or 'none' when nothing fits. "
    "Answer every field; booleans are yes/no judgements about the query text. "
    "Numeric extraction (prices, weights, elevation) is handled deterministically — "
    "you only judge whether a bound exists. "
    "Distinguish the coffee's origin (origin_group/origin_country) from the roaster's "
    "location (roaster_location); 'European roasters' is a roaster location, not an origin. "
    "Never infer filters or sort orders the query does not state; leave them at their "
    "'none'/'default' value."
)


# ---------------------------------------------------------------------------
# Regex-field LLM (hybrid split: Jev for structured fields, Gemini for the
# wildcard-grammar fields such as ``tasting_notes_search``)
# ---------------------------------------------------------------------------


async def run_regex_fields(
    query: str,
    model_name: str = REGEX_MODEL_DEFAULT,
    http_client: Any | None = None,
) -> dict[str, Any]:
    """Compose the wildcard-grammar fields (e.g. ``tasting_notes_search``) via Gemini.

    Returns a ``dict`` mapping each ``REGEX_FIELDS`` name to its emitted
    wildcard expression (or ``None`` when the query has no flavour preference).
    Missing ``GOOGLE_API_KEY`` degrades to ``{}`` (caller falls back to the Jev
    candidate path).  ``http_client`` is only used by the web inspector (a
    capturing ``httpx2.AsyncClient``); GoogleModel/GoogleProvider are lazily
    imported so the CLI/benchmark import set stays unchanged.
    """
    if not os.environ.get("GOOGLE_API_KEY"):
        print(
            "warning: GOOGLE_API_KEY missing; skipping regex-field LLM "
            "(tasting_notes_search falls back to Jev candidates)",
            file=sys.stderr,
        )
        return {}
    from pydantic_ai.models.google import GoogleModel
    from pydantic_ai.providers.google import GoogleProvider

    provider = GoogleProvider(http_client=http_client) if http_client is not None else GoogleProvider()
    model = GoogleModel(model_name, provider=provider)
    regex_model_type = create_model("RegexFields", **{f: (str | None, Field(None)) for f in REGEX_FIELDS})
    agent = Agent(model, output_type=regex_model_type, instructions=REGEX_INSTRUCTIONS)
    with _optional_span("jev.regex", query=query, model=model_name, fields=list(REGEX_FIELDS)) as span:
        result = await agent.run(query)
        out = {f: sanitize_regex_value(v) for f, v in result.output.model_dump().items()}
        if span is not None:
            span.set_attribute("model_name", result.response.model_name)
            span.set_attribute("success", True)
        _logfire_info("jev.regex.result", **out)
        return out


# ---------------------------------------------------------------------------
# Context prompt (mirror the section labels the Gemini pipeline uses)
# ---------------------------------------------------------------------------

_CONTEXT_SECTIONS: list[tuple[str, str]] = [
    ("MATCHED TASTING NOTES", "tasting_notes"),
    ("MATCHED VARIETALS (canonical names — use these directly)", "varietals"),
    ("MATCHED ROASTERS", "roasters"),
    ("MATCHED PROCESSES", "processes"),
    ("MATCHED FARMS", "farms"),
    ("MATCHED PRODUCERS", "producers"),
    ("MATCHED REGIONS", "regions"),
    ("ROAST LEVELS", "roast_levels"),
    ("COFFEE ORIGIN COUNTRIES", "countries"),
    ("ROASTER LOCATIONS", "roaster_locations"),
]


def build_context_prompt(query: str, filtered: dict[str, list[str]]) -> str:
    """Render the filtered context as text, mirroring the Gemini prompt layout.

    The native adapter derives ``state`` from the user message, so the context
    must be embedded in the prompt itself (there is no structured ``state=``).
    """
    context_sections = []
    for label, key in _CONTEXT_SECTIONS:
        items = filtered.get(key) or []
        if items:
            context_sections.append(f"{label}:\n{', '.join(items)}")
    context_body = (
        "\n\n".join(context_sections)
        if context_sections
        else (
            "No matching database entries found for query keywords. "
            "Use your coffee knowledge to generate appropriate search parameters."
        )
    )
    return (
        f"User Query: {query}\n\n{context_body}\n\n"
        "Please analyze the user query and generate appropriate search parameters."
    )


# ---------------------------------------------------------------------------
# Per-query output model
# ---------------------------------------------------------------------------


def _loc_options(filtered: dict[str, list[str]]) -> tuple[list[str], dict[str, str]]:
    """Parse 'GB (United Kingdom)' style entries into (codes, descriptions).

    Option keys stay the codes — the search URL needs the code — but each
    description is human-readable so Jev can tell the options apart:
    countries become ``"United Kingdom (GB)"``, while regional groupings
    (``XE``/``XF``/... and ``EU``) get explicit scope so a query like
    "european roasters" picks ``XE`` rather than a single country.
    """
    codes: list[str] = []
    descriptions: dict[str, str] = {}
    for loc in filtered.get("roaster_locations") or []:
        m = re.match(r"^(\w+)\s*\((.*)\)\s*$", loc)
        if not m:
            continue
        code, name = m.group(1), m.group(2).strip()
        if code in codes:
            continue
        codes.append(code)
        if code.startswith("X"):
            descriptions[code] = f"{name} \u2014 all roasters in {name} ({code})"
        else:
            descriptions[code] = f"{name} ({code})"
    return codes, descriptions


def _choices(options: list[str], descriptions: dict[str, str] | None, name: str, question: str) -> Any:
    """Build a dynamic ``Choices`` type over per-query candidates + explicit none."""
    criteria = {opt: (descriptions.get(opt, opt) if descriptions else str(opt)) for opt in options}
    criteria[NONE_OPTION] = "Nothing fits / not in the query."
    return Choices(criteria, name=name, description=question)


def build_native_model(
    query: str,
    filtered: dict[str, list[str]],
    context: Any,
    top_notes: int = 8,
    include_tasting_notes: bool = True,
) -> tuple[type, dict[str, Any]]:
    """Build (output_model, meta) for ONE query.

    ``meta`` maps the note-slug question ids back to human note names exactly
    like ``common._build_meta``, so ``compose_search_params``
    consumes the same shape.  ``include_tasting_notes=False`` (the hybrid
    mode where a general LLM owns the tasting-note expression) skips the whole
    tasting-note candidate block so Jev is never asked about notes.
    """
    if include_tasting_notes:
        note_candidates = _select_note_candidates(
            filtered.get("tasting_notes") or [], context.available_tasting_notes, query, top_notes
        )
        meta = _build_meta(filtered, top_notes, notes=note_candidates)
    else:
        note_candidates = []
        meta = _build_meta(filtered, top_notes, notes=[])

    fields: dict[str, tuple[Any, Any]] = {}

    # --- static Literal fields (choice primitives) -------------------------
    fields["roast_level"] = (
        _literal_of(ROAST_LEVEL_OPTIONS),
        Field(description=_FIELD_QUESTIONS["roast_level"]),
    )
    fields["sort_by"] = (_literal_of(SORT_FIELDS), Field(description=_FIELD_QUESTIONS["sort_by"]))
    fields["sort_order"] = (_literal_of(SORT_ORDERS), Field(description=_FIELD_QUESTIONS["sort_order"]))
    fields["origin_group"] = (
        _literal_of(ORIGIN_GROUP_OPTIONS),
        Field(description=_FIELD_QUESTIONS["origin_group"]),
    )
    fields["is_single_origin"] = (
        _literal_of(SINGLE_ORIGIN_OPTIONS),
        Field(description=_FIELD_QUESTIONS["is_single_origin"]),
    )

    # --- dynamic Choices fields (candidate sets) ---------------------------
    # The adapter requires a Choice to have >= 2 options.  When a query yields
    # an empty candidate list, the only representable choice would be "none"
    # (deterministic None) — the native equivalent is to OMIT
    # the field, which compose treats identically (missing answer -> None).
    # ``origin_country`` / ``roaster_location`` always have >= 1 candidate in a
    # real DB (full small lists are always included by filter_context_by_query).
    roasters = (filtered.get("roasters") or [])[:20]
    if roasters:
        fields["roaster"] = (
            _choices(roasters, None, "roaster", _CHOICE_QUESTIONS["roaster"]),
            Field(description=_CHOICE_QUESTIONS["roaster"]),
        )

    countries = _select_countries(context, query)
    country_options = [c.country_code for c in countries]
    country_desc = {c.country_code: f"{c.country_full_name} ({c.country_code})" for c in countries}
    fields["origin_country"] = (
        _choices(country_options, country_desc, "origin_country", _CHOICE_QUESTIONS["origin_country"]),
        Field(description=_CHOICE_QUESTIONS["origin_country"]),
    )

    varietals = (filtered.get("varietals") or [])[:20]
    if varietals:
        fields["variety"] = (
            _choices(varietals, None, "variety", _CHOICE_QUESTIONS["variety"]),
            Field(description=_CHOICE_QUESTIONS["variety"]),
        )
    processes = (filtered.get("processes") or [])[:20]
    if processes:
        fields["process"] = (
            _choices(processes, None, "process", _CHOICE_QUESTIONS["process"]),
            Field(description=_CHOICE_QUESTIONS["process"]),
        )
    loc_codes, loc_desc = _loc_options(filtered)
    if loc_codes:
        fields["roaster_location"] = (
            _choices(loc_codes, loc_desc, "roaster_location", _CHOICE_QUESTIONS["roaster_location"]),
            Field(description=_CHOICE_QUESTIONS["roaster_location"]),
        )
    regions = (filtered.get("regions") or [])[:20]
    if regions:
        fields["region"] = (
            _choices(regions, None, "region", _CHOICE_QUESTIONS["region"]),
            Field(description=_CHOICE_QUESTIONS["region"]),
        )
    producers = (filtered.get("producers") or [])[:20]
    if producers:
        fields["producer"] = (
            _choices(producers, None, "producer", _CHOICE_QUESTIONS["producer"]),
            Field(description=_CHOICE_QUESTIONS["producer"]),
        )
    farms = (filtered.get("farms") or [])[:20]
    if farms:
        fields["farm"] = (
            _choices(farms, None, "farm", _CHOICE_QUESTIONS["farm"]),
            Field(description=_CHOICE_QUESTIONS["farm"]),
        )

    # --- tasting notes ------------------------------------------------------
    # Skipped entirely when include_tasting_notes=False (the hybrid mode where
    # a general LLM owns the tasting-note expression).  Otherwise: preferred
    # dynamic multi-select via list[Choices(...)] (proven live: one Noul per
    # option, output = selected note names).  The adapter rejects a list whose
    # Choices has < 2 options, so with 0-1 note candidates we fall back to
    # per-candidate bool fields note_<slug> / exclude_<slug> (which the
    # adapter supports for any count and compose reads identically).
    if include_tasting_notes:
        if len(note_candidates) >= 2:
            note_pick = Choices(
                {note: f'The flavour note "{note}".' for note in note_candidates},
                name="tasting_notes",
                description="Every flavour note the query requests, if any.",
            )
            fields["tasting_notes"] = (
                list[note_pick],
                Field(description="Every flavour note the query requests (multi-select; empty when none)."),
            )
            fields["excluded_notes"] = (
                list[note_pick],
                Field(description="Every flavour note the query explicitly excludes (multi-select; empty when none)."),
            )
        else:
            for slug, note in meta["note_slugs"].items():
                fields[f"note_{slug}"] = (
                    bool,
                    Field(description=f'Does the query request the flavour "{note}" (or a close synonym)?'),
                )
                fields[f"exclude_{slug}"] = (
                    bool,
                    Field(description=f'Does the query explicitly exclude the flavour "{note}"?'),
                )

    # --- query specificity -> Score (IntEnum 0..2) --------------------------
    fields["query_specificity"] = (
        QuerySpecificity,
        Field(description="How specific is the query?"),
    )

    # --- static bool fields (noul primitives) -------------------------------
    for qid, question in _FIELD_QUESTIONS.items():
        if qid in fields or qid == "roast_level":
            continue
        fields[qid] = (bool, Field(description=question))

    # force insertion order (only for fields that exist for this query)
    ordered: dict[str, tuple[Any, Any]] = {}
    for name in (
        "roast_level",
        "sort_by",
        "sort_order",
        "needs_origin",
        "origin_group",
        "roaster",
        "origin_country",
        "variety",
        "needs_variety",
        "process",
        "roaster_location",
        "region",
        "needs_region",
        "producer",
        "farm",
        "needs_farm",
        "tasting_notes",
        "excluded_notes",
        "needs_tasting_notes",
        "is_flavour_query",
        "notes_disjunctive",
        "has_max_price",
        "has_min_price",
        "has_large_bag",
        "high_altitude",
        "is_decaf",
        "is_single_origin",
        "in_stock_only",
        "variety_spelling_variant",
        "process_excludes_anaerobic",
        "query_specificity",
    ):
        if name in fields:
            ordered[name] = fields[name]
    # note_<slug>/exclude_<slug> bool fallbacks (when <2 note candidates)
    for name in fields:
        if name.startswith(("note_", "exclude_")):
            ordered[name] = fields[name]

    model = create_model(
        "JevNative",
        __doc__=(
            "Translate a natural-language coffee-search query into structured search "
            "parameters; judge only what the query asks for."
        ),
        **ordered,
    )
    return model, meta


# ---------------------------------------------------------------------------
# Adapter -> answers dict conversion
# ---------------------------------------------------------------------------

# Field-name -> (compose question id, kind).  Kinds: "choice", "bool".
_BOOL_FIELDS = [
    "is_flavour_query",
    "needs_tasting_notes",
    "needs_origin",
    "needs_region",
    "needs_variety",
    "needs_farm",
    "notes_disjunctive",
    "has_max_price",
    "has_min_price",
    "has_large_bag",
    "high_altitude",
    "is_decaf",
    "in_stock_only",
    "variety_spelling_variant",
    "process_excludes_anaerobic",
]

_CHOICE_FIELDS = [
    "roaster",
    "origin_country",
    "origin_group",
    "variety",
    "process",
    "roast_level",
    "roaster_location",
    "region",
    "producer",
    "farm",
    "sort_by",
    "sort_order",
    "is_single_origin",
]


def native_to_answers(output: Any, meta: dict[str, Any]) -> dict[str, Any]:
    """Convert ``result.output`` into the ``answers`` dict shape compose expects.

    Mapping (documented for review):
      * choice fields (Literal / Choices) -> ``{"type": "choice", "choice": <str>}``
        — the adapter returns the chosen option key; ``"none"`` is interpreted
        by ``compose_search_params`` exactly like a ``None`` answer.
        Fields omitted from the model (empty candidate set) are absent here,
        which compose treats identically to a ``None`` answer.
      * bool fields (Noul) -> ``{"type": "noul", "noul": 1.0|0.0}`` — the adapter
        already thresholded the raw noul at 0.5 (``decision_boolean_threshold``),
        so mapping the *output boolean* to 1.0/0.0 reproduces the identical
        decision deterministically (``compose`` only checks ``> 0.5``).
      * tasting notes: with >= 2 candidates the model has ``tasting_notes`` /
        ``excluded_notes`` ``list[Choices]`` fields -> per-slug ``note_<slug>`` /
        ``exclude_<slug>`` nouls; with 0-1 candidates the model itself has
        per-slug bool fields that map straight to nouls.
      * query_specificity (IntEnum Score) -> ``{"type": "score", "score": float}``
    """
    answers: dict[str, Any] = {}

    for qid in _CHOICE_FIELDS:
        if hasattr(output, qid):
            answers[qid] = {"type": "choice", "choice": getattr(output, qid)}

    for qid in _BOOL_FIELDS:
        answers[qid] = {"type": "noul", "noul": 1.0 if getattr(output, qid) else 0.0}

    if hasattr(output, "tasting_notes"):  # list[Choices] branch (>= 2 candidates)
        selected = set(getattr(output, "tasting_notes") or [])
        excluded = set(getattr(output, "excluded_notes") or [])
        for slug, note in meta.get("note_slugs", {}).items():
            answers[f"note_{slug}"] = {"type": "noul", "noul": 1.0 if note in selected else 0.0}
            answers[f"exclude_{slug}"] = {"type": "noul", "noul": 1.0 if note in excluded else 0.0}
    else:  # per-slug bool fallback (< 2 candidates)
        for slug in meta.get("note_slugs", {}):
            if hasattr(output, f"note_{slug}"):
                answers[f"note_{slug}"] = {"type": "noul", "noul": 1.0 if getattr(output, f"note_{slug}") else 0.0}
            if hasattr(output, f"exclude_{slug}"):
                answers[f"exclude_{slug}"] = {
                    "type": "noul",
                    "noul": 1.0 if getattr(output, f"exclude_{slug}") else 0.0,
                }

    answers["query_specificity"] = {"type": "score", "score": float(int(output.query_specificity))}
    return answers


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


async def run_native(
    query: str,
    filtered: dict[str, list[str]],
    context: Any,
    model_pin: str = MODEL_PIN_DEFAULT,
    top_notes: int = 8,
    http_client: Any | None = None,
    use_regex_llm: bool = True,
    regex_model: str = REGEX_MODEL_DEFAULT,
) -> dict[str, Any]:
    """Run one query through the native adapter; returns a result dict.

    ``http_client`` is only used by the web inspector: a capturing
    ``httpx2.AsyncClient`` whose transport records the raw ``/v1/systemone``
    request/response bodies (and, when ``use_regex_llm``, the Gemini
    ``generateContent`` call too).  When ``None`` (the CLI/benchmark paths) the
    agent is built exactly as before — string model id, no extra imports.

    Hybrid split: when ``use_regex_llm`` the tasting-note questions are dropped
    from the Jev model (``include_tasting_notes=False``) and the wildcard
    ``tasting_notes_search`` expression comes from ``run_regex_fields``
    (``regex_fields``); the Jev candidate expression is only used as the
    fallback when the LLM is disabled or fails.
    """
    model, meta = build_native_model(
        query, filtered, context, top_notes, include_tasting_notes=not use_regex_llm
    )
    if http_client is None:
        agent = Agent(
            f"typesafe:{model_pin}",
            output_type=model,
            instructions=INSTRUCTIONS,
            model_settings=TypeSafeModelSettings(decision_boolean_threshold=0.5),
        )
    else:
        # Lazy: pydantic_ai.providers.typesafe pulls in httpx2, which the
        # CLI/benchmark paths never need.
        from pydantic_ai.models.typesafe import TypeSafeModel
        from pydantic_ai.providers.typesafe import TypeSafeProvider

        agent = Agent(
            TypeSafeModel(model_pin, provider=TypeSafeProvider(http_client=http_client)),
            output_type=model,
            instructions=INSTRUCTIONS,
            model_settings=TypeSafeModelSettings(decision_boolean_threshold=0.5),
        )
    start = time.monotonic()
    result = await agent.run(build_context_prompt(query, filtered))
    latency_ms = (time.monotonic() - start) * 1000

    answers = native_to_answers(result.output, meta)

    # Jev gate: only ask Gemini to compose the wildcard tasting-note expression
    # when Jev itself says the query has taste intent.  When the gate is closed
    # (e.g. 'Standout ture waji' — the salient words are roaster/producer names)
    # the LLM is skipped entirely: no network call, and the Jev candidate path
    # is not used either (the tasting-note questions were dropped from the
    # model, so compose finds no notes and emits None).
    needs_tasting_notes = wants_tasting_notes(answers)
    regex_llm_called = bool(use_regex_llm and needs_tasting_notes)

    # Jev origin gate: ``needs_origin`` decides whether ``params.origin`` is
    # composed at all (mirrors the ``needs_tasting_notes`` gate; consumed by
    # ``compose_search_params``).
    needs_origin = wants_origin(answers)
    needs_region = wants_region(answers)
    needs_variety = wants_variety(answers)
    needs_farm = wants_farm(answers)

    regex_fields: dict[str, Any] = {}
    if regex_llm_called:
        try:
            regex_fields = await run_regex_fields(query, regex_model, http_client)
        except Exception as exc:  # noqa: BLE001
            _logfire_error(
                "jev.regex failed",
                query=query,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            print(
                f"warning: regex-field LLM failed ({type(exc).__name__}: {exc}); "
                "tasting_notes_search falls back to Jev candidates",
                file=sys.stderr,
            )
            regex_fields = {}

    params = compose_search_params(query, answers, context, filtered, meta, regex_fields=regex_fields)
    usage = result.usage  # property in pydantic-ai 2.x (not a method)
    return {
        "filtered": filtered,
        "answers": answers,
        "params": params,
        "url": generate_search_url(params),
        "model_name": result.response.model_name,
        "provider_details": dict(result.response.provider_details or {}),
        "usage": usage,
        "latency_ms": latency_ms,
        "output": result.output,
        "regex_fields": regex_fields,
        "needs_tasting_notes": needs_tasting_notes,
        "regex_llm_called": regex_llm_called,
        "needs_origin": needs_origin,
        "needs_region": needs_region,
        "needs_variety": needs_variety,
        "needs_farm": needs_farm,
    }


# ---------------------------------------------------------------------------
# Application adapter (first-class alternative to AISearchAgent)
# ---------------------------------------------------------------------------


class JevSearchAgent(BaseSearchTranslator):
    """TypeSafe Jev engine for translating queries to structured search parameters.

    Text-only: the Jev model takes a text prompt, so image queries must be
    routed to ``AISearchAgent`` by the ``SearchTranslator`` facade.  Shares the
    base orchestration (caching, rate limiting, origin/roaster normalization,
    search-URL generation) with the Gemini engine.
    """

    def __init__(
        self,
        database_connection: Any,
        api_key: str | None = None,
        cache_db_path: str | None = None,
        cache: Any | None = None,
        model_pin: str | None = None,
        regex_model: str | None = None,
        top_notes: int = 8,
    ) -> None:
        super().__init__(database_connection, api_key=api_key, cache_db_path=cache_db_path, cache=cache)
        if not os.getenv("TYPESAFE_API_KEY"):
            raise ValueError(
                "TYPESAFE_API_KEY required for the Jev search engine. "
                "Set TYPESAFE_API_KEY or use KISSATEN_AI_SEARCH_ENGINE=llm."
            )
        self.model_pin = model_pin
        self.regex_model = regex_model
        self.top_notes = top_notes

    async def _build_context(self) -> Any:
        """Build the search context straight from the DB (no Gemini context query)."""
        return build_search_context(self.conn)

    async def _produce_search_params(self, query: str | None, image_data: bytes | None, context: Any) -> Any:
        """Run the hybrid Jev pipeline and return its composed ``SearchParameters``."""
        if image_data is not None:
            # Defensive: the facade routes images to AISearchAgent, so this
            # documents the text-only contract rather than firing in production.
            raise NotImplementedError(
                "JevSearchAgent is text-only; image queries must be routed to AISearchAgent."
            )
        assert query is not None  # query is always present for the text path
        filtered = filter_context_by_query(query, context)
        result = await run_native(
            query,
            filtered,
            context,
            model_pin=self.model_pin or MODEL_PIN_DEFAULT,
            top_notes=self.top_notes,
            use_regex_llm=True,
            regex_model=self.regex_model or REGEX_MODEL_DEFAULT,
        )
        return result["params"]
