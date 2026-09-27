"""Shared pure/DB logic for the Jev smart-search prototype (native pydantic-ai TypeSafe adapter).

Deliberately dependency-free: **stdlib + pydantic + ``kissaten.schemas.ai_search``
only**, plus **``rapidfuzz``** (already a project dependency, used by
``kissaten.dedup.matcher``) for the Jaro-Winkler typo recall in the candidate
lists.  No ``pydantic_ai``, no ``kissaten.ai.search_agent``.

The native prototype (``scripts/jev_native_prototype.py``) imports this module
as ``kissaten.ai.jev.common`` and runs under the project's pydantic-ai 2.x
installation; the schemas come from the normal package import and are the *same*
objects the rest of the codebase uses.

The public surface mirrors the helpers the production ``AISearchAgent`` exposes
(``_strip_accents``, ``_generate_query_ngrams``, ``_filter_context_by_query``,
``_resolve_canonical_roasters``, ``_generate_search_url``, ``get_search_context``)
plus the prototype's pure composition logic (``compose_search_params`` and the
candidate-selection helpers) and the shared benchmark data.
"""

from __future__ import annotations

import os
import re
import unicodedata
from typing import Any
from urllib.parse import urlencode

from rapidfuzz import process
from rapidfuzz.distance import JaroWinkler

from kissaten.schemas.ai_search import Country, SearchContext, SearchParameters

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NOUL_THRESHOLD = 0.5

# Choice options must stay <= 255; every choice gets an explicit "none" option
# so "nothing fits" is representable.
NONE_OPTION = "none"

SORT_FIELDS = ["date_added", "price", "price_large", "name", "cupping_score", "relevance", "default"]
SORT_ORDERS = ["asc", "desc", "default"]

# Minimum number of DB mentions for a region / farm / producer name to be
# offered as a selector candidate.  Scraper extraction errors (countries
# mislabeled as regions, one-off junk names) inflate the long tail; a name seen
# fewer than this many times is treated as unreliable and excluded.  Override
# for experiments with ``KISSATEN_MIN_ENTITY_MENTIONS``.
MIN_ENTITY_MENTIONS = int(os.environ.get("KISSATEN_MIN_ENTITY_MENTIONS", "2"))

# Jaro-Winkler threshold for typo recall in candidate lists: n-grams that got
# no substring match fall back to fuzzy matching (e.g. "larina" -> "Laurina"
# 0.85, "borbon" -> "Bourbon" 0.85); measured non-varietal false positives sit
# at 0.80-0.81 ("berry" -> "Peaberry" 0.81, "natural" -> "Caturra" 0.81).
NAME_FUZZY_MIN = 0.82

# Emitted wildcard strings (not bare DB values) — the same strings Gemini emits.
ROAST_LEVEL_OPTIONS = [
    "Light",
    "Light|Medium-Light|Medium",
    "Medium-Light",
    "Medium",
    "Medium|Medium-Dark",
    "Medium-Dark",
    "Dark",
    "Extra-Light",
    NONE_OPTION,
]

# Continent -> country-code expansions.  The south_america / asia lists are
# copied verbatim from the existing Gemini prompt's EXAMPLES block; the others
# are sensible curated lists for the remaining continents.
CONTINENT_CODES: dict[str, list[str]] = {
    "south_america": [
        "CO",
        "PE",
        "PA",
        "GT",
        "CR",
        "NI",
        "SV",
        "HN",
        "DO",
        "BR",
        "EC",
        "BO",
        "AR",
        "CL",
        "UY",
        "PY",
        "VE",
        "GY",
        "SR",
    ],
    "central_america": ["PA", "GT", "CR", "NI", "SV", "HN", "MX", "BZ"],
    "caribbean": ["DO", "CU", "JM", "HT", "TT", "PR"],
    "north_america": ["US", "CA", "MX"],
    "africa": ["ET", "KE", "RW", "UG", "TZ", "MW", "ZM", "ZW", "AO", "CD", "NG", "GH", "CI", "SN", "BJ", "MG"],
    "asia": ["IN", "ID", "VN", "TH", "MY", "PH", "CN", "TW", "JP", "KR", "LK", "PG"],
    "oceania": ["AU", "NZ", "PG"],
    "europe": [
        "GB",
        "DE",
        "FR",
        "IT",
        "ES",
        "PT",
        "NL",
        "BE",
        "CH",
        "AT",
        "SE",
        "NO",
        "DK",
        "FI",
        "IE",
        "PL",
        "CZ",
        "GR",
    ],
    "specific_country": [],
    NONE_OPTION: [],
}

ORIGIN_GROUP_OPTIONS = list(CONTINENT_CODES.keys())

PRICE_MAX_RE = re.compile(
    r"\b(?:under|below|max(?:imum)?|less than|cheaper than|no more than|at most)\b", re.IGNORECASE
)
PRICE_MIN_RE = re.compile(r"\b(?:over|above|at least|more than|min(?:imum)?)\b", re.IGNORECASE)
AMOUNT_RE = re.compile(r"(?:[£$€]\s*)?(\d+(?:\.\d+)?)")
WEIGHT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|grams?|gr)\b", re.IGNORECASE)
ELEVATION_RE = re.compile(r"(\d{3,4})\s*(?:m(?:asl)?|meters?|metres?)\b", re.IGNORECASE)
GEISHA_RE = re.compile(r"gei?sha", re.IGNORECASE)

_WILDCARD_OPERATOR_CHARS = frozenset("&|!()*?")

# Common words that are too generic to be useful for context filtering (copied
# verbatim from AISearchAgent._STOPWORDS).
STOPWORDS = frozenset(
    {
        "coffee",
        "beans",
        "bean",
        "with",
        "from",
        "that",
        "this",
        "like",
        "notes",
        "flavor",
        "flavors",
        "taste",
        "tasting",
        "find",
        "show",
        "any",
        "some",
        "for",
        "the",
        "and",
        "but",
        "not",
        "or",
        "want",
        "looking",
        "need",
        "please",
        "help",
        "me",
        "you",
        "are",
        "was",
    }
)

# Golden set copied verbatim from search_agent.py EXAMPLE_QUERIES (lines 569-653).
GOLDEN_SET: list[dict[str, Any]] = [
    {
        "query": "Find me coffee beans that taste like a pina colada",
        "expected": {
            "tasting_notes_search": "pineapple&coconut",
            "use_tasting_notes_only": True,
            "is_single_origin": None,
            "confidence": 0.9,
        },
    },
    {
        "query": "light roast pink bourbon",
        "expected": {
            "roast_level": "Light",
            "variety": "Pink Bourbon",
            "use_tasting_notes_only": False,
            "is_single_origin": None,
            "tasting_notes_search": None,
            "origin": None,
            "region": None,
            "confidence": 0.95,
        },
    },
    {
        "query": "fruity Ethiopian coffee under £25",
        "expected": {
            "tasting_notes_search": "fruit*|berry*",
            "origin": ["ET"],
            "max_price": 25.0,
            "use_tasting_notes_only": True,
            "region": None,
            "farm": None,
            "confidence": 0.85,
        },
    },
    {
        "query": "cartwheel natural process with chocolate notes",
        "expected": {
            "roaster": ["Cartwheel Coffee"],
            "process": "Natural",
            "tasting_notes_search": "chocolate",
            "use_tasting_notes_only": True,
            "variety": None,
            "confidence": 0.7,
        },
    },
    {
        "query": "chocolate coffee that's not bitter",
        "expected": {"tasting_notes_search": "chocolate&!bitter", "use_tasting_notes_only": True, "confidence": 0.8},
    },
    {
        "query": "high altitude Colombian coffee with citrus flavors above 1800m",
        "expected": {
            "search_text": "Colombian",
            "tasting_notes_search": "citrus*|lemon*|orange*|tangerine*|lime*",
            "origin": ["CO"],
            "min_elevation": 1800,
            "use_tasting_notes_only": False,
            "confidence": 0.95,
        },
    },
    {
        "query": "coffee from uk roasters",
        "expected": {
            "roaster_location": ["GB"],
            "origin": None,
            "use_tasting_notes_only": False,
            "is_single_origin": None,
            "tasting_notes_search": None,
            "confidence": 0.9,
        },
    },
    {
        "query": "light roast from european roasters with berry notes",
        "expected": {
            "tasting_notes_search": "berry*",
            "roast_level": "Light",
            "roaster_location": ["XE"],
            "origin": None,
            "use_tasting_notes_only": False,
            "confidence": 0.85,
        },
    },
    {
        "query": "Kenyan AA with wine-like acidity",
        "expected": {
            "search_text": "AA",
            "tasting_notes_search": "wine*|acidic*",
            "origin": ["KE"],
            "use_tasting_notes_only": False,
            "is_single_origin": None,
            "confidence": 0.9,
        },
    },
    {
        "query": "Colombian coffee from Huila or Nariño regions, natural or honey process",
        "expected": {
            "origin": ["CO"],
            "region": "Huila|Nariño",
            "process": "Natural|Honey",
            "use_tasting_notes_only": False,
            "confidence": 0.95,
        },
    },
    {
        "query": "any geisha variety with light to medium roast",
        "expected": {
            "variety": "Ge*sha",
            "roast_level": "Light|Medium-Light|Medium",
            "use_tasting_notes_only": False,
            "tasting_notes_search": None,
            "origin": None,
            "confidence": 0.9,
        },
    },
    {
        "query": "Indonesian coffee that is not chocolatey",
        "expected": {
            "tasting_notes_search": "!chocolate&!cocoa",
            "origin": ["ID"],
            "use_tasting_notes_only": True,
            "confidence": 0.85,
        },
    },
    {
        "query": "coffees from south america",
        "expected": {
            "origin": [
                "CO",
                "PE",
                "PA",
                "GT",
                "CR",
                "NI",
                "SV",
                "HN",
                "DO",
                "BR",
                "EC",
                "BO",
                "AR",
                "CL",
                "UY",
                "PY",
                "VE",
                "GY",
                "SR",
            ],
            "use_tasting_notes_only": False,
            "is_single_origin": None,
            "tasting_notes_search": None,
            "confidence": 0.9,
        },
    },
    {
        "query": "coffees from asia",
        "expected": {
            "origin": ["IN", "ID", "VN", "TH", "MY", "PH", "CN", "TW", "JP", "KR", "LK", "PG"],
            "use_tasting_notes_only": False,
            "confidence": 0.9,
        },
    },
    {
        "query": "cheapest bulk options",
        "expected": {
            "sort_by": "price_large",
            "sort_order": "asc",
            "min_large_weight": 1000,
            "use_tasting_notes_only": False,
            "is_single_origin": None,
            "tasting_notes_search": None,
            "confidence": 0.95,
        },
    },
    {
        "query": "1kg bags sorted by price",
        "expected": {
            "min_large_weight": 1000,
            "sort_by": "price_large",
            "sort_order": "asc",
            "use_tasting_notes_only": False,
            "confidence": 0.95,
        },
    },
    {
        "query": "large bag options under £30",
        "expected": {
            "min_large_weight": 500,
            "max_price": 30.0,
            "sort_by": "default",
            "sort_order": "default",
            "use_tasting_notes_only": False,
            "confidence": 0.9,
        },
    },
    {
        "query": "best value large bags",
        "expected": {
            "min_large_weight": 1000,
            "sort_by": "price_large",
            "sort_order": "asc",
            "use_tasting_notes_only": False,
            "confidence": 0.9,
        },
    },
    {
        "query": "single origin coffees",
        "expected": {"is_single_origin": True, "origin": None},
    },
    {
        "query": "blends only",
        "expected": {"is_single_origin": False, "origin": None},
    },
    # NEGATIVE EXAMPLES (only the ✓ lines are the expected outcome).
    {
        "query": "panama geisha",
        "expected": {"origin": ["PA"], "variety": "Ge*sha"},
    },
    {
        "query": "sudan rume",
        "expected": {"variety": "Sudan Rume"},
    },
    {
        "query": "killbean panama geisha",
        "expected": {"roaster": ["KillBean"], "origin": ["PA"], "variety": "Ge*sha"},
    },
]

TRACKED_FIELDS = [
    "search_text",
    "tasting_notes_search",
    "use_tasting_notes_only",
    "roaster",
    "variety",
    "process",
    "origin",
    "region",
    "farm",
    "roast_level",
    "roaster_location",
    "min_price",
    "max_price",
    "min_weight",
    "max_weight",
    "min_large_weight",
    "min_elevation",
    "max_elevation",
    "is_decaf",
    "is_single_origin",
    "in_stock_only",
    "sort_by",
    "sort_order",
    "confidence",
]


# ---------------------------------------------------------------------------
# Context filtering helpers (mirror AISearchAgent, no class needed)
# ---------------------------------------------------------------------------


def strip_accents(text: str) -> str:
    """Remove combining diacritics so 'cafēn' matches 'cafen'."""
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def is_country_name(value: str, country_names_normalized: set[str]) -> bool:
    """True when a candidate name is actually a country name (scraper mislabel).

    Region extraction sometimes stores the country (e.g. ``"Colombia"``) in the
    ``region`` column.  Comparing the accent/case-normalised value against the
    ``country_codes`` names lets ``build_search_context`` drop those rows so
    they are never offered as region candidates.
    """
    return bool(value) and strip_accents(value.strip().lower()) in country_names_normalized


def generate_query_ngrams(query: str) -> list[str]:
    """Generate n-grams from a query string for context filtering."""
    words = [strip_accents(w) for w in re.findall(r"[^\W\d_]+", query.lower())]
    single_grams = [w for w in words if len(w) >= 4 and w not in STOPWORDS]
    ngrams: list[str] = []
    for n in range(min(len(words), 4), 1, -1):
        for i in range(len(words) - n + 1):
            ngrams.append(" ".join(words[i : i + n]))
    ngrams.extend(single_grams)
    return ngrams


def fuzzy_matches(
    ngram: str, items: list[str], threshold: float = NAME_FUZZY_MIN, limit: int = 20
) -> list[str]:
    """Return items whose Jaro-Winkler similarity to ``ngram`` is >= threshold, best first.

    Pure typo recall for the candidate lists: when an n-gram has no substring
    match, ``filter_context_by_query`` falls back to this so a misspelled
    entity name still surfaces the canonical candidate (e.g. "larina" ->
    "Laurina", "giesha" -> "Gesha", "borbon" -> "Bourbon").
    """
    matches = process.extract(
        ngram,
        items,
        scorer=JaroWinkler.normalized_similarity,
        score_cutoff=threshold,
        limit=limit,
    )
    return [item for item, _score, _index in matches]


def filter_context_by_query(query: str, context: SearchContext, limit_per_list: int = 20) -> dict[str, list[str]]:
    """Filter context lists to only items relevant to the query keywords.

    Each list keeps its n-gram substring matches (sorted by longest match, then
    alphabetically) and, per n-gram fallback, any item whose Jaro-Winkler
    similarity to an *unmatched* n-gram is >= ``NAME_FUZZY_MIN`` (best fuzzy
    score wins, ranked below substring matches).  The ``varietals`` /
    ``farms`` / ``producers`` / ``regions`` lists also drop any candidate that
    is actually a country name (scraper mislabel guard, see ``is_country_name``).
    """
    ngrams = generate_query_ngrams(query)
    # Accent/case-normalised country names once per call; varietals / farms /
    # producers / regions must never offer a bare country name as a candidate
    # (e.g. "Ethiopia" appearing as a "variety" in the DB).
    country_names_normalized = {
        strip_accents(c.country_full_name.strip().lower()) for c in context.available_countries
    }

    def filter_list(items: list[str], apply_country_guard: bool = False) -> list[str]:
        if not items or not ngrams:
            return []
        item_lowers = [strip_accents(item.lower()) for item in items]
        best_len = [0] * len(items)
        matched_ngrams: set[str] = set()
        for i, item_lower in enumerate(item_lowers):
            for ngram in ngrams:
                if ngram in item_lower:
                    best_len[i] = max(best_len[i], len(ngram))
                    matched_ngrams.add(ngram)
        # Per-ngram fuzzy fallback: only n-grams that matched NO item are tried
        # against the whole list; each returned item records its best score.
        fuzzy_score = [0.0] * len(items)
        index = {strip_accents(item.lower()): i for i, item in enumerate(items)}
        for ngram in ngrams:
            if ngram in matched_ngrams:
                continue
            for match in fuzzy_matches(ngram, items):
                i = index.get(strip_accents(match.lower()))
                if i is not None:
                    score = JaroWinkler.normalized_similarity(ngram, match)
                    fuzzy_score[i] = max(fuzzy_score[i], score)
        kept: list[tuple[int, float, str]] = []
        for i, item in enumerate(items):
            if best_len[i] > 0 or fuzzy_score[i] >= NAME_FUZZY_MIN:
                if apply_country_guard and is_country_name(item, country_names_normalized):
                    continue
                kept.append((best_len[i], fuzzy_score[i], item))
        kept.sort(key=lambda x: (-x[0], -x[1], x[2]))
        return [item for _, _, item in kept[:limit_per_list]]

    return {
        "tasting_notes": filter_list(context.available_tasting_notes),
        "varietals": filter_list(context.available_varietals, apply_country_guard=True),
        "roasters": filter_list(context.available_roasters),
        "processes": filter_list(context.available_processes),
        "farms": filter_list(context.available_farms, apply_country_guard=True),
        "producers": filter_list(context.available_producers, apply_country_guard=True),
        "regions": filter_list(context.available_regions, apply_country_guard=True),
        "roast_levels": context.available_roast_levels,
        "countries": [f"{c.country_full_name} ({c.country_code})" for c in context.available_countries],
        "roaster_locations": context.available_roaster_locations,
    }


def resolve_canonical_roasters(names: list[str], canonical_roasters: list[str]) -> list[str]:
    """Same accent/case-insensitive mapping as AISearchAgent._resolve_canonical_roasters."""
    lookup = {strip_accents(r.lower()): r for r in canonical_roasters}
    return [lookup.get(strip_accents(n.lower()), n) for n in names]


# ---------------------------------------------------------------------------
# Candidate selection (shared by both prototypes)
# ---------------------------------------------------------------------------


def _slugify(name: str) -> str:
    """Deterministic slug for a tasting-note name (used in question ids)."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "note"


def _select_countries(context: SearchContext, query: str, max_options: int = 200) -> list[Country]:
    """Pick the countries offered as ``origin_country`` choice options.

    The Choice primitive caps at 255 options.  The real DB has 79 countries,
    well under the cap, so the full list is used.  If a database ever grows
    past ``max_options`` we fall back to n-gram matches + a curated sample.
    """
    countries = context.available_countries
    if len(countries) <= max_options:
        return countries
    ngrams = generate_query_ngrams(query)
    matched = [c for c in countries if any(g in f"{c.country_full_name} {c.country_code}".lower() for g in ngrams)]
    return matched or countries[: max_options - 1]


def _matches_content_word(note: str, content_words: list[str]) -> bool:
    """True if a note is plausibly about one of the query's content words."""
    lower = note.lower()
    if any(w in lower for w in content_words):
        return True
    tokens = [t for t in re.split(r"[^a-z0-9]+", lower) if len(t) >= 4]
    return any(w.startswith(t) or t.startswith(w) for w in content_words for t in tokens)


def _select_note_candidates(
    filtered_notes: list[str], all_notes: list[str], query: str, top_notes: int = 8
) -> list[str]:
    """Pick the tasting-note candidates offered to the Jev questions.

    ``filtered_notes`` (the n-gram-matched list) is the primary pool, but its
    alphabetical tiebreak lets long compound labels ("70% Dark Chocolate") crowd
    out the plain canonical notes ("Chocolate", "Bitter").  We therefore:
      1. always augment the pool with simple (<=2-word) notes from the full
         list that relate to a content word of the query, and
      2. rank candidates so simpler (fewer-word) notes come first.
    """
    content_words = [w for w in generate_query_ngrams(query) if " " not in w]
    candidates = list(dict.fromkeys(filtered_notes))

    def wordiness(note: str) -> tuple[int, int]:
        return len(note.split()), len(note)

    if content_words:
        seen = set(candidates)
        for note in all_notes:
            if note in seen:
                continue
            if wordiness(note)[0] <= 2 and _matches_content_word(note, content_words):
                candidates.append(note)
                seen.add(note)
                if len(candidates) >= 60:  # bound the ranking work; top-8 is all we emit
                    break

    ranked = sorted(enumerate(candidates), key=lambda t: (wordiness(t[1])[0], wordiness(t[1])[1], t[0]))
    return [note for _, note in ranked[:top_notes]]


def _build_meta(filtered: dict[str, list[str]], top_notes: int = 8, notes: list[str] | None = None) -> dict[str, Any]:
    """Metadata mapping question ids back to the values they refer to."""
    if notes is None:
        notes = (filtered.get("tasting_notes") or [])[:top_notes]
    note_slugs: dict[str, str] = {}
    for note in notes:
        note_slugs.setdefault(_slugify(note), note)  # first occurrence wins on slug collisions
    return {
        "top_notes": list(note_slugs.values()),
        "note_slugs": note_slugs,
    }


# ---------------------------------------------------------------------------
# Answer interpretation (PURE — unit-testable, no network / DB)
# ---------------------------------------------------------------------------


def _get_noul(answers: dict[str, Any], qid: str, default: bool = False) -> bool:
    ans = answers.get(qid)
    if not ans or not isinstance(ans, dict):
        return default
    return ans.get("noul", 0.0 if default is False else 1.0) > NOUL_THRESHOLD


def _get_choice(answers: dict[str, Any], qid: str) -> str | None:
    ans = answers.get(qid)
    if not ans or not isinstance(ans, dict):
        return None
    choice = ans.get("choice")
    return choice if choice and choice != NONE_OPTION else None


def _get_score(answers: dict[str, Any], qid: str) -> float | None:
    ans = answers.get(qid)
    if not ans or not isinstance(ans, dict):
        return None
    score = ans.get("score")
    return float(score) if score is not None else None


def wants_tasting_notes(answers: dict[str, Any]) -> bool:
    """True when the Jev gate field says this query has taste intent.

    The ``needs_tasting_notes`` noul is the gate in front of the regex-field
    Gemini call: when it is False (the only salient words are roaster /
    producer / farm / varietal / bean names, or the query is only about
    origin / roast / process / price / bag size) the LLM is skipped entirely.
    Missing answer -> False (``_get_noul`` default).
    """
    return _get_noul(answers, "needs_tasting_notes")


def wants_origin(answers: dict[str, Any]) -> bool:
    """True when the Jev gate field says this query names a coffee origin.

    The ``needs_origin`` noul is the gate in front of ``params.origin``
    composition: when it is False — the only place words describe the
    ROASTER's location or availability/shipping, or the query only names a
    roaster / producer / farm / varietal / bean / process / roast / price /
    bag size — no origin filter is composed even if ``origin_group`` /
    ``origin_country`` picked something.  Missing answer -> False
    (``_get_noul`` default).
    """
    return _get_noul(answers, "needs_origin")


def wants_region(answers: dict[str, Any]) -> bool:
    """True when the Jev gate field says this query names a sub-national region.

    The ``needs_region`` noul is the gate in front of ``params.region``
    composition: when it is False — the query names a whole country (a
    country is the coffee's origin, not a region), or only names a roaster,
    producer, farm, varietal, bean/lot, process, roast level, price, or bag
    size — no region filter is composed even if the ``region`` choice picked
    a candidate.  Missing answer -> False (``_get_noul`` default).
    """
    return _get_noul(answers, "needs_region")


def wants_variety(answers: dict[str, Any]) -> bool:
    """True when the Jev gate field says this query names a coffee varietal.

    The ``needs_variety`` noul is the gate in front of ``params.variety``
    composition: when it is False — the name is a roaster, producer, farm,
    bean/lot, product name, or origin rather than a varietal — no variety
    filter is composed even if the ``variety`` choice picked a candidate.
    Missing answer -> False (``_get_noul`` default).
    """
    return _get_noul(answers, "needs_variety")


def wants_farm(answers: dict[str, Any]) -> bool:
    """True when the Jev gate field says this query names a farm/estate.

    The ``needs_farm`` noul is the gate in front of ``params.farm``
    composition: when it is False — the name is a roaster, producer,
    varietal, bean/lot, region, or country rather than a farm — no farm
    filter is composed even if the ``farm`` choice picked a candidate.
    Missing answer -> False (``_get_noul`` default).
    """
    return _get_noul(answers, "needs_farm")


def sanitize_regex_value(value: Any) -> str | None:
    """Normalise a regex-LLM string: strip, and treat null-ish/sentinel output as None.

    The regex-field LLM occasionally answers with the literal strings
    ``"null"`` / ``"none"`` / ``"*"`` (or whitespace-padded text).  Those are
    truthy strings and would otherwise reach ``compose_search_params`` as a
    real ``tasting_notes_search`` expression.  Rules: ``None`` -> ``None``;
    non-str -> ``str(value)``; ``value.strip()``; empty or a casefolded
    null-ish/sentinel value -> ``None``; otherwise the stripped string.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    stripped = value.strip()
    if not stripped or stripped.casefold() in {"null", "none", "n/a", "na", "nil", "*"}:
        return None
    return stripped


def _parse_price(query: str, pattern: re.Pattern[str]) -> float | None:
    """Extract the amount near the first max/min keyword in the query."""
    m = pattern.search(query)
    if not m:
        return None
    lo = max(0, m.start() - 15)
    hi = min(len(query), m.end() + 25)
    window = query[lo:hi]
    am = AMOUNT_RE.search(window)
    if not am:
        return None
    return round(float(am.group(1)), 2)


def _parse_weights(query: str, has_large_bag: bool) -> tuple[int | None, int | None, int | None]:
    """Return (min_large_weight, min_weight, max_weight) from explicit amounts."""
    min_large = None
    min_w = None
    max_w = None
    for m in WEIGHT_RE.finditer(query):
        grams = int(round(float(m.group(1)) * (1000 if m.group(2).lower() == "kg" else 1)))
        window = query[max(0, m.start() - 30) : m.end() + 10].lower()
        if has_large_bag and grams >= 500:
            min_large = max(min_large or 0, grams)
        elif re.search(r"under|below|less than|max", window):
            max_w = max(max_w or 0, grams)
        elif re.search(r"over|above|at least|more than|min", window):
            min_w = max(min_w or 0, grams)
    return min_large, min_w, max_w


def _parse_elevation(query: str, high_altitude: bool) -> tuple[int | None, int | None]:
    """Return (min_elevation, max_elevation) from explicit amounts + 'high altitude'."""
    min_elev = None
    max_elev = None
    for m in ELEVATION_RE.finditer(query):
        elev = int(m.group(1))
        if elev > 3000:  # schema caps elevation at 3000
            continue
        window = query[max(0, m.start() - 20) : m.end() + 5].lower()
        if re.search(r"above|over|at least|high|min", window):
            min_elev = max(min_elev or 0, elev)
        elif re.search(r"below|under|max", window):
            max_elev = max(max_elev or 0, elev)
        else:  # bare "1800m" → treat as "at least"
            min_elev = max(min_elev or 0, elev)
    if min_elev is None and high_altitude:
        min_elev = 1500
    return min_elev, max_elev


def _synthesize_reasoning(params: SearchParameters) -> str:
    """Deterministic one-line reasoning listing the non-default fields."""
    defaults = SearchParameters()
    parts = []
    for name in SearchParameters.model_fields:
        if name in ("reasoning", "confidence"):
            continue
        value = getattr(params, name)
        if value != getattr(defaults, name):
            if isinstance(value, list):
                rendered = ",".join(value)
            else:
                rendered = str(value)
            parts.append(f"{name}={rendered}")
    return "Jev: " + ", ".join(parts) if parts else "Jev: no specific filters"


def _paren_if_needed(term: str) -> str:
    """Wrap a tasting-note term in parentheses when it contains wildcard operators.

    The DB stores compound note labels such as "Bright & Fruity"; emitted
    bare, the ``&`` would be parsed by the search backend as the AND operator,
    silently corrupting the expression.  ``()`` grouping keeps such labels a
    single alternative (the wildcard grammar supports it).
    """
    if any(ch in term for ch in _WILDCARD_OPERATOR_CHARS):
        return f"({term})"
    return term


def _dedupe_substrings(terms: list[str]) -> list[str]:
    """Drop near-duplicate note labels, keeping the most specific one.

    Jev often says "yes" to both "Choc" and "Chocolate" (or "Bitter" and
    "Bitterness").  Since the backend matches substrings case-insensitively,
    a term that is a substring of another kept term is redundant — keep the
    longer, more specific label.
    """
    kept: list[str] = []
    for term in sorted(terms, key=lambda s: -len(s)):
        if any(term.lower() in kept_term.lower() for kept_term in kept):
            continue
        kept.append(term)
    return kept


def _validate_origin(codes: list[str], context: SearchContext) -> list[str] | None:
    """Full-name→code fixup, drop codes not in the DB, dedupe, empty→None."""
    valid_codes = {c.country_code for c in context.available_countries}
    name_to_code = {c.country_full_name: c.country_code for c in context.available_countries}
    fixed = []
    for code in codes:
        if len(code) != 2:
            code = name_to_code.get(code, code)
        if code in valid_codes and code not in fixed:
            fixed.append(code)
    return fixed or None


def compose_search_params(
    query: str,
    answers: dict[str, Any],
    context: SearchContext,
    filtered: dict[str, list[str]],
    meta: dict[str, Any] | None = None,
    regex_fields: dict[str, Any] | None = None,
) -> SearchParameters:
    """Interpret Jev answers (+ deterministic regex extraction) into SearchParameters.

    Pure function: no network, no DB.  ``meta`` maps note slugs back to names;
    when omitted it is rebuilt from ``filtered``.

    ``regex_fields`` carries structured values produced by an external
    wildcard-expression LLM (the hybrid split: Jev for structured/enumerated
    fields, Gemini for the wildcard-grammar fields).  When it supplies a
    ``tasting_notes_search`` value that wins over the candidate-derived
    expression; when ``None``/empty the Jev note-candidate path is used
    unchanged.
    """
    if meta is None:
        meta = _build_meta(filtered)
    params = SearchParameters()

    def noul(qid: str) -> bool:
        return _get_noul(answers, qid)

    def choice(qid: str) -> str | None:
        return _get_choice(answers, qid)

    # --- tasting notes -----------------------------------------------------
    # Hybrid split: the regex-field LLM's expression (if any) wins outright;
    # otherwise fall back to the Jev note-candidate expression unchanged.
    regex_notes = (regex_fields or {}).get("tasting_notes_search")
    if regex_notes:
        params.tasting_notes_search = regex_notes
    else:
        include_notes = [note for slug, note in meta.get("note_slugs", {}).items() if noul(f"note_{slug}")]
        exclude_notes = [note for slug, note in meta.get("note_slugs", {}).items() if noul(f"exclude_{slug}")]
        includes = [_paren_if_needed(n) for n in _dedupe_substrings(include_notes)]
        excludes = [_paren_if_needed(n) for n in _dedupe_substrings(exclude_notes)]
        if includes or excludes:
            if len(includes) == 1 and not excludes:
                expr = includes[0]
            else:
                parts = []
                if includes:
                    joiner = "|" if noul("notes_disjunctive") else "&"
                    parts.append(joiner.join(includes))
                parts.extend(f"!{e}" for e in excludes)
                expr = "&".join(parts)
            params.tasting_notes_search = expr
    params.use_tasting_notes_only = noul("is_flavour_query")

    # --- roaster -----------------------------------------------------------
    roaster = choice("roaster")
    if roaster:
        params.roaster = resolve_canonical_roasters([roaster], context.available_roasters)

    # --- origin ------------------------------------------------------------
    # The ``needs_origin`` noul gates origin composition: when Jev says the
    # query never names the coffee's origin (only roaster location /
    # availability, or roaster/producer/farm/varietal/bean names), no origin
    # filter is composed even if origin_group/origin_country picked something.
    if noul("needs_origin"):
        group = choice("origin_group")
        country = choice("origin_country")
        if group == "specific_country":
            codes = [country] if country else []
        elif group and group in CONTINENT_CODES and group != NONE_OPTION:
            codes = list(CONTINENT_CODES[group])
        else:
            codes = []
        params.origin = _validate_origin(codes, context)
    else:
        params.origin = None

    # --- variety -----------------------------------------------------------
    # The ``needs_variety`` noul gates variety composition: when Jev says the
    # name is a roaster / producer / farm / bean / product / origin rather
    # than a varietal, no variety filter is composed even if the ``variety``
    # choice picked a candidate.
    if noul("needs_variety"):
        variety = choice("variety")
        if variety:
            if noul("variety_spelling_variant") or GEISHA_RE.search(query):
                variety = "Ge*sha"  # prototype: only the geisha/gesha fuzzy case
            params.variety = variety

    # --- process -----------------------------------------------------------
    process = choice("process")
    if process:
        if noul("process_excludes_anaerobic"):
            process = f"{process}&!Anaerobic"
        params.process = process

    # --- roast level / location / region / producer / farm -----------------
    roast_level = choice("roast_level")
    if roast_level:
        params.roast_level = roast_level
    location = choice("roaster_location")
    if location:
        params.roaster_location = [location]
    # The ``needs_region`` noul gates region composition: when Jev says the
    # query names a whole country (origin, not region) or only a roaster /
    # producer / farm / varietal / bean / process / roast / price / bag size,
    # no region filter is composed even if the ``region`` choice picked a
    # candidate.
    if noul("needs_region"):
        region = choice("region")
        if region:
            params.region = region
    producer = choice("producer")
    if producer:
        params.producer = producer
    # The ``needs_farm`` noul gates farm composition: when Jev says the name
    # is a roaster, producer, varietal, bean/lot, region, or country rather
    # than a farm/estate, no farm filter is composed even if the ``farm``
    # choice picked a candidate.
    if noul("needs_farm"):
        farm = choice("farm")
        if farm:
            params.farm = farm

    # --- price -------------------------------------------------------------
    if noul("has_max_price"):
        max_price = _parse_price(query, PRICE_MAX_RE)
        if max_price is not None:
            params.max_price = max_price
    if noul("has_min_price"):
        min_price = _parse_price(query, PRICE_MIN_RE)
        if min_price is not None:
            params.min_price = min_price

    # --- weights -----------------------------------------------------------
    min_large, min_w, max_w = _parse_weights(query, noul("has_large_bag"))
    if min_large is not None:
        params.min_large_weight = min_large
    elif noul("has_large_bag"):
        # No explicit amount: "bulk"/"best value" → 1000, "large bag" → 500.
        lowered = query.lower()
        if "best value" in lowered or re.search(r"\bbulk\b|cheapest", lowered):
            params.min_large_weight = 1000
        elif "large bag" in lowered or "big bag" in lowered:
            params.min_large_weight = 500
    if min_w is not None:
        params.min_weight = min_w
    if max_w is not None:
        params.max_weight = max_w

    # --- elevation ---------------------------------------------------------
    min_elev, max_elev = _parse_elevation(query, noul("high_altitude"))
    params.min_elevation = min_elev
    params.max_elevation = max_elev

    # --- booleans ----------------------------------------------------------
    params.is_decaf = True if noul("is_decaf") else None
    single_origin = choice("is_single_origin")
    if single_origin == "single_origin":
        params.is_single_origin = True
    elif single_origin == "blend":
        params.is_single_origin = False
    else:
        params.is_single_origin = None
    params.in_stock_only = noul("in_stock_only")

    # --- sort --------------------------------------------------------------
    sort_by = choice("sort_by")
    sort_order = choice("sort_order")
    params.sort_by = "date_added" if sort_by in (None, "default") else sort_by
    params.sort_order = "desc" if sort_order in (None, "default") else sort_order

    # --- confidence --------------------------------------------------------
    specificity = _get_score(answers, "query_specificity")
    if specificity is None:
        confidence = 0.8
    else:
        confidence = min(0.95, 0.7 + 0.125 * specificity)
    params.confidence = round(confidence, 3)

    # --- reasoning ---------------------------------------------------------
    params.reasoning = _synthesize_reasoning(params)
    return params


# ---------------------------------------------------------------------------
# Context acquisition (DB)
# ---------------------------------------------------------------------------


def build_search_context(conn: Any) -> SearchContext:
    """Build SearchContext directly from the DB.

    Mirrors the SQL in ``AISearchAgent.get_search_context`` so the prototypes
    work without a Gemini key.  ``conn`` is any object exposing
    ``execute(sql).fetchall()`` (a read-only duckdb connection).
    """
    tasting_notes = [
        row[0]
        for row in conn.execute(
            """
            SELECT DISTINCT unnest(tasting_notes) as note
            FROM coffee_beans
            WHERE tasting_notes IS NOT NULL AND array_length(tasting_notes) > 0
            ORDER BY note
            """
        ).fetchall()
        if row[0]
    ]
    varietals = [
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT c FROM origins, UNNEST(variety_canonical) AS t(c) "
            "WHERE c IS NOT NULL AND c != '' ORDER BY c"
        ).fetchall()
        if row[0]
    ]
    roasters = [
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT roaster FROM coffee_beans WHERE roaster IS NOT NULL AND roaster != '' ORDER BY roaster"
        ).fetchall()
        if row[0]
    ]
    processes = [
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT process_common_name FROM origins "
            "WHERE process_common_name IS NOT NULL AND process_common_name != '' ORDER BY process_common_name"
        ).fetchall()
        if row[0]
    ]
    roast_levels = [
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT roast_level FROM coffee_beans "
            "WHERE roast_level IS NOT NULL AND roast_level != '' ORDER BY roast_level"
        ).fetchall()
        if row[0]
    ]
    countries = []
    for code, name in conn.execute(
        """
        SELECT DISTINCT o.country as country_code, cc.name as country_name
        FROM origins o
        LEFT JOIN country_codes cc ON o.country = cc.alpha_2
        WHERE o.country IS NOT NULL AND o.country != ''
        ORDER BY cc.name, o.country
        """
    ).fetchall():
        countries.append(Country(country_full_name=name or code, country_code=code))
    roaster_locations = [
        f"{code} ({location})"
        for code, location, _region in conn.execute(
            "SELECT rlc.code, rlc.location, rlc.region FROM roaster_location_codes rlc ORDER BY rlc.location"
        ).fetchall()
    ]
    farms = [
        row[0]
        for row in conn.execute(
            "SELECT farm FROM origins WHERE farm IS NOT NULL AND farm != '' "
            "GROUP BY farm HAVING COUNT(*) >= ? ORDER BY farm",
            [MIN_ENTITY_MENTIONS],
        ).fetchall()
        if row[0]
    ]
    producers = [
        row[0]
        for row in conn.execute(
            "SELECT producer FROM origins WHERE producer IS NOT NULL AND producer != '' "
            "GROUP BY producer HAVING COUNT(*) >= ? ORDER BY producer",
            [MIN_ENTITY_MENTIONS],
        ).fetchall()
        if row[0]
    ]
    # Region extraction sometimes stores a country name (e.g. "Colombia") in the
    # region column; drop those scraper mislabels so they are never offered.
    country_names_normalized = {
        strip_accents(name.strip().lower())
        for (name,) in conn.execute(
            "SELECT name FROM country_codes WHERE name IS NOT NULL AND name != ''"
        ).fetchall()
        if name
    }
    regions = [
        row[0]
        for row in conn.execute(
            "SELECT region FROM origins WHERE region IS NOT NULL AND region != '' "
            "GROUP BY region HAVING COUNT(*) >= ? ORDER BY region",
            [MIN_ENTITY_MENTIONS],
        ).fetchall()
        if row[0] and not is_country_name(row[0], country_names_normalized)
    ]
    return SearchContext(
        available_tasting_notes=tasting_notes,
        available_varietals=varietals,
        available_roasters=roasters,
        available_processes=processes,
        available_roast_levels=roast_levels,
        available_countries=countries,
        available_roaster_locations=roaster_locations,
        available_farms=farms,
        available_producers=producers,
        available_regions=regions,
    )


# ---------------------------------------------------------------------------
# Search URL (mirror AISearchAgent._generate_search_url)
# ---------------------------------------------------------------------------


def generate_search_url(params: SearchParameters) -> str:
    """Generate a search URL from the structured parameters."""
    url_params = {}

    if params.search_text:
        url_params["q"] = params.search_text

    if params.tasting_notes_search:
        url_params["tasting_notes_query"] = params.tasting_notes_search

    if params.roaster:
        for roaster in params.roaster:
            if isinstance(url_params.get("roaster"), list):
                url_params.setdefault("roaster", []).append(roaster)
            else:
                url_params.update({"roaster": roaster})

    if params.roaster_location:
        for location in params.roaster_location:
            if "roaster_location" not in url_params:
                url_params["roaster_location"] = []
            url_params["roaster_location"].append(location)

    if params.variety:
        url_params["variety"] = params.variety

    if params.process:
        url_params["process"] = params.process

    if params.origin:
        for origin in params.origin:
            if "origin" not in url_params:
                url_params["origin"] = []
            url_params["origin"].append(origin)

    if params.region:
        url_params["region"] = params.region
    if params.producer:
        url_params["producer"] = params.producer
    if params.farm:
        url_params["farm"] = params.farm

    if params.roast_level:
        url_params["roast_level"] = params.roast_level
    if params.roast_profile:
        url_params["roast_profile"] = params.roast_profile

    if params.min_price is not None:
        url_params["min_price"] = str(params.min_price)
    if params.max_price is not None:
        url_params["max_price"] = str(params.max_price)
    if params.min_weight is not None:
        url_params["min_weight"] = str(params.min_weight)
    if params.min_large_weight is not None:
        url_params["min_large_weight"] = str(params.min_large_weight)
    if params.max_weight is not None:
        url_params["max_weight"] = str(params.max_weight)
    if params.min_elevation is not None:
        url_params["min_elevation"] = str(params.min_elevation)
    if params.max_elevation is not None:
        url_params["max_elevation"] = str(params.max_elevation)

    if params.in_stock_only:
        url_params["in_stock_only"] = "true"
    if params.is_decaf is not None:
        url_params["is_decaf"] = "true" if params.is_decaf else "false"
    if params.is_single_origin is not None:
        url_params["is_single_origin"] = "true" if params.is_single_origin else "false"

    if params.sort_by != "date_added":
        url_params["sort_by"] = params.sort_by
    if params.sort_order != "desc":
        url_params["sort_order"] = params.sort_order

    query_parts = []
    for key, value in url_params.items():
        if isinstance(value, list):
            for v in value:
                query_parts.append(f"{key}={urlencode({'': v})[1:]}")
        else:
            query_parts.append(f"{key}={urlencode({'': value})[1:]}")

    return f"/search?{'&'.join(query_parts)}" if query_parts else "/search"


# ---------------------------------------------------------------------------
# Benchmark comparison helpers
# ---------------------------------------------------------------------------


def field_matches(field: str, got: Any, expected: Any) -> bool:
    if field == "tasting_notes_search":
        # Wildcard expressions: compare case-insensitively with only outer
        # whitespace stripped — inner spacing/operator order is significant.
        return (got or "").strip().casefold() == (expected or "").strip().casefold()
    if field == "sort_by" and expected == "default":
        return got == "date_added"
    if field == "sort_order" and expected == "default":
        return got == "desc"
    if field == "confidence":
        return isinstance(got, int | float) and isinstance(expected, int | float) and abs(got - expected) <= 0.15
    if isinstance(expected, list):
        return list(got or []) == list(expected)
    if expected is None:
        return got is None
    return got == expected


def print_benchmark_results(
    results: list[dict[str, Any]],
    aggregate: dict[str, list[int]],
    timing: dict[str, float],
    tracked_fields: list[str] | None = None,
) -> None:
    """Print the per-query diff list + per-field aggregate table.

    Shared golden-set benchmark helper so ``--benchmark`` output stays
    byte-for-byte comparable across runs.  ``aggregate`` maps field -> [matched, total].
    """
    if tracked_fields is None:
        tracked_fields = TRACKED_FIELDS
    print("\n=== PER-QUERY DIFFS ===")
    for i, res in enumerate(results, 1):
        diffs = res["diffs"]
        print(
            f"#{i:02d} {res['query'][:60]!r}  matched {res['matched']}/{res['fields']}  "
            f"({res['latency_ms']:.0f} ms, {res['input_tokens']} tok in)"
        )
        for field, got, expected in diffs:
            print(f"      {field}: got={got!r} expected={expected!r}")
    print("\n=== AGGREGATE PER-FIELD MATCH RATE ===")
    print(f"{'field':<24} {'matched':>7} {'total':>6} {'rate':>7}")
    for field in tracked_fields:
        matched, total = aggregate[field]
        rate = f"{matched}/{total}" if total else "-"
        print(f"{field:<24} {matched:>7} {total:>6} {rate:>7}")
    print(
        f"\ntotal: {timing['matched']}/{timing['fields']} fields "
        f"across {timing['queries']} queries; avg Jev latency "
        f"{timing['avg_latency_ms']:.0f} ms; total input tokens {timing['input_tokens']}; "
        f"total output tokens {timing['output_tokens']}"
    )
    print(f"total wall time: {timing['wall_sec']:.1f} s")
