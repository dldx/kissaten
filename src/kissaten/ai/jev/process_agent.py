"""TypeSafe Jev hybrid processing-method categorizer adapter (stage 2 prototype).

Stage 1 (``kissaten.ai.jev.process_common``) owns the deterministic half of the
hybrid: normalization, existing-mapping lookup, candidate selection/ranking,
answer composition, merge-pair generation/aggregation and conflict bookkeeping.
This module owns the semantic half — it turns those pure helpers into actual Jev
(TypeSafe) and Gemini calls:

* **Jev Choice questions** (:func:`run_categorize`) — one ``Choices`` field per
  input method, offering the selected canonical candidates plus
  ``none_of_the_above``.  Jev decides whether a candidate is EXACTLY the same
  process; anything it declines goes to composition.
* **Jev Score questions** (:func:`run_merge_review`, :func:`run_conflicts`) —
  one 0..2 rubric field per canonical-name pair (merge) or per common-name group
  (conflict), so ``aggregate_merge_scores`` /
  ``compose_conflict_decisions`` consume the answers exactly as in stage 1.
* **Small Gemini fallback** (:func:`run_canonical_name_llm`) — composes a brand
  new canonical name when Jev answers ``none_of_the_above`` (or no candidate was
  offered at all), mirroring ``agent.run_regex_fields`` with
  ``gemini-3.5-flash``, the model the production categorizer pins.

The output models are built per batch with ``pydantic.create_model`` (the
TypeSafe adapter maps ``Choices`` -> Choice, ``IntEnum + UseEnumMemberDocstrings``
-> Score), and the Agent is constructed INSIDE the async functions because
pydantic-ai 2.x clients are bound to one event loop.

Contract notes:
    * ``run_categorize``'s ``use_llm`` flag gates ONLY the Gemini composition
      fallback.  Jev is a System One decision model, not a generative LLM, and
      it stays in the loop when ``use_llm=False`` (the benchmark's ``--no-llm``
      disables the paid Gemini fallback, not the categorizer).
    * ``mappings`` entries always carry the *input* method as ``original_name``
      (normalized), even when a deterministic lookup hit was recorded under a
      differently-cased alias, so the result list lines up with the input list.
    * ``usage_totals`` includes the Jev batches AND the Gemini composition calls;
      per-batch usage is in ``batches``.
"""

from __future__ import annotations

import os
import sys
import time
from enum import IntEnum
from typing import Any

from pydantic import BaseModel, Field, create_model
from pydantic_ai import Agent, Choices, UseEnumMemberDocstrings
from pydantic_ai.models.typesafe import TypeSafeModelSettings

from kissaten.ai.jev.agent import (
    MODEL_PIN_ALT,
    MODEL_PIN_DEFAULT,
    _logfire_error,
    _logfire_info,
    _optional_span,
    set_logfire_enabled,
)
from kissaten.ai.jev.process_common import (
    CATEGORIZE_INSTRUCTIONS,
    DEFAULT_BATCH_SIZE,
    DEFAULT_CANDIDATE_LIMIT,
    DEFAULT_CONFLICT_BATCH,
    DEFAULT_MERGE_BATCH,
    NONE_OF_THE_ABOVE,
    ProcessVocabulary,
    aggregate_merge_scores,
    build_categorize_question,
    build_categorize_state,
    candidate_descriptions,
    canonical_sanitize,
    compose_categorize_answers,
    compose_conflict_decisions,
    deterministic_map,
    generate_merge_pairs,
    normalize_process_text,
    select_process_candidates,
)

__all__ = (
    "CANONICAL_NAME_INSTRUCTIONS",
    "LLM_MODEL_DEFAULT",
    "MODEL_PIN_ALT",
    "MODEL_PIN_DEFAULT",
    "ConflictDecision",
    "MergeDecision",
    "build_categorize_model",
    "build_conflict_model",
    "build_merge_model",
    "extract_choice_answers",
    "run_canonical_name_llm",
    "run_categorize",
    "run_conflicts",
    "run_merge_review",
    "set_logfire_enabled",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Mirrors the production categorizer's ``Agent("google:gemini-3.5-flash", ...)``
# (the pydantic-ai Google model name is the part after the provider prefix).
LLM_MODEL_DEFAULT = "gemini-3.5-flash"

# Port of the production ``ProcessCategorizer._create_agent`` rules.  The
# composition LLM only ever sees a method Jev could not map (or offered no
# candidates for), so the prompt is a standalone "standardize this one name"
# instruction set.
CANONICAL_NAME_INSTRUCTIONS = """\
You are an expert in coffee processing methods with deep knowledge of coffee production.
Your task is to map a coffee processing method name to a standardized common name.

CRITICAL RULES:
1. ONLY standardize onto a name that refers to the EXACT SAME process.
2. DO NOT merge different processes even if they're similar.
3. These categories should NEVER be merged:
   - Natural/Dry vs Washed/Wet vs Honey/Pulped Natural vs Semi-washed
   - Different fermentation methods (aerobic vs anaerobic)
   - Different drying methods (sun-dried vs mechanical)
   - Different decaffeination methods (EA vs Swiss Water vs CO2)
   - Different honey levels (Black vs Red vs Yellow)
   - Different added substrates (e.g. lychee vs mango)

When standardizing the name:
- Use the most descriptive common term.
- Fix capitalization and typos.
- Remove time/duration details and redundant words, but keep important qualifiers.

Things that should NOT prevent using an existing name (do not compose a new one for these):
- Different ordering of the same steps in the name
- Adverbs like "carefully", "slowly", "gently"
- Time/duration info (e.g. "48hrs", "72 hour")
- Punctuation differences (+, comma, "and", "with")
- Abbreviations (e.g. "Coco" = "Coconut")
- "Fully Washed" = "Washed" (same process)

A compound process is written as a comma-separated list, e.g. "Washed, Sugarcane EA Decaf".
If the input is equipment, a product, or not a processing method at all, return "Unknown".
"""

_CATEGORIZE_MODEL_DOC = (
    "Categorize messy coffee processing-method names onto canonical processing methods: pick the candidate that "
    "is EXACTLY the same process, or none_of_the_above when a new canonical name must be composed."
)
_MERGE_MODEL_DOC = (
    "Decide, for each named pair of canonical coffee processing-method names, whether the two describe the same "
    "process."
)
_CONFLICT_MODEL_DOC = (
    "Decide, for each common processing-method name, whether every original name grouped under it describes the "
    "same process."
)

_MERGE_INSTRUCTIONS = (
    "You compare pairs of canonical coffee processing-method names. Judge whether each pair describes the SAME "
    "process. Names that differ only in step order, adverbs, duration, punctuation or abbreviations are the "
    "same; names that differ in base method, fermentation type, honey level, drying method, added substrate or "
    "decaffeination method are different. Answer review when the pair only partially overlaps or you are unsure."
)
_CONFLICT_INSTRUCTIONS = (
    "You audit groups of original coffee processing-method names that share one common name. Keep a group when "
    "every original under it is the same process; split it when at least one original is a fundamentally "
    "different process; answer review when the evidence is mixed or uncertain."
)


# ---------------------------------------------------------------------------
# Rubric enums (UseEnumMemberDocstrings + IntEnum -> Jev Score 0..2)
# ---------------------------------------------------------------------------


class MergeDecision(UseEnumMemberDocstrings, IntEnum):
    """Are the two processing-method names the same process?"""

    DIFFERENT = 0
    """Two clearly different processing methods; keep the names separate."""
    REVIEW = 1
    """Uncertain or partially overlapping; a human should decide — do not auto-merge."""
    SAME = 2
    """The same processing method under different wording; safe to merge."""


class ConflictDecision(UseEnumMemberDocstrings, IntEnum):
    """Do all originals grouped under one common name describe the same process?"""

    KEEP = 0
    """Every original under this common name is the same process — keep the group merged."""
    REVIEW = 1
    """Uncertain, mixed, or qualifier-only differences whose significance is uncertain — honey level such as
    Black vs plain Honey, extended fermentation, or duration-only variants. A human should review the group;
    do not auto-merge."""
    SPLIT = 2
    """At least one original is a fundamentally different process — different base method, different
    fermentation type (aerobic vs anaerobic), different decaffeination method, or different added substrates
    (lychee vs mango). The group should be split."""


# ---------------------------------------------------------------------------
# Shared helpers (keep the module import-light: no pydantic-ai model imports,
# no event-loop-bound state at module level)
# ---------------------------------------------------------------------------


def _build_agent(model: type, instructions: str, model_pin: str, http_client: Any | None = None) -> Agent[Any, Any]:
    """Build the per-batch TypeSafe agent (must run inside the caller's loop).

    ``http_client`` is only used by the future web inspector (a capturing
    ``httpx2.AsyncClient``); ``TypeSafeModel``/``TypeSafeProvider`` are imported
    lazily so the CLI/benchmark import set stays unchanged, mirroring
    ``agent.run_native``.
    """
    settings = TypeSafeModelSettings(decision_boolean_threshold=0.5)
    if http_client is None:
        return Agent(f"typesafe:{model_pin}", output_type=model, instructions=instructions, model_settings=settings)
    from pydantic_ai.models.typesafe import TypeSafeModel
    from pydantic_ai.providers.typesafe import TypeSafeProvider

    return Agent(
        TypeSafeModel(model_pin, provider=TypeSafeProvider(http_client=http_client)),
        output_type=model,
        instructions=instructions,
        model_settings=settings,
    )


def _usage_dict(usage: Any) -> dict[str, int]:
    """Normalise ``result.usage`` (pydantic-ai 2.x property) into a plain dict."""
    if usage is None:
        return {"requests": 0, "input_tokens": 0, "output_tokens": 0}
    return {
        "requests": int(getattr(usage, "requests", 0) or 0),
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
    }


def _new_usage_totals() -> dict[str, int]:
    return {"input_tokens": 0, "output_tokens": 0, "requests": 0}


def _add_usage(totals: dict[str, int], usage: Any) -> None:
    """Add a usage object or a usage dict produced by :func:`_usage_dict` into ``totals``."""
    if usage is None:
        return
    if isinstance(usage, dict):
        values = usage
    else:
        values = _usage_dict(usage)
    for key in ("input_tokens", "output_tokens", "requests"):
        try:
            totals[key] = totals.get(key, 0) + int(values.get(key) or 0)
        except (TypeError, ValueError):
            continue


def _fallback_mapping(method: str) -> dict[str, Any]:
    """The deterministic identity fallback: keep the (normalized) name, confidence 0.5."""
    return {
        "original_name": method,
        "common_name": normalize_process_text(method),
        "confidence": 0.5,
    }


def _merge_state(pairs: list[tuple[str, str]]) -> str:
    """Render the batch state for the merge Score questions."""
    lines = ["Decide whether each pair of coffee processing-method names is the same process:"]
    lines.extend(f'{index}. "{a}" and "{b}"' for index, (a, b) in enumerate(pairs, 1))
    return "\n".join(lines)


def _conflict_state(groups: list[tuple[str, list[str]]]) -> str:
    """Render the batch state for the conflict Score questions."""
    lines = ["Decide whether every original name in each group describes the same processing method:"]
    for index, (common_name, originals) in enumerate(groups, 1):
        shown = ", ".join(f'"{name}"' for name in originals)
        lines.append(f'{index}. Common name: "{common_name}"; originals: {shown}')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Categorize: Choice questions + Gemini composition fallback
# ---------------------------------------------------------------------------


def build_categorize_model(
    batch: list[str], vocabulary: ProcessVocabulary, candidate_limit: int = DEFAULT_CANDIDATE_LIMIT
) -> tuple[type[BaseModel], dict[str, Any]]:
    """Build (output_model, meta) for one batch of processing-method names.

    Each method that has at least one ranked candidate gets a ``map_<i>`` field
    (``i`` is the batch index) holding a ``Choices`` over the candidate
    descriptions plus ``NONE_OF_THE_ABOVE``; methods with no candidates are
    omitted (Jev cannot pick and the composition phase handles them).  ``meta``
    maps each field back to its method and candidate list, which
    ``extract_choice_answers`` / ``compose_categorize_answers`` consume.
    """
    fields: dict[str, Any] = {}
    field_methods: dict[str, str] = {}
    field_candidates: dict[str, list[str]] = {}

    for index, method in enumerate(batch):
        candidates = select_process_candidates(method, vocabulary, candidate_limit)
        if not candidates:
            continue
        field = f"map_{index}"
        criteria = candidate_descriptions(vocabulary, candidates)
        criteria[NONE_OF_THE_ABOVE] = "No candidate is the same process — a new canonical name must be composed."
        question = build_categorize_question(method)
        fields[field] = (Choices(criteria, name=field, description=question), Field(description=question))
        field_methods[field] = method
        field_candidates[field] = candidates

    model = create_model("JevProcessCategorize", __doc__=_CATEGORIZE_MODEL_DOC, **fields)
    return model, {"field_methods": field_methods, "field_candidates": field_candidates}


def extract_choice_answers(
    output: Any, meta: dict[str, Any], provider_details: dict[str, Any] | None = None
) -> tuple[dict[str, Any], dict[str, float]]:
    """Convert a Jev Choice output into the stage-1 ``answers`` shape.

    For every ``meta["field_methods"]`` field present on ``output``: a
    ``{"type": "choice", "choice": <value>, "confidence": float}`` answer, with
    the confidence read from ``provider_details["confidence"][field]`` (1.0 when
    the provider omitted it).  Returns ``(answers, confidences)``; the
    confidences dict is also passed to ``compose_categorize_answers`` so it can
    bucket low-confidence picks into review.
    """
    provider_confidences = (provider_details or {}).get("confidence") or {}
    answers: dict[str, Any] = {}
    confidences: dict[str, float] = {}

    for field in meta.get("field_methods") or {}:
        if not hasattr(output, field):
            continue
        try:
            confidence = float(provider_confidences.get(field, 1.0))
        except (TypeError, ValueError):
            confidence = 1.0
        confidences[field] = confidence
        answers[field] = {"type": "choice", "choice": getattr(output, field), "confidence": confidence}

    return answers, confidences


async def run_categorize(
    methods: list[str],
    vocabulary: ProcessVocabulary,
    lookup: dict[str, dict] | None = None,
    model_pin: str = MODEL_PIN_DEFAULT,
    batch_size: int = DEFAULT_BATCH_SIZE,
    candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
    use_llm: bool = True,
    llm_model: str = LLM_MODEL_DEFAULT,
    http_client: Any | None = None,
) -> dict[str, Any]:
    """Categorize ``methods`` with the deterministic tier + Jev + Gemini fallback.

    Tier 1 resolves methods through ``deterministic_map`` (existing mapping or
    canonical-name identity).  The rest go to Jev in batches: each method with
    candidates becomes a Choice question, and every pick is interpreted by
    ``compose_categorize_answers``.  Methods Jev declines (or has no candidates
    for) are composed by :func:`run_canonical_name_llm` when ``use_llm`` —
    failure, a missing key or ``use_llm=False`` falls back to the deterministic
    identity at confidence 0.5.  A batch that raises falls back to identity for
    that whole batch (recorded in ``batches[i]["error"]``).

    ``use_llm`` gates ONLY the Gemini composition fallback; Jev always runs.

    Returns a dict with:
        * ``mappings``: ``[{"original_name", "common_name", "confidence"}, ...]``
          in input order;
        * ``sources``: method -> ``"deterministic" | "pick" | "composed" | "fallback"``;
        * ``candidates``: method -> offered canonicals (model-routed methods only);
        * ``picks`` / ``review``: Jev pick entries / low-confidence picks;
        * ``needs_composition``: methods that went to the composition phase;
        * ``batches``: per-Jev-batch ``{batch_index, size, latency_ms, model_name,
          usage, error}``;
        * ``usage_totals``: ``{input_tokens, output_tokens, requests}`` (Jev +
          composition calls);
        * ``latency_ms`` / ``model_name`` (last resolved Jev model; the
          composition model when no Jev batch ran).
    """
    started = time.monotonic()
    normalized = [normalize_process_text(method) for method in methods]
    lookup = lookup or {}

    by_method: dict[str, dict[str, Any]] = {}
    sources: dict[str, str] = {}
    method_candidates: dict[str, list[str]] = {}
    remaining: list[str] = []
    seen_remaining: set[str] = set()

    for method in normalized:
        if not method:
            # An empty name has nothing semantic to judge; keep the identity
            # fallback without spending a Jev/Gemini call on it.
            by_method.setdefault(method, _fallback_mapping(method))
            sources.setdefault(method, "fallback")
            continue
        hit = deterministic_map(method, lookup, vocabulary)
        if hit is not None:
            by_method.setdefault(
                method,
                {"original_name": method, "common_name": hit["common_name"], "confidence": hit["confidence"]},
            )
            sources.setdefault(method, "deterministic")
            continue
        if method not in seen_remaining:
            seen_remaining.add(method)
            remaining.append(method)

    batches: list[dict[str, Any]] = []
    usage_totals = _new_usage_totals()
    last_model_name: str | None = None
    picks: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    needs_composition: list[str] = []
    batching_step = max(1, batch_size)

    for batch_index, start in enumerate(range(0, len(remaining), batching_step)):
        batch = remaining[start : start + batching_step]
        model, meta = build_categorize_model(batch, vocabulary, candidate_limit)
        field_methods = meta["field_methods"]
        for field, method in field_methods.items():
            method_candidates[method] = list(meta["field_candidates"][field])

        record: dict[str, Any] = {
            "batch_index": batch_index,
            "size": len(batch),
            "latency_ms": 0.0,
            "model_name": None,
            "usage": {},
            "error": None,
        }
        batches.append(record)

        if not field_methods:
            # No method in this batch had a candidate: nothing to ask Jev, all
            # of them go straight to the composition phase.
            for method in batch:
                if method not in needs_composition:
                    needs_composition.append(method)
            continue

        batch_start = time.monotonic()
        span: Any = None
        try:
            with _optional_span(
                "jev.process.categorize",
                batch_index=batch_index,
                size=len(batch),
                model=model_pin,
                fields=len(field_methods),
            ) as span:
                agent = _build_agent(model, CATEGORIZE_INSTRUCTIONS, model_pin, http_client)
                result = await agent.run(build_categorize_state(batch))
                record["latency_ms"] = (time.monotonic() - batch_start) * 1000
                record["model_name"] = result.response.model_name
                record["usage"] = _usage_dict(result.usage)
                _add_usage(usage_totals, result.usage)
                last_model_name = result.response.model_name
                if span is not None:
                    span.set_attribute("model_name", result.response.model_name)
                    span.set_attribute("input_tokens", record["usage"]["input_tokens"])
                    span.set_attribute("output_tokens", record["usage"]["output_tokens"])
                    span.set_attribute("success", True)

            answers, confidences = extract_choice_answers(
                result.output, meta, dict(result.response.provider_details or {})
            )
            interpreted = compose_categorize_answers(batch, answers, meta, confidences)
            picks.extend(interpreted["picks"])
            review.extend(interpreted["review"])
            for pick in interpreted["picks"]:
                by_method.setdefault(pick["original_name"], pick)
                sources.setdefault(pick["original_name"], "pick")
            for method in interpreted["needs_composition"]:
                if method not in needs_composition:
                    needs_composition.append(method)
            _logfire_info(
                "jev.process.categorize.batch",
                batch_index=batch_index,
                size=len(batch),
                picks=len(interpreted["picks"]),
                composition=len(interpreted["needs_composition"]),
            )
        except Exception as exc:  # noqa: BLE001 - a failed batch must not kill the run
            record["latency_ms"] = (time.monotonic() - batch_start) * 1000
            record["error"] = f"{type(exc).__name__}: {exc}"
            if span is not None:
                span.set_attribute("success", False)
            _logfire_error(
                "jev.process.categorize failed",
                batch_index=batch_index,
                size=len(batch),
                error=str(exc),
                error_type=type(exc).__name__,
            )
            print(
                f"warning: Jev categorize batch {batch_index} failed ({type(exc).__name__}: {exc}); "
                "falling back to identity for that batch",
                file=sys.stderr,
            )
            for method in batch:
                by_method.setdefault(method, _fallback_mapping(method))
                sources.setdefault(method, "fallback")
                if method in needs_composition:
                    needs_composition.remove(method)

    # Composition phase: Gemini composes a brand-new canonical for every method
    # Jev declined / could not be asked about.  ``use_llm=False``, a missing key
    # or any failure falls back to the deterministic identity at 0.5.
    for method in needs_composition:
        if method in by_method:
            continue
        composed: dict[str, Any] | None = None
        if use_llm:
            try:
                composed = await run_canonical_name_llm(
                    method, method_candidates.get(method, []), llm_model, http_client
                )
            except Exception as exc:  # noqa: BLE001
                _logfire_error(
                    "jev.process.canonical failed",
                    method=method,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                print(
                    f"warning: canonical-name LLM failed for {method!r} ({type(exc).__name__}: {exc}); "
                    "using identity fallback",
                    file=sys.stderr,
                )
                composed = None
        if composed and composed.get("common_name"):
            by_method[method] = {
                "original_name": method,
                "common_name": composed["common_name"],
                "confidence": float(composed.get("confidence", 0.85) or 0.85),
            }
            sources[method] = "composed"
            _add_usage(usage_totals, composed.get("usage"))
            if last_model_name is None and composed.get("model_name"):
                last_model_name = composed["model_name"]
        else:
            by_method[method] = _fallback_mapping(method)
            sources[method] = "fallback"

    mappings = []
    for method in normalized:
        mapping = by_method.get(method)
        if mapping is None:  # defensive: every method is decided above
            mapping = _fallback_mapping(method)
            sources.setdefault(method, "fallback")
        mappings.append(mapping)

    return {
        "mappings": mappings,
        "sources": sources,
        "candidates": method_candidates,
        "picks": picks,
        "review": review,
        "needs_composition": needs_composition,
        "batches": batches,
        "usage_totals": usage_totals,
        "latency_ms": (time.monotonic() - started) * 1000,
        "model_name": last_model_name,
    }


async def run_canonical_name_llm(
    method: str,
    candidates_hint: list[str] | None = None,
    model_name: str = LLM_MODEL_DEFAULT,
    http_client: Any | None = None,
) -> dict[str, Any] | None:
    """Compose a canonical name for ``method`` with Gemini (production model).

    Mirrors ``agent.run_regex_fields``: missing ``GOOGLE_API_KEY`` -> stderr
    warning + ``None`` (the caller falls back to identity); Google model
    classes are imported lazily.  At most 12 existing common names from
    ``candidates_hint`` are offered under an explicit "only use one when it is
    exactly the same process" heading so the LLM prefers an existing canonical
    over inventing a near-duplicate.  The answer is run through
    ``canonical_sanitize`` (null-ish output -> ``None``).

    Returns ``{"common_name", "confidence", "model_name", "usage"}`` or ``None``.
    """
    if not os.environ.get("GOOGLE_API_KEY"):
        print(
            "warning: GOOGLE_API_KEY missing; skipping canonical-name LLM (identity fallback)",
            file=sys.stderr,
        )
        return None
    from pydantic_ai.models.google import GoogleModel
    from pydantic_ai.providers.google import GoogleProvider

    provider = GoogleProvider(http_client=http_client) if http_client is not None else GoogleProvider()
    model = GoogleModel(model_name, provider=provider)
    canonical_model = create_model(
        "CanonicalProcessName",
        common_name=(
            str,
            Field(description="The standardized canonical processing method name."),
        ),
        confidence=(
            float,
            Field(ge=0.0, le=1.0, default=0.85, description="Confidence that the canonical name is correct (0-1)."),
        ),
    )

    hint_names = list(dict.fromkeys(candidates_hint or []))[:12]
    lines = [f'Processing method to standardize: "{method}"']
    if hint_names:
        lines.append("")
        lines.append("Existing common names (only use one when it is exactly the same process):")
        lines.extend(f"- {name}" for name in hint_names)
    prompt = "\n".join(lines)

    with _optional_span("jev.process.canonical", method=method, model=model_name, candidates=len(hint_names)) as span:
        agent = Agent(model, output_type=canonical_model, instructions=CANONICAL_NAME_INSTRUCTIONS)
        result = await agent.run(prompt)
        raw_common_name = getattr(result.output, "common_name", None)
        common_name = canonical_sanitize(raw_common_name)
        if common_name is None:
            _logfire_info("jev.process.canonical.rejected", method=method, raw=str(raw_common_name))
            if span is not None:
                span.set_attribute("success", False)
            return None
        confidence = float(getattr(result.output, "confidence", 0.85) or 0.85)
        usage = _usage_dict(result.usage)
        if span is not None:
            span.set_attribute("common_name", common_name)
            span.set_attribute("confidence", confidence)
            span.set_attribute("model_name", result.response.model_name)
            span.set_attribute("success", True)
        _logfire_info(
            "jev.process.canonical.result", method=method, common_name=common_name, confidence=confidence
        )
        return {
            "common_name": common_name,
            "confidence": confidence,
            "model_name": result.response.model_name,
            "usage": usage,
        }


# ---------------------------------------------------------------------------
# Merge review: Score questions per canonical-name pair
# ---------------------------------------------------------------------------


def build_merge_model(pairs: list[tuple[str, str]]) -> tuple[type[BaseModel], dict[str, Any]]:
    """Build (output_model, meta) for pairs of canonical names.

    Each pair becomes a ``pair_<j>`` field typed ``MergeDecision`` (the
    docstrings carry the rubric: 0 = DIFFERENT, 1 = REVIEW, 2 = SAME); the
    field description names the two names.  ``meta["field_pairs"]`` maps every
    field back to its pair.
    """
    fields: dict[str, Any] = {}
    field_pairs: dict[str, list[str]] = {}

    for index, (a, b) in enumerate(pairs):
        field = f"pair_{index}"
        fields[field] = (
            MergeDecision,
            Field(
                description=(
                    f'Are "{a}" and "{b}" the same processing method? Same only when one canonical name describes '
                    "both; different when the base method, fermentation type, honey level, drying method, added "
                    "substrate or decaffeination method differs; review when uncertain or partially overlapping."
                )
            ),
        )
        field_pairs[field] = [a, b]

    model = create_model("JevProcessMerge", __doc__=_MERGE_MODEL_DOC, **fields)
    return model, {"field_pairs": field_pairs}


async def run_merge_review(
    vocabulary: ProcessVocabulary,
    pairs: list[tuple[str, str]] | None = None,
    max_pairs: int = 400,
    per_name: int = 5,
    batch_size: int = DEFAULT_MERGE_BATCH,
    model_pin: str = MODEL_PIN_DEFAULT,
    http_client: Any | None = None,
) -> dict[str, Any]:
    """Score canonical-name pairs with Jev and aggregate them into merges.

    ``pairs=None`` generates candidates with ``generate_merge_pairs`` (honoring
    ``max_pairs``/``per_name``); otherwise the given pairs are used.  Each batch
    becomes a group of 0..2 Score questions and the selected levels are fed to
    ``aggregate_merge_scores``.  A failed batch leaves its pairs unscored, which
    the aggregator treats as REVIEW (never auto-merge on missing evidence).

    Returns ``{"pairs", "pair_scores" [(a, b, score)], "merges", "components",
    "review_pairs", "review_components", "usage_totals", "latency_ms",
    "model_name", "batches"}``.
    """
    started = time.monotonic()
    pair_list = (
        list(pairs)
        if pairs is not None
        else generate_merge_pairs(vocabulary, max_pairs=max_pairs, per_name=per_name)
    )
    scores: dict[tuple[str, str], float | None] = {}
    batches: list[dict[str, Any]] = []
    usage_totals = _new_usage_totals()
    last_model_name: str | None = None
    batching_step = max(1, batch_size)

    for batch_index, start in enumerate(range(0, len(pair_list), batching_step)):
        batch = pair_list[start : start + batching_step]
        model, meta = build_merge_model(batch)
        record: dict[str, Any] = {
            "batch_index": batch_index,
            "size": len(batch),
            "latency_ms": 0.0,
            "model_name": None,
            "usage": {},
            "error": None,
        }
        batches.append(record)
        batch_start = time.monotonic()
        span: Any = None
        try:
            with _optional_span(
                "jev.process.merge", batch_index=batch_index, size=len(batch), model=model_pin
            ) as span:
                agent = _build_agent(model, _MERGE_INSTRUCTIONS, model_pin, http_client)
                result = await agent.run(_merge_state(batch))
                record["latency_ms"] = (time.monotonic() - batch_start) * 1000
                record["model_name"] = result.response.model_name
                record["usage"] = _usage_dict(result.usage)
                _add_usage(usage_totals, result.usage)
                last_model_name = result.response.model_name
                if span is not None:
                    span.set_attribute("model_name", result.response.model_name)
                    span.set_attribute("success", True)
            for field, pair in meta["field_pairs"].items():
                member = getattr(result.output, field, None)
                scores[tuple(pair)] = float(int(member)) if member is not None else None
            _logfire_info("jev.process.merge.batch", batch_index=batch_index, size=len(batch))
        except Exception as exc:  # noqa: BLE001
            record["latency_ms"] = (time.monotonic() - batch_start) * 1000
            record["error"] = f"{type(exc).__name__}: {exc}"
            if span is not None:
                span.set_attribute("success", False)
            _logfire_error(
                "jev.process.merge failed",
                batch_index=batch_index,
                size=len(batch),
                error=str(exc),
                error_type=type(exc).__name__,
            )
            print(
                f"warning: Jev merge batch {batch_index} failed ({type(exc).__name__}: {exc}); "
                "those pairs stay unscored (review)",
                file=sys.stderr,
            )
            for pair in batch:
                scores.setdefault(tuple(pair), None)

    aggregation = aggregate_merge_scores(pair_list, scores, vocabulary)
    return {
        "pairs": pair_list,
        "pair_scores": [(a, b, scores.get((a, b))) for a, b in pair_list],
        "merges": aggregation["merges"],
        "components": aggregation["components"],
        "review_pairs": aggregation["review_pairs"],
        "review_components": aggregation["review_components"],
        "usage_totals": usage_totals,
        "latency_ms": (time.monotonic() - started) * 1000,
        "model_name": last_model_name,
        "batches": batches,
    }


# ---------------------------------------------------------------------------
# Conflict audit: Score questions per common-name group
# ---------------------------------------------------------------------------


def build_conflict_model(
    groups: dict[str, list[str]], start_index: int = 0
) -> tuple[type[BaseModel], dict[str, Any]]:
    """Build (output_model, meta) for common-name groups.

    Each group becomes a ``group_<g>`` field typed ``ConflictDecision``
    (0 = KEEP, 1 = REVIEW, 2 = SPLIT); its description names the common name and
    lists the originals (clipped to the first 15 with ``(and N more)``).  Field
    numbering starts at ``start_index`` so ``run_conflicts`` can keep the field
    ids unique when it batches a large group set.  ``meta["field_groups"]`` maps
    every field back to ``[common_name, originals]``.
    """
    fields: dict[str, Any] = {}
    field_groups: dict[str, list[Any]] = {}

    for index, (common_name, originals) in enumerate(groups.items(), start=start_index):
        field = f"group_{index}"
        original_list = list(originals)
        shown = ", ".join(f'"{name}"' for name in original_list[:15])
        if len(original_list) > 15:
            shown += f" (and {len(original_list) - 15} more)"
        fields[field] = (
            ConflictDecision,
            Field(
                description=(
                    f'Do these original names all describe the same processing method, "{common_name}"? {shown}. '
                    "Keep when every original is the same process; split when at least one is fundamentally "
                    "different; review when the evidence is mixed or uncertain."
                )
            ),
        )
        field_groups[field] = [common_name, original_list]

    model = create_model("JevProcessConflict", __doc__=_CONFLICT_MODEL_DOC, **fields)
    return model, {"field_groups": field_groups}


async def run_conflicts(
    groups: dict[str, list[str]],
    protected_common_names: set[str] | None = None,
    batch_size: int = DEFAULT_CONFLICT_BATCH,
    model_pin: str = MODEL_PIN_DEFAULT,
    http_client: Any | None = None,
) -> dict[str, Any]:
    """Audit common-name groups with Jev and resolve them to keep/split/review.

    Each batch asks one 0..2 Score question per group; the levels are fed to
    ``compose_conflict_decisions`` (a reviewed/protected name is never demoted).
    A failed batch's groups stay unscored, which the composer keeps as-is with a
    "missing decision score" note.

    Returns ``{"group_scores": {field: score}, "group_keys": {field: common_name},
    "resolved", "kept", "notes", "usage_totals", "latency_ms", "model_name",
    "batches"}``.
    """
    started = time.monotonic()
    group_items = list(groups.items())
    group_scores: dict[str, float] = {}
    group_keys: dict[str, str] = {}
    batches: list[dict[str, Any]] = []
    usage_totals = _new_usage_totals()
    last_model_name: str | None = None
    batching_step = max(1, batch_size)

    for batch_index, start in enumerate(range(0, len(group_items), batching_step)):
        batch = group_items[start : start + batching_step]
        model, meta = build_conflict_model(
            {common: originals for common, originals in batch}, start_index=start
        )
        record: dict[str, Any] = {
            "batch_index": batch_index,
            "size": len(batch),
            "latency_ms": 0.0,
            "model_name": None,
            "usage": {},
            "error": None,
        }
        batches.append(record)
        batch_start = time.monotonic()
        span: Any = None
        try:
            with _optional_span(
                "jev.process.conflict", batch_index=batch_index, size=len(batch), model=model_pin
            ) as span:
                agent = _build_agent(model, _CONFLICT_INSTRUCTIONS, model_pin, http_client)
                result = await agent.run(_conflict_state(batch))
                record["latency_ms"] = (time.monotonic() - batch_start) * 1000
                record["model_name"] = result.response.model_name
                record["usage"] = _usage_dict(result.usage)
                _add_usage(usage_totals, result.usage)
                last_model_name = result.response.model_name
                if span is not None:
                    span.set_attribute("model_name", result.response.model_name)
                    span.set_attribute("success", True)
            for field, (common_name, _originals) in meta["field_groups"].items():
                member = getattr(result.output, field, None)
                if member is None:
                    continue
                group_scores[field] = float(int(member))
                group_keys[field] = common_name
            _logfire_info("jev.process.conflict.batch", batch_index=batch_index, size=len(batch))
        except Exception as exc:  # noqa: BLE001
            record["latency_ms"] = (time.monotonic() - batch_start) * 1000
            record["error"] = f"{type(exc).__name__}: {exc}"
            if span is not None:
                span.set_attribute("success", False)
            _logfire_error(
                "jev.process.conflict failed",
                batch_index=batch_index,
                size=len(batch),
                error=str(exc),
                error_type=type(exc).__name__,
            )
            print(
                f"warning: Jev conflict batch {batch_index} failed ({type(exc).__name__}: {exc}); "
                "those groups stay unscored (kept as-is)",
                file=sys.stderr,
            )

    answers: dict[str, float] = {
        group_keys[field]: score for field, score in group_scores.items() if field in group_keys
    }
    decisions = compose_conflict_decisions(groups, answers, protected_common_names)
    return {
        "group_scores": group_scores,
        "group_keys": group_keys,
        "resolved": decisions["resolved"],
        "kept": decisions["kept"],
        "notes": decisions["notes"],
        "usage_totals": usage_totals,
        "latency_ms": (time.monotonic() - started) * 1000,
        "model_name": last_model_name,
        "batches": batches,
    }
