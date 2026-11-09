"""Pure logic for the hybrid Jev processing-method categorizer (stage 1 prototype).

The production categorizer (``kissaten.ai.processing_method_categorizer``) sends
every messy processing-method string to a Gemini agent and asks it for a
canonical name.  The Jev hybrid keeps the same goal but splits the work by
determinism:

* **Deterministic code (this module)** — string normalization, existing-mapping
  lookup, candidate selection/ranking, answer composition, benchmark sampling
  and merge/conflict bookkeeping.  Pure functions, no network, no DB.
* **TypeSafe Jev Choice/Score (stage 2 adapter)** — the semantic judgements:
  "is this candidate EXACTLY the same process?" per method and the
  merge/conflict Score calls per name pair/group.
* **Small Gemini fallback (stage 2 harness)** — composes a brand-new canonical
  name when Jev answers ``none_of_the_above``.

This module deliberately depends on the **stdlib + ``rapidfuzz`` +
``kissaten.ai.jev.common``** only (no ``pydantic_ai``, no ``duckdb``), so the
stage-2 adapter can import it without pulling in network/DB machinery and the
whole module is unit-testable offline.

The shared helpers come from :mod:`kissaten.ai.jev.common`:
``strip_accents`` (accent-insensitive comparison), ``generate_query_ngrams``
(content-word n-grams), ``sanitize_regex_value`` (null-ish LLM output) and
``NONE_OPTION`` (the search prototype's sentinel name).  Alias scoring needs the
raw Jaro-Winkler / token-set scores, so it calls ``rapidfuzz`` directly rather
than the name-only ``fuzzy_matches`` helper.

Naming notes:
    * ``mapping_key`` mirrors the DB/production join (``LOWER(original_name)``).
    * ``canonical_key`` is the stricter identity key used for "same process
      name" comparisons (casefold + accents + ``&|,+/``-and-dash separators).
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler

from kissaten.ai.jev.common import generate_query_ngrams, sanitize_regex_value, strip_accents

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Sentinel emitted instead of a candidate when no existing canonical preserves
# the same process identity.  Distinct from ``common.NONE_OPTION`` ("none"):
# here "no candidate fits" drives the small Gemini composition fallback.
NONE_OF_THE_ABOVE = "none_of_the_above"

DEFAULT_CANDIDATE_LIMIT = 16

# Base-process family fallback: extra candidates appended AFTER the ranked
# ``limit`` matches for canonicals that share a base-process marker with the
# input but scored below the keep threshold or fell past the limit.  Exact /
# alias / n-gram matches keep their rank; the family names never displace them.
FAMILY_TOPUP = 4

# Typo-recall threshold for process names (informational; candidate ranking
# uses ``ALIAS_FUZZY_MIN`` for aliases and 0.9 token-set for canonical names).
PROCESS_FUZZY_MIN = 0.82

# Minimum alias similarity (Jaro-Winkler or token-set, whichever is higher) for
# a canonical to be offered as a candidate.
ALIAS_FUZZY_MIN = 0.78

# Picks below this Jev-reported confidence go into the review bucket.
REVIEW_CONFIDENCE = 0.6

DEFAULT_BATCH_SIZE = 15
DEFAULT_MERGE_BATCH = 30
DEFAULT_CONFLICT_BATCH = 15

CATEGORIZE_TRACKED_METRICS = [
    "deterministic",
    "candidate_recall",
    "jev_correct",
    "false_merge",
    "none_of_the_above",
    "composition_match",
    "overall_match",
]

_WHITESPACE_RE = re.compile(r"\s+")
_TRAILING_QUOTES = ("'", '"')
# ``&|,+/`` and dashes are separators in canonical identity keys.
_CANONICAL_PUNCT_RE = re.compile(r"[&|,+/]")
_CANONICAL_DASH_RE = re.compile(r"[-–—]")
# Dashes / underscores act as word separators for marker detection.
_MARKER_SEP_RE = re.compile(r"[-–—_]+")
_DECAF_EA_RE = re.compile(r"\bea\b")

# (marker regex fragment in marker-normalized text -> base-process tag).  Each
# marker is matched after a word boundary (so "aerobic" does not fire inside
# "anaerobic", "natural" not inside "supernatural") but without a trailing
# boundary (so "co ferment" matches "co fermented").  Markers are matched
# against lowercased, accent-stripped, dash-normalized text, so "Wet-Hulled"
# and "wet hulled" both match.
_BASE_PROCESS_MARKERS: tuple[tuple[str, str], ...] = (
    ("washed", "washed"),
    ("natural", "natural"),
    ("honey", "honey"),
    ("anaerobic", "anaerobic"),
    ("aerobic", "aerobic"),
    ("lactic", "lactic"),
    ("carbonic", "carbonic"),
    ("maceration", "maceration"),
    ("wet hulled", "wet hulled"),
    ("giling basah", "wet hulled"),
    ("semi washed", "semi washed"),
    ("pulped natural", "pulped natural"),
    ("yeast", "yeast"),
    ("co ferment", "co-ferment"),
    ("thermal shock", "thermal shock"),
    ("anoxic", "anoxic"),
    ("oxydator", "oxydator"),
)

# "decaf" is also implied by any named decaffeination method:
# Swiss Water, Ethyl Acetate ("EA"), sugarcane, CO2, caffeine.
_DECAF_SUBSTRINGS = ("decaf", "swiss water", "ethyl acetate", "sugarcane", "co2", "caffeine")

# Merge-pair signals: an alias link is the strongest evidence (the two names
# literally share a recorded alias), then initialism equality, then a
# token-boundary substring; fuzzy scores slot in where they land.
_ALIAS_LINK_SCORE = 0.99
_INITIALISM_SCORE = 0.95
_SUBSTRING_SCORE = 0.9
_TOKEN_SET_KEEP = 0.9


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def normalize_process_text(name: str) -> str:
    """Strip, collapse internal whitespace and drop trailing quotes.

    Mirrors ``ProcessingMethodMapping.clean_names`` (strip + remove trailing
    ``'``/``"``) with whitespace collapsing so ``"  Fully   Washed  "`` and
    ``"Fully Washed"`` are the same value.  Falsy input -> ``""``.
    """
    if not name:
        return ""
    value = str(name).strip()
    while value and value[-1] in _TRAILING_QUOTES:
        value = value[:-1]
    return _WHITESPACE_RE.sub(" ", value).strip()


def mapping_key(name: str) -> str:
    """Lookup key mirroring the DB's case-insensitive ``LOWER(original_name)`` join."""
    return normalize_process_text(name).lower()


def canonical_key(name: str) -> str:
    """Identity key for "same process name" comparisons.

    casefold + accent stripping, ``&|,+/`` and dashes replaced by spaces,
    whitespace collapsed.  ``"Wet-Hulled"`` and ``"wet hulled"`` compare equal;
    ``"EA Decaf"`` and ``"ea decaf"`` likewise.
    """
    value = normalize_process_text(name)
    if not value:
        return ""
    value = strip_accents(value.casefold())
    value = _CANONICAL_PUNCT_RE.sub(" ", value)
    value = _CANONICAL_DASH_RE.sub(" ", value)
    return _WHITESPACE_RE.sub(" ", value).strip()


# ---------------------------------------------------------------------------
# Mappings file / vocabulary
# ---------------------------------------------------------------------------


def load_mappings_file(path: str | Path) -> list[dict]:
    """Load a processing-method mappings JSON file (same shape as production)."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


@dataclass(frozen=True)
class ProcessVocabulary:
    """Canonical process names plus their recorded aliases and popularity.

    ``canonicals`` is ordered for candidate emission (most aliases first);
    ``aliases`` maps canonical -> recorded original names in file order;
    ``counts`` maps canonical -> number of mapping-file entries (used to pick
    the surviving target when merging common names).
    """

    canonicals: list[str]
    aliases: dict[str, list[str]]
    counts: dict[str, int]


def build_vocabulary(mappings: list[dict]) -> ProcessVocabulary:
    """Group mapping entries by ``common_name`` into a :class:`ProcessVocabulary`.

    Empty ``original_name``/``common_name`` entries are skipped.  Aliases keep
    file order and are deduped case-insensitively.  ``canonicals`` is sorted by
    alias count (desc) then casefold name.
    """
    aliases: dict[str, list[str]] = {}
    seen: dict[str, set[str]] = {}
    counts: dict[str, int] = {}
    for item in mappings:
        common = normalize_process_text(item.get("common_name") or "")
        original = normalize_process_text(item.get("original_name") or "")
        if not common or not original:
            continue
        counts[common] = counts.get(common, 0) + 1
        bucket = aliases.setdefault(common, [])
        dedupe = seen.setdefault(common, set())
        lowered = original.lower()
        if lowered not in dedupe:
            dedupe.add(lowered)
            bucket.append(original)
    canonicals = sorted(aliases, key=lambda canonical: (-len(aliases[canonical]), canonical.casefold()))
    return ProcessVocabulary(canonicals=canonicals, aliases=aliases, counts=counts)


def existing_mapping_lookup(mappings: list[dict]) -> dict[str, dict]:
    """Index mapping entries by :func:`mapping_key` (last writer wins).

    The returned dicts are copies so callers can never mutate the loaded file
    data.  Entries with an empty original or common name are skipped.
    """
    lookup: dict[str, dict] = {}
    for item in mappings:
        original = normalize_process_text(item.get("original_name") or "")
        common = normalize_process_text(item.get("common_name") or "")
        if not original or not common:
            continue
        confidence = item.get("confidence", 1.0)
        confidence = float(confidence) if confidence is not None else 1.0
        lookup[mapping_key(original)] = {
            "original_name": original,
            "common_name": common,
            "confidence": confidence,
        }
    return lookup


def deterministic_map(method: str, lookup: dict[str, dict], vocabulary: ProcessVocabulary) -> dict | None:
    """Resolve ``method`` without any LLM call.

    (a) case-insensitive existing-mapping hit -> a copy of the recorded entry;
    (b) identity match against a canonical name (``canonical_key`` equality) ->
        ``{"original_name": method, "common_name": canonical, "confidence": 1.0}``;
    (c) ``None`` (ambiguous -> candidate selection / Jev).
    """
    key = mapping_key(method)
    if not key:
        return None
    hit = lookup.get(key)
    if hit is not None:
        return dict(hit)
    identity = canonical_key(method)
    if identity:
        for canonical in vocabulary.canonicals:
            if canonical_key(canonical) == identity:
                return {"original_name": method, "common_name": canonical, "confidence": 1.0}
    return None


# ---------------------------------------------------------------------------
# Base-process detection / candidate selection
# ---------------------------------------------------------------------------


def _marker_text(name: str) -> str:
    """Lowercase, accent-strip and dash-normalize text for marker scanning."""
    text = strip_accents(str(name or "").lower())
    text = _MARKER_SEP_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def detect_base_processes(name: str) -> frozenset[str]:
    """Detect base-process / fermentation / decaf markers in a messy name.

    Returns a frozenset of tags such as ``{"natural", "anaerobic", "decaf"}``.
    Decaf is implied by any named decaffeination method (Swiss Water, Ethyl
    Acetate / "EA", sugarcane, CO2, caffeine); wet-hulled / giling basah map to
    the same ``"wet hulled"`` tag.
    """
    text = _marker_text(name)
    if not text:
        return frozenset()
    found = {tag for marker, tag in _BASE_PROCESS_MARKERS if re.search(rf"\b{re.escape(marker)}", text)}
    if any(marker in text for marker in _DECAF_SUBSTRINGS) or _DECAF_EA_RE.search(text):
        found.add("decaf")
    return frozenset(found)


def select_process_candidates(
    method: str, vocabulary: ProcessVocabulary, limit: int = DEFAULT_CANDIDATE_LIMIT
) -> list[str]:
    """Pick and rank the canonical candidates offered to the Jev Choice question.

    Each canonical is scored by:
      (a) the longest ``generate_query_ngrams(method)`` n-gram contained in its
          normalized name;
      (b) alias similarity = max over its first 10 aliases of
          ``max(JaroWinkler, token_set_ratio / 100)``;
      (c) base-process marker overlap.

    A canonical is kept when it has an n-gram hit, an alias similarity >=
    ``ALIAS_FUZZY_MIN``, or a token-set ratio >= 0.9 against its canonical
    name.  Kept candidates rank by ``(-exact_match, -base_overlap,
    -best_score, -longest_ngram, casefold name)`` and are capped at ``limit``.

    The ``exact_match`` component (a deliberate addition to the prototype spec)
    puts a canonical whose name or *recorded alias* equals the input at the
    top.  Token-set ratio saturates at 1.0 for subset matches ("Pulped Natural"
    scores 1.0 against both "Honey" and every "Natural" canonical), so without
    this tie-break the recorded canonical can be pushed out of the top-12 by
    its neighbours ("EA Decaf" -> "Ethyl Acetate Decaf" loses to a dozen
    "Sugarcane EA Decaf ..." canonicals).  Exact identity is the strongest
    candidate evidence and cannot leak held-out benchmark answers because
    ``prepare_benchmark`` strips them from alias lists first.

     Normalized names / alias lists / base-process sets are precomputed once per
    call; rapidfuzz scoring is C++-backed, so a full 795-canonical vocabulary
    stays well inside the prototype's per-method budget.

    Base-process family fallback: after the ranked ``limit`` matches, up to
    ``FAMILY_TOPUP`` extra candidates are appended for canonicals that share at
    least one base-process marker with the input but either fell past the limit
    or scored below the keep threshold.  The kept-but-cut names keep their
    existing rank order; below-threshold names rank by ``token_set_ratio``
    against the input; an initialism match ("EA Decaf" -> "Ethyl Acetate Decaf")
    is promoted to the front of the fallback.  Without this, a marker-sharing
    canonical whose wording scores poorly ("EA Decaf" vs "Ethyl Acetate Decaf")
    could never be offered even though the input clearly names its family.
    """
    if limit <= 0 or not method or not vocabulary.canonicals:
        return []
    method_norm = canonical_key(method)
    if not method_norm:
        return []
    ngrams = generate_query_ngrams(method)
    method_bases = detect_base_processes(method)

    prepared: list[tuple[str, str, frozenset[str], list[str], frozenset[str]]] = []
    for canonical in vocabulary.canonicals:
        alias_norms = [canonical_key(alias) for alias in vocabulary.aliases.get(canonical, ())]
        prepared.append(
            (
                canonical,
                canonical_key(canonical),
                detect_base_processes(canonical),
                alias_norms[:10],
                frozenset(alias_norms),
            )
        )

    kept: list[tuple[tuple[float, float, float, int, str], str, frozenset[str]]] = []
    below: list[tuple[float, str, frozenset[str]]] = []
    for canonical, canonical_norm, canonical_bases, alias_norms, all_alias_norms in prepared:
        exact = 1.0 if method_norm == canonical_norm or method_norm in all_alias_norms else 0.0
        longest = 0
        for ngram in ngrams:
            if len(ngram) > longest and ngram in canonical_norm:
                longest = len(ngram)
        alias_score = 0.0
        for alias_norm in alias_norms:
            if not alias_norm:
                continue
            similarity = JaroWinkler.normalized_similarity(method_norm, alias_norm)
            token_set = fuzz.token_set_ratio(method_norm, alias_norm) / 100.0
            alias_score = max(alias_score, similarity, token_set)
        canonical_token_set = 0.0
        if canonical_norm:
            canonical_token_set = fuzz.token_set_ratio(method_norm, canonical_norm) / 100.0
        if longest <= 0 and alias_score < ALIAS_FUZZY_MIN and canonical_token_set < _TOKEN_SET_KEEP:
            below.append((canonical_token_set, canonical, canonical_bases))
            continue
        overlap = float(len(method_bases & canonical_bases))
        best_score = max(alias_score, canonical_token_set)
        rank = (-exact, -overlap, -best_score, -longest, canonical.casefold())
        kept.append((rank, canonical, canonical_bases))

    kept.sort(key=lambda item: item[0])
    selected = [canonical for _rank, canonical, _bases in kept[:limit]]
    if not method_bases:
        return selected

    family_pool: list[str] = [
        canonical for _rank, canonical, canonical_bases in kept[limit:] if canonical_bases & method_bases
    ]
    below.sort(key=lambda item: (-item[0], item[1].casefold()))
    family_pool.extend(canonical for _score, canonical, canonical_bases in below if canonical_bases & method_bases)
    family_pool.sort(key=lambda canonical: not _initialism_match(method, canonical))
    return selected + family_pool[:FAMILY_TOPUP]


def candidate_descriptions(
    vocabulary: ProcessVocabulary, candidates: list[str], max_aliases: int = 3, alias_max_len: int = 42
) -> dict[str, str]:
    """Human-readable criteria for the Jev Choice options.

    Format: ``Canonical processing method "X". Previously used for: "a", "b",
    "c".``  Aliases longer than ``alias_max_len`` are clipped with an ellipsis;
    when a canonical has more than ``max_aliases`` aliases the tail is folded
    into ``(and N more)``; canonicals without aliases omit the clause.
    """
    descriptions: dict[str, str] = {}
    for canonical in candidates:
        aliases = vocabulary.aliases.get(canonical, [])
        shown = []
        for alias in aliases[: max(0, max_aliases)]:
            text = alias if len(alias) <= alias_max_len else alias[:alias_max_len].rstrip() + "..."
            shown.append(f'"{text}"')
        clause = ""
        if shown:
            clause = " Previously used for: " + ", ".join(shown)
            remaining = len(aliases) - len(shown)
            if remaining > 0:
                clause += f" (and {remaining} more)"
            clause += "."
        descriptions[canonical] = f'Canonical processing method "{canonical}".{clause}'
    return descriptions


# ---------------------------------------------------------------------------
# Jev question / answer composition
# ---------------------------------------------------------------------------


def build_categorize_question(method: str) -> str:
    """The per-method Jev Choice question text.

    A candidate may only be picked when it preserves process identity; a
    merely similar candidate must not be selected, and ``none_of_the_above``
    is the answer when nothing fits.  The non-mergeable distinctions and the
    merge-irrelevant differences are spelled out explicitly, plus the
    duration/adverb rule: when the candidates offer both a plainer canonical
    and a variant that only adds duration/time/adverb detail, the plainer one
    is the same process identity.
    """
    return (
        f'Which canonical processing method is "{method}"? '
        "Pick the candidate that is EXACTLY the same process — merely similar candidates must NOT be selected. "
        f'Pick "{NONE_OF_THE_ABOVE}" when no candidate preserves the same process identity — a candidate that '
        "only resembles the input (similar wording, an extra or missing qualifier) is NOT the same process. "
        "Duration/time/adverb detail in the input is not part of process identity: when the candidates offer "
        "both a plainer name and a variant that only adds that detail (e.g. '72h Fermentation', 'Extended "
        "Fermentation'), pick the plainer canonical unless the input's defining difference IS that fermentation "
        "specification. "
        "Never merge across these distinctions: base method (Natural vs Washed vs Honey); aerobic vs anaerobic "
        "fermentation; decaffeination method (Swiss Water vs EA/Ethyl Acetate); honey level (Black vs Red vs "
        "Yellow); added substrates (e.g. lychee vs mango). "
        "These differences do NOT make processes different: step order, time/duration info (48hrs, 72 hour), "
        "adverbs (carefully, slowly), punctuation (plus vs comma vs 'and' vs 'with'), and abbreviations "
        "(Coco = Coconut, Fully Washed = Washed)."
    )


CATEGORIZE_INSTRUCTIONS = (
    "You are an expert in coffee processing methods mapping messy method names to canonical names. "
    "Pick the candidate that refers to EXACTLY the same process; merely similar candidates must NOT be "
    f'selected. Answer "{NONE_OF_THE_ABOVE}" when no candidate preserves process identity — a candidate that '
    "only resembles the input is NOT the same process. "
    "Duration/time/adverb detail is not part of process identity: when both a plainer canonical and a variant "
    "that only adds that detail (e.g. '72h Fermentation', 'Extended Fermentation') are offered, prefer the "
    "plainer canonical unless the input's defining difference IS that fermentation specification. "
    "Never merge across these distinctions: base method (Natural vs Washed vs Honey); aerobic vs anaerobic "
    "fermentation; decaffeination method (Swiss Water vs EA/Ethyl Acetate); honey level (Black vs Red vs "
    "Yellow); added substrates (e.g. lychee vs mango). "
    "Step order, time/duration info, adverbs, punctuation and abbreviations (Coco = Coconut, Fully Washed = "
    "Washed) do NOT make processes different."
)


def build_categorize_state(methods: list[str]) -> str:
    """Render the batch state: ``Normalize these coffee processing methods:`` + numbered list."""
    lines = ["Normalize these coffee processing methods:"]
    lines.extend(f'{index}. "{method}"' for index, method in enumerate(methods, 1))
    return "\n".join(lines)


def compose_categorize_answers(
    methods: list[str],
    answers: dict[str, Any],
    meta: dict[str, Any],
    confidences: dict[str, float] | None = None,
) -> dict:
    """Interpret batch Jev answers into picks / review / composition work.

    Pure function.  ``meta["field_methods"]`` maps a Jev field id to the input
    method it asks about; ``meta["field_candidates"]`` maps the same field id to
    the candidate canonicals offered.  ``answers`` uses the adapter shapes::

        {"type": "choice", "choice": <canonical|none_of_the_above>, "confidence": float}

    Returns::

        {
          "picks": [{"original_name", "common_name", "confidence"}, ...],
          "review": [<pick dicts with confidence < REVIEW_CONFIDENCE>],
          "needs_composition": [<methods whose answer is missing or none_of_the_above, input order>],
        }

    ``confidences`` optionally overrides the confidence for a field (falling
    back to a method-keyed entry), which the harness uses when a Jev primitive
    does not carry its confidence through the output model.
    """
    field_methods = meta.get("field_methods") or {}
    fields_for_method: dict[str, list[str]] = {}
    for field, method in field_methods.items():
        fields_for_method.setdefault(method, []).append(field)

    picks: list[dict] = []
    needs_composition: list[str] = []
    for method in methods:
        field = next(iter(fields_for_method.get(method, ())), None)
        if field is None:
            needs_composition.append(method)
            continue
        answer = answers.get(field)
        choice = answer.get("choice") if isinstance(answer, dict) else None
        if not isinstance(choice, str) or not choice or choice == NONE_OF_THE_ABOVE:
            needs_composition.append(method)
            continue
        confidence: Any = None
        if confidences:
            confidence = confidences.get(field)
            if confidence is None:
                confidence = confidences.get(method)
        if confidence is None and isinstance(answer, dict):
            confidence = answer.get("confidence")
        try:
            confidence = float(confidence) if confidence is not None else 1.0
        except (TypeError, ValueError):
            confidence = 1.0
        picks.append({"original_name": method, "common_name": choice, "confidence": confidence})

    review = [pick for pick in picks if pick["confidence"] < REVIEW_CONFIDENCE]
    return {"picks": picks, "review": review, "needs_composition": needs_composition}


def canonical_sanitize(value: Any) -> str | None:
    """Clean a Gemini-composed canonical name; ``None`` when unusable.

    Uses :func:`~kissaten.ai.jev.common.sanitize_regex_value` (null-ish/sentinel
    output -> ``None``), then strips surrounding quotes, collapses whitespace,
    trims trailing periods.  Empty results and values longer than 120 chars are
    rejected.
    """
    text = sanitize_regex_value(value)
    if text is None:
        return None
    text = text.strip().strip("'\"")
    text = _WHITESPACE_RE.sub(" ", text).strip()
    text = text.rstrip(".").strip()
    if not text or len(text) > 120:
        return None
    return text


def mapping_matches(expected: str | None, got: str | None) -> bool:
    """True when two canonical names are the same process name (``canonical_key``)."""
    return canonical_key(expected or "") == canonical_key(got or "")


# ---------------------------------------------------------------------------
# Merge pairing / aggregation
# ---------------------------------------------------------------------------


def _tokens(name: str) -> list[str]:
    return canonical_key(name).split()


def _initialism_match(a: str, b: str) -> bool:
    """True when one name spells the other out (initials/abbreviation alignment).

    Tokens of the shorter name are aligned, in order, onto runs of tokens of the
    longer name: a token matches a run when it equals the run's token (e.g.
    ``"decaf"`` -> ``["decaf"]``) or the run's first letters concatenated (e.g.
    ``"ea"`` -> ``["ethyl", "acetate"]``).  So ``"EA Decaf"`` matches
    ``"Ethyl Acetate Decaf"``.
    """
    tokens_a = _tokens(a)
    tokens_b = _tokens(b)
    if not tokens_a or not tokens_b:
        return False

    def aligns(shorter: list[str], longer: list[str]) -> bool:
        if not shorter:
            return not longer
        head, rest = shorter[0], shorter[1:]
        for end in range(1, len(longer) + 1):
            run = longer[:end]
            initials = "".join(token[0] for token in run)
            if head == initials or (end == 1 and head == run[0]):
                if aligns(rest, longer[end:]):
                    return True
        return False

    return aligns(tokens_a, tokens_b) or aligns(tokens_b, tokens_a)


def _alias_keys(vocabulary: ProcessVocabulary, canonical: str) -> set[str]:
    keys = {canonical_key(canonical)}
    for alias in vocabulary.aliases.get(canonical, ()):
        key = canonical_key(alias)
        if key:
            keys.add(key)
    return keys


def generate_merge_pairs(
    vocabulary: ProcessVocabulary, max_pairs: int = 400, per_name: int = 5, threshold: float = 0.80
) -> list[tuple[str, str]]:
    """Generate candidate canonical-merge pairs for the Jev merge scorer.

    A pair is generated when ANY signal fires:
      * token-boundary substring (one normalized name contained in the other);
      * Jaro-Winkler >= ``threshold`` or token-set ratio >= 0.9;
      * ``_initialism_match`` (e.g. "EA Decaf" / "Ethyl Acetate Decaf");
      * alias link (one canonical name appears among the other's aliases, or
        they share an alias key — catches "Pulped Natural" -> "Honey").

    Pairs rank by signal strength (alias link > initialism > substring > fuzzy
    score) then names.  Each canonical is kept for at most ``per_name``
    strongest partners, and the result is capped at ``max_pairs`` overall.
    """
    canonicals = list(vocabulary.canonicals)
    if len(canonicals) < 2 or max_pairs <= 0 or per_name <= 0:
        return []
    norms = {canonical: canonical_key(canonical) for canonical in canonicals}
    alias_keys = {canonical: _alias_keys(vocabulary, canonical) for canonical in canonicals}

    scored: list[tuple[float, str, str]] = []
    for index, a in enumerate(canonicals):
        norm_a = norms[a]
        for b in canonicals[index + 1 :]:
            norm_b = norms[b]
            jaro = JaroWinkler.normalized_similarity(norm_a, norm_b)
            token_set = fuzz.token_set_ratio(norm_a, norm_b) / 100.0
            substring = f" {norm_a} " in f" {norm_b} " or f" {norm_b} " in f" {norm_a} "
            alias_link = bool(alias_keys[a] & alias_keys[b])
            initialism = _initialism_match(a, b)
            fuzzy = jaro >= threshold or token_set >= _TOKEN_SET_KEEP
            if not (fuzzy or substring or alias_link or initialism):
                continue
            score = max(jaro, token_set)
            if substring:
                score = max(score, _SUBSTRING_SCORE)
            if initialism:
                score = max(score, _INITIALISM_SCORE)
            if alias_link:
                score = max(score, _ALIAS_LINK_SCORE)
            low, high = (a, b) if a.casefold() <= b.casefold() else (b, a)
            scored.append((score, low, high))

    scored.sort(key=lambda item: (-item[0], item[1].casefold(), item[2].casefold()))
    kept: list[tuple[str, str]] = []
    degree: dict[str, int] = {}
    for _score, a, b in scored:
        if degree.get(a, 0) >= per_name or degree.get(b, 0) >= per_name:
            continue
        kept.append((a, b))
        degree[a] = degree.get(a, 0) + 1
        degree[b] = degree.get(b, 0) + 1
        if len(kept) >= max_pairs:
            break
    return kept


def _merge_target(members: list[str], vocabulary: ProcessVocabulary | None) -> str:
    """Pick the surviving canonical: highest ``counts`` then casefold name.

    Without a vocabulary (or for names missing from it) the casefold-first
    name wins.
    """

    def sort_key(name: str) -> tuple[int, str]:
        count = vocabulary.counts.get(name, 0) if vocabulary is not None else 0
        return (-count, name.casefold())

    return min(members, key=sort_key)


def aggregate_merge_scores(
    pairs: list[tuple[str, str]], scores: Any, vocabulary: ProcessVocabulary | None = None
) -> dict:
    """Aggregate per-pair Jev scores into merges, components and review work.

    ``scores`` is either a dict keyed by the pair tuple (both orders accepted)
    or a sequence parallel to ``pairs``.  Score semantics: 2 = SAME, 1 = REVIEW,
    0 = DIFFERENT; ``None``/missing counts as REVIEW.  SAME edges are unioned;
    when a REVIEW edge connects two members of an already-unioned component the
    whole component is flagged for review and NOT auto-merged.

    Returns ``{"merges": {source: target}, "components": [[...], ...],
    "review_pairs": [(a, b, score_or_None), ...],
    "review_components": [[...], ...]}``.  Merge targets are the most popular
    canonical (``counts``) with a casefold-name tie-break.  Only connected
    components (size >= 2) are reported.
    """
    pair_list = [tuple(pair) for pair in pairs]
    if isinstance(scores, dict):
        scored = []
        for a, b in pair_list:
            value = scores.get((a, b), scores.get((b, a)))
            if value is None:
                value = scores.get(frozenset((a, b)))
            scored.append((a, b, value))
    else:
        score_list = list(scores)
        scored = [(a, b, score_list[i] if i < len(score_list) else None) for i, (a, b) in enumerate(pair_list)]

    def classify(value: Any) -> int:
        if value is None:
            return 1
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 1
        if numeric >= 1.5:
            return 2
        if numeric >= 0.5:
            return 1
        return 0

    classes = [classify(value) for _a, _b, value in scored]

    parent: dict[str, str] = {}

    def find(node: str) -> str:
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a: str, b: str) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    nodes: list[str] = []
    seen_nodes: set[str] = set()
    for a, b, _value in scored:
        for node in (a, b):
            if node not in seen_nodes:
                seen_nodes.add(node)
                nodes.append(node)
                parent[node] = node

    for (a, b, _value), klass in zip(scored, classes):
        if klass == 2:
            union(a, b)

    review_roots: set[str] = set()
    for (a, b, _value), klass in zip(scored, classes):
        if klass == 1 and find(a) == find(b):
            review_roots.add(find(a))

    component_map: dict[str, list[str]] = {}
    for node in nodes:
        component_map.setdefault(find(node), []).append(node)

    component_list: list[tuple[str, list[str]]] = []
    for root, members in component_map.items():
        if len(members) > 1:
            component_list.append((root, sorted(members, key=str.casefold)))
    component_list.sort(key=lambda item: item[1][0].casefold())

    merges: dict[str, str] = {}
    for root, members in component_list:
        if root in review_roots:
            continue
        target = _merge_target(members, vocabulary)
        for member in members:
            if member != target:
                merges[member] = target

    return {
        "merges": merges,
        "components": [members for _root, members in component_list],
        "review_pairs": [(a, b, value) for (a, b, value), klass in zip(scored, classes) if klass == 1],
        "review_components": [members for root, members in component_list if root in review_roots],
    }


# ---------------------------------------------------------------------------
# Golden sets (copied from the production prompts, docs/KIT_REVIEW-adjacent)
# ---------------------------------------------------------------------------

# "same" = must merge; "review" = uncertain, Jev should score 1; "different" =
# must stay separate.  Mirrors the production categorizer/merge/conflict prompts.
MERGE_GOLDEN_SET: list[dict[str, Any]] = [
    {"a": "Natural", "b": "Natural Process", "expected": "same"},
    {"a": "EA Decaf", "b": "Ethyl Acetate Decaffeinated", "expected": "same"},
    {"a": "Pulped Natural", "b": "Honey Process", "expected": "same"},
    {"a": "Fully Washed", "b": "Washed", "expected": "same"},
    {"a": "Natural + Coconut", "b": "Coco Natural", "expected": "same"},
    {
        "a": "Washed, Yeast Inoculation + Thermal Shock",
        "b": "Yeast Inoculated, Thermal Shock, Washed",
        "expected": "same",
    },
    {"a": "Oxydator Natural (48hrs)", "b": "Oxydator Natural", "expected": "same"},
    {"a": "Natural Anaerobic", "b": "Natural", "expected": "different"},
    {"a": "Yellow Honey", "b": "Red Honey", "expected": "different"},
    {"a": "Swiss Water Decaf", "b": "EA Decaf", "expected": "different"},
    {"a": "Natural", "b": "Anaerobic Natural", "expected": "different"},
    {"a": "Washed", "b": "Honey", "expected": "different"},
    {"a": "Natural, Lychee", "b": "Natural, Mango", "expected": "different"},
    {"a": "Carbonic Maceration Natural", "b": "Natural", "expected": "different"},
    {"a": "Black Honey", "b": "Honey", "expected": "review"},
    {"a": "Anaerobic Natural", "b": "Anaerobic Natural, Extended Fermentation", "expected": "review"},
]

# Synthetic conflict groups: expected 0 = KEEP (confirmed merge), 1 = REVIEW
# (uncertain), 2 = SPLIT (fundamentally different processes).
CONFLICT_GOLDEN_SET: list[dict[str, Any]] = [
    {"common_name": "Natural", "originals": ["Natural", "Natural Process"], "expected": 0},
    {"common_name": "Anaerobic Natural", "originals": ["Natural", "Anaerobic Natural"], "expected": 2},
    {"common_name": "Washed", "originals": ["Washed", "Fully Washed"], "expected": 0},
    {"common_name": "Honey", "originals": ["Honey", "Black Honey"], "expected": 1},
    {"common_name": "Decaf", "originals": ["Swiss Water Decaf", "EA Decaf"], "expected": 2},
    {"common_name": "Co-Fermented Natural", "originals": ["Natural, Lychee", "Natural, Mango"], "expected": 2},
    {
        "common_name": "Yeast Fermentation",
        "originals": ["Anaerobic Natural", "Anaerobic Natural, Extended Fermentation"],
        "expected": 1,
    },
]


def compose_conflict_decisions(
    groups: dict[str, list[str]], answers: dict[str, Any], protected_common_names: set[str] | None = None
) -> dict:
    """Turn per-group Jev scores into resolved / kept buckets with notes.

    Pure function.  ``groups`` maps a common name to the original names merged
    under it; ``answers`` maps each common name to a Jev Score answer
    (``{"type": "score", "score": 2}`` or a bare number).  One score per group:
    0 = KEEP (merge confirmed), 1 = REVIEW (uncertain), 2 = SPLIT.  Score >= 1
    resolves the group (goes to ``resolved``, mirroring production's manual
    review set) unless the lowercased common name is in
    ``protected_common_names`` — a reviewed name is never demoted, it stays in
    ``kept`` with an explanatory note.  Missing scores and scores < 1 stay in
    ``kept``.

    Returns ``{"resolved": {common: originals}, "kept": {common: originals},
    "notes": {common: reason}}`` with deterministic note strings.
    """
    protected = {name.lower() for name in (protected_common_names or ())}
    resolved: dict[str, list[str]] = {}
    kept: dict[str, list[str]] = {}
    notes: dict[str, str] = {}

    for common_name, originals in groups.items():
        answer = answers.get(common_name)
        raw_score = answer.get("score") if isinstance(answer, dict) else answer
        score: float | None
        try:
            score = float(raw_score) if raw_score is not None else None
        except (TypeError, ValueError):
            score = None

        if score is None:
            kept[common_name] = list(originals)
            notes[common_name] = "missing decision score; kept as-is"
            continue
        if score < 0.5:
            kept[common_name] = list(originals)
            notes[common_name] = "confirmed: same process"
            continue
        if common_name.lower() in protected:
            kept[common_name] = list(originals)
            notes[common_name] = "reviewed name never demoted; kept as-is"
            continue
        resolved[common_name] = list(originals)
        if score >= 1.5:
            notes[common_name] = "split: fundamentally different processes"
        else:
            notes[common_name] = "review: uncertain merge flagged for manual review"

    return {"resolved": resolved, "kept": kept, "notes": notes}


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------


def build_categorize_benchmark(mappings: list[dict], limit: int = 100, seed: int = 42) -> list[dict]:
    """Deterministically sample non-empty mapping entries for benchmarking.

    Returns ``[{"original_name", "common_name"}, ...]`` sampled with
    ``random.Random(seed)`` so a run is reproducible.
    """
    entries = [
        item
        for item in mappings
        if normalize_process_text(item.get("original_name") or "")
        and normalize_process_text(item.get("common_name") or "")
    ]
    sample_size = min(limit, len(entries))
    if sample_size <= 0:
        return []
    chosen = random.Random(seed).sample(entries, k=sample_size)
    return [
        {
            "original_name": normalize_process_text(item["original_name"]),
            "common_name": normalize_process_text(item["common_name"]),
        }
        for item in chosen
    ]


def prepare_benchmark(
    mappings: list[dict], sample: list[dict], cold: bool = False
) -> tuple[ProcessVocabulary, dict[str, dict]]:
    """Build a leakage-free vocabulary + lookup for a benchmark sample.

    The sample's held-out ``original_name`` entries are removed before the
    vocabulary/lookup are built, so no alias list or lookup key leaks the
    expected answer.  With ``cold=True`` the expected ``common_name`` values are
    also removed from ``vocabulary.canonicals`` (a cold-start run cannot even
    choose the recorded canonical as a candidate).
    """
    held_out = {
        mapping_key(item.get("original_name") or "") for item in sample if mapping_key(item.get("original_name") or "")
    }
    expected = {
        normalize_process_text(item.get("common_name") or "")
        for item in sample
        if normalize_process_text(item.get("common_name") or "")
    }
    filtered = [item for item in mappings if mapping_key(item.get("original_name") or "") not in held_out]
    vocabulary = build_vocabulary(filtered)
    lookup = existing_mapping_lookup(filtered)
    if cold:
        remaining = [canonical for canonical in vocabulary.canonicals if canonical not in expected]
        vocabulary = replace(vocabulary, canonicals=remaining)
    return vocabulary, lookup
