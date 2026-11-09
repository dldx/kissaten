"""Pure-logic unit tests for the hybrid Jev processing-method categorizer helpers.

These tests exercise ``kissaten.ai.jev.process_common`` — normalization,
vocabulary/lookup building, deterministic mapping, candidate selection, Jev
question/answer composition, merge pairing/aggregation, conflict decisions and
the benchmark helpers — with hand-built mappings: no network, no DB, no
``pydantic_ai``, no ``duckdb``.

The fixture vocabulary mirrors the shapes of the real
``src/kissaten/database/processing_methods_mappings.json`` file on a small scale:
canonical names plus several messy aliases per canonical, including the
case/punctuation/duration variants the real pipeline sees.
"""

import json

import pytest

from kissaten.ai.jev import process_common as pc
from kissaten.ai.jev.process_common import (
    ALIAS_FUZZY_MIN,
    CATEGORIZE_INSTRUCTIONS,
    CATEGORIZE_TRACKED_METRICS,
    CONFLICT_GOLDEN_SET,
    DEFAULT_BATCH_SIZE,
    DEFAULT_CANDIDATE_LIMIT,
    DEFAULT_CONFLICT_BATCH,
    DEFAULT_MERGE_BATCH,
    FAMILY_TOPUP,
    MERGE_GOLDEN_SET,
    NONE_OF_THE_ABOVE,
    PROCESS_FUZZY_MIN,
    REVIEW_CONFIDENCE,
    ProcessVocabulary,
    aggregate_merge_scores,
    build_categorize_benchmark,
    build_categorize_question,
    build_categorize_state,
    build_vocabulary,
    candidate_descriptions,
    canonical_key,
    canonical_sanitize,
    compose_categorize_answers,
    compose_conflict_decisions,
    detect_base_processes,
    deterministic_map,
    existing_mapping_lookup,
    generate_merge_pairs,
    load_mappings_file,
    mapping_key,
    mapping_matches,
    normalize_process_text,
    prepare_benchmark,
    select_process_candidates,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MAPPINGS: list[dict] = [
    {"original_name": "Washed", "common_name": "Washed", "confidence": 1.0},
    {"original_name": "Fully Washed", "common_name": "Washed", "confidence": 1.0},
    {"original_name": "Natural", "common_name": "Natural", "confidence": 1.0},
    {"original_name": "Anaerobic Natural", "common_name": "Anaerobic Natural", "confidence": 1.0},
    {"original_name": "48 hrs Anaerobic Natural", "common_name": "Anaerobic Natural", "confidence": 1.0},
    {"original_name": "Anaerobic Natural 72h", "common_name": "Anaerobic Natural", "confidence": 1.0},
    {"original_name": "Honey", "common_name": "Honey", "confidence": 1.0},
    {"original_name": "Pulped Natural", "common_name": "Honey", "confidence": 1.0},
    {"original_name": "Ethyl Acetate Decaf", "common_name": "Ethyl Acetate Decaf", "confidence": 1.0},
    {"original_name": "EA Decaf", "common_name": "Ethyl Acetate Decaf", "confidence": 1.0},
    {"original_name": "Latic Fermentation Washed", "common_name": "Lactic Fermentation Washed", "confidence": 1.0},
    {"original_name": "Swiss Water Decaf", "common_name": "Swiss Water Decaf", "confidence": 1.0},
    {"original_name": "Wet Hulled", "common_name": "Wet Hulled", "confidence": 1.0},
    {"original_name": "Unknown", "common_name": "Unknown", "confidence": 1.0},
    {"original_name": "Dripper", "common_name": "Unknown", "confidence": 0.5},
]


@pytest.fixture()
def vocabulary() -> ProcessVocabulary:
    return build_vocabulary(MAPPINGS)


def _pair_set(pairs: list[tuple[str, str]]) -> set[frozenset[str]]:
    return {frozenset(pair) for pair in pairs}


def _choice(value: str, confidence: float = 1.0) -> dict:
    return {"type": "choice", "choice": value, "probabilities": {value: 1.0}, "confidence": confidence}


def _score(value: float) -> dict:
    return {"type": "score", "score": value, "legend": {}, "probabilities": {}, "confidence": 1.0}


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


class TestNormalizeProcessText:
    def test_strips_and_collapses_whitespace(self):
        assert normalize_process_text("  Fully   Washed  ") == "Fully Washed"

    def test_removes_trailing_quotes(self):
        assert normalize_process_text('Washed"') == "Washed"
        assert normalize_process_text("Washed'") == "Washed"
        assert normalize_process_text("Washed\"'") == "Washed"

    def test_falsy_input_is_empty(self):
        assert normalize_process_text("") == ""
        assert normalize_process_text("   ") == ""

    def test_mapping_key_lowercases_but_keeps_accents(self):
        assert mapping_key("EA Decaf") == "ea decaf"
        assert mapping_key("  Washed ") == "washed"
        # Mirrors the DB LOWER() join: accents are NOT stripped for lookups.
        assert mapping_key("Café") == "café"

    def test_canonical_key_normalizes_case_accents_and_punctuation(self):
        assert canonical_key("Café & Honey/Red") == "cafe honey red"
        assert canonical_key("Wet-Hulled") == "wet hulled"
        assert canonical_key("ETHYL ACETATE") == "ethyl acetate"
        assert canonical_key("Washed, 15h Fermentation") == "washed 15h fermentation"

    def test_canonical_key_matches_spelling_variants(self):
        assert canonical_key("Wet-Hulled") == canonical_key("wet hulled")
        assert canonical_key("EA Decaf") == canonical_key("ea decaf")
        assert canonical_key("Natural + Coconut") == canonical_key("Natural, Coconut")

    def test_canonical_key_falsy(self):
        assert canonical_key("") == ""
        assert canonical_key("   ") == ""


# ---------------------------------------------------------------------------
# Vocabulary / mapping lookup
# ---------------------------------------------------------------------------


class TestBuildVocabulary:
    def test_canonicals_sorted_by_alias_count_then_casefold(self, vocabulary):
        assert vocabulary.canonicals[0] == "Anaerobic Natural"  # 3 aliases
        assert vocabulary.canonicals == [
            "Anaerobic Natural",
            "Ethyl Acetate Decaf",
            "Honey",
            "Unknown",
            "Washed",
            "Lactic Fermentation Washed",
            "Natural",
            "Swiss Water Decaf",
            "Wet Hulled",
        ]

    def test_aliases_in_file_order(self, vocabulary):
        assert vocabulary.aliases["Washed"] == ["Washed", "Fully Washed"]
        assert vocabulary.aliases["Anaerobic Natural"] == [
            "Anaerobic Natural",
            "48 hrs Anaerobic Natural",
            "Anaerobic Natural 72h",
        ]
        assert vocabulary.aliases["Honey"] == ["Honey", "Pulped Natural"]

    def test_counts_are_file_occurrences(self, vocabulary):
        assert vocabulary.counts["Anaerobic Natural"] == 3
        assert vocabulary.counts["Washed"] == 2
        assert vocabulary.counts["Unknown"] == 2
        assert vocabulary.counts["Natural"] == 1

    def test_case_insensitive_alias_dedupe(self):
        vocab = build_vocabulary(
            [
                {"original_name": "WASHED", "common_name": "Washed"},
                {"original_name": "washed", "common_name": "Washed"},
                {"original_name": "Fully Washed", "common_name": "Washed"},
            ]
        )
        assert vocab.aliases["Washed"] == ["WASHED", "Fully Washed"]
        assert vocab.counts["Washed"] == 3

    def test_skips_empty_names(self):
        vocab = build_vocabulary(
            [
                {"original_name": "", "common_name": "Washed"},
                {"original_name": "Washed", "common_name": ""},
                {"original_name": "  ", "common_name": "Natural"},
                {"original_name": "Natural", "common_name": "Natural"},
            ]
        )
        assert vocab.canonicals == ["Natural"]
        assert vocab.aliases == {"Natural": ["Natural"]}

    def test_empty_mappings(self):
        vocab = build_vocabulary([])
        assert vocab.canonicals == []
        assert vocab.aliases == {}
        assert vocab.counts == {}


class TestExistingMappingLookup:
    def test_keyed_case_insensitively(self):
        lookup = existing_mapping_lookup(MAPPINGS)
        assert lookup["ea decaf"]["common_name"] == "Ethyl Acetate Decaf"
        assert lookup["fully washed"]["common_name"] == "Washed"
        assert lookup["ea decaf"]["confidence"] == 1.0

    def test_last_writer_wins(self):
        lookup = existing_mapping_lookup(
            [
                {"original_name": "Washed", "common_name": "Washed"},
                {"original_name": "WASHED", "common_name": "Wet Process"},
            ]
        )
        assert lookup["washed"]["common_name"] == "Wet Process"

    def test_skips_empty_names(self):
        lookup = existing_mapping_lookup(
            [
                {"original_name": "", "common_name": "Washed"},
                {"original_name": "Natural", "common_name": ""},
                {"original_name": "Honey", "common_name": "Honey"},
            ]
        )
        assert set(lookup) == {"honey"}

    def test_returned_dicts_are_copies(self):
        lookup = existing_mapping_lookup(MAPPINGS)
        lookup["ea decaf"]["common_name"] = "Mutated"
        assert existing_mapping_lookup(MAPPINGS)["ea decaf"]["common_name"] == "Ethyl Acetate Decaf"


class TestLoadMappingsFile:
    def test_loads_json_list(self, tmp_path):
        path = tmp_path / "mappings.json"
        path.write_text(json.dumps(MAPPINGS), encoding="utf-8")
        assert load_mappings_file(path) == MAPPINGS
        assert load_mappings_file(str(path)) == MAPPINGS


# ---------------------------------------------------------------------------
# Deterministic mapping
# ---------------------------------------------------------------------------


class TestDeterministicMap:
    def test_lookup_hit_is_returned(self, vocabulary):
        lookup = existing_mapping_lookup(MAPPINGS)
        result = deterministic_map("EA Decaf", lookup, vocabulary)
        assert result == {
            "original_name": "EA Decaf",
            "common_name": "Ethyl Acetate Decaf",
            "confidence": 1.0,
        }

    def test_lookup_hit_is_case_insensitive(self, vocabulary):
        lookup = existing_mapping_lookup(MAPPINGS)
        result = deterministic_map("ea decaf", lookup, vocabulary)
        assert result is not None
        assert result["common_name"] == "Ethyl Acetate Decaf"
        # The recorded entry wins, not the differently-cased input.
        assert result["original_name"] == "EA Decaf"

    def test_canonical_identity_match(self, vocabulary):
        # No lookup entry, but the input IS a canonical name modulo case/dashes.
        result = deterministic_map("WET-HULLED", {}, vocabulary)
        assert result == {"original_name": "WET-HULLED", "common_name": "Wet Hulled", "confidence": 1.0}

    def test_canonical_identity_prefers_canonical_spelling(self, vocabulary):
        result = deterministic_map("swiss water decaf", {}, vocabulary)
        assert result == {
            "original_name": "swiss water decaf",
            "common_name": "Swiss Water Decaf",
            "confidence": 1.0,
        }

    def test_unknown_method_returns_none(self, vocabulary):
        lookup = existing_mapping_lookup(MAPPINGS)
        assert deterministic_map("Totally New Process", lookup, vocabulary) is None

    def test_empty_method_returns_none(self, vocabulary):
        assert deterministic_map("", existing_mapping_lookup(MAPPINGS), vocabulary) is None


# ---------------------------------------------------------------------------
# Base-process detection
# ---------------------------------------------------------------------------


class TestDetectBaseProcesses:
    def test_washed_and_natural(self):
        assert detect_base_processes("Fully Washed") == frozenset({"washed"})
        assert detect_base_processes("Natural") == frozenset({"natural"})

    def test_anaerobic_natural(self):
        assert detect_base_processes("Anaerobic Natural") == frozenset({"natural", "anaerobic"})

    def test_decaf_implied_by_named_methods(self):
        for name in ("Decaf", "Swiss Water", "Ethyl Acetate Decaffeinated", "EA", "Sugarcane", "CO2", "caffeine"):
            assert "decaf" in detect_base_processes(name), name

    def test_decaf_ea_requires_word_boundary(self):
        assert "decaf" not in detect_base_processes("Idea Natural")

    def test_wet_hulled_variants(self):
        assert detect_base_processes("Wet-Hulled") == frozenset({"wet hulled"})
        assert detect_base_processes("Giling Basah") == frozenset({"wet hulled"})

    def test_distinct_traditional_tags(self):
        assert "semi washed" in detect_base_processes("Semi-Washed")
        assert "pulped natural" in detect_base_processes("Pulped Natural")
        assert "thermal shock" in detect_base_processes("Thermal Shock Washed")
        assert "co-ferment" in detect_base_processes("Red Fruits Co-Fermented")
        assert "anoxic" in detect_base_processes("Anoxic Washed")
        assert "oxydator" in detect_base_processes("Oxydator Natural")
        assert "yeast" in detect_base_processes("Yeast Inoculation")

    def test_empty_is_empty(self):
        assert detect_base_processes("") == frozenset()


# ---------------------------------------------------------------------------
# Candidate selection
# ---------------------------------------------------------------------------


class TestSelectProcessCandidates:
    def test_recall_anaerobic_natural(self, vocabulary):
        candidates = select_process_candidates("48 hrs Anaerobic Natural", vocabulary)
        assert candidates[0] == "Anaerobic Natural"

    def test_recall_fully_washed(self, vocabulary):
        assert select_process_candidates("Fully Washed", vocabulary)[0] == "Washed"

    def test_recall_ea_decaf(self, vocabulary):
        assert select_process_candidates("EA Decaf", vocabulary)[0] == "Ethyl Acetate Decaf"

    def test_recall_dripper_alias(self, vocabulary):
        assert select_process_candidates("Dripper", vocabulary) == ["Unknown"]

    def test_recall_pulped_natural_alias(self, vocabulary):
        candidates = select_process_candidates("Pulped Natural", vocabulary)
        assert candidates[0] == "Honey"
        # Natural also shares the base method, so it stays available as a candidate.
        assert "Natural" in candidates

    def test_recall_latic_typo(self, vocabulary):
        assert select_process_candidates("Latic Fermentation Washed", vocabulary)[0] == "Lactic Fermentation Washed"

    def test_recall_punctuated_washed_fermentation(self, vocabulary):
        vocab = build_vocabulary(
            [
                *MAPPINGS,
                {"original_name": "Washed, 15h Fermentation", "common_name": "Washed, 15h Fermentation"},
            ]
        )
        assert select_process_candidates("Washed; 15h Fermentation", vocab)[0] == "Washed, 15h Fermentation"

    def test_base_process_overlap_offers_both_families(self, vocabulary):
        candidates = select_process_candidates("Anaerobic Honey", vocabulary)
        assert "Anaerobic Natural" in candidates
        assert "Honey" in candidates

    def test_limit_is_respected(self, vocabulary):
        full = select_process_candidates("Washed Natural", vocabulary)
        limited = select_process_candidates("Washed Natural", vocabulary, limit=2)
        assert len(full) > 2
        # The ranked ``limit`` matches are the prefix; family-fallback extras may
        # be appended after them (never displacing the ranked matches).
        assert limited[:2] == full[:2]
        assert len(limited) <= 2 + FAMILY_TOPUP

    def test_zero_limit_returns_empty(self, vocabulary):
        assert select_process_candidates("Washed", vocabulary, limit=0) == []

    def test_empty_method_returns_empty(self, vocabulary):
        assert select_process_candidates("", vocabulary) == []

    def test_unrelated_canonicals_are_excluded(self, vocabulary):
        candidates = select_process_candidates("Dripper", vocabulary)
        assert "Natural" not in candidates
        assert "Washed" not in candidates

    def test_deterministic_ordering(self, vocabulary):
        assert select_process_candidates("Washed Natural", vocabulary) == select_process_candidates(
            "Washed Natural", vocabulary
        )

    def test_family_fallback_adds_marker_canonical_without_literal_overlap(self):
        # "Swiss Water" implies the decaf marker without containing the word, so
        # it has no n-gram/alias overlap with "EA Decaf" but must still be offered.
        vocab = build_vocabulary(
            [
                {"original_name": "Ethyl Acetate Decaf", "common_name": "Ethyl Acetate Decaf"},
                {"original_name": "Swiss Water", "common_name": "Swiss Water"},
            ]
        )
        candidates = select_process_candidates("EA Decaf", vocab)
        assert "Ethyl Acetate Decaf" in candidates
        assert "Swiss Water" in candidates

    def test_family_fallback_promotes_initialism_match(self):
        vocab = build_vocabulary(
            [
                {"original_name": "Sugarcane EA Decaf One", "common_name": "Sugarcane EA Decaf One"},
                {"original_name": "Sugarcane EA Decaf Two", "common_name": "Sugarcane EA Decaf Two"},
                {"original_name": "Sugarcane EA Decaf Three", "common_name": "Sugarcane EA Decaf Three"},
                {"original_name": "Ethyl Acetate Decaf", "common_name": "Ethyl Acetate Decaf"},
            ]
        )
        candidates = select_process_candidates("EA Decaf", vocab, limit=1)
        # The ranked match keeps rank 1; the abbreviation spelling-out is the
        # first family-fallback extra even though it scored lowest on wording.
        assert candidates[0] == "Sugarcane EA Decaf One"
        assert candidates[1] == "Ethyl Acetate Decaf"

    def test_family_fallback_capped(self):
        mappings = [
            {"original_name": f"Anaerobic Natural Variant {index}", "common_name": f"Anaerobic Natural Variant {index}"}
            for index in range(10)
        ]
        vocab = build_vocabulary(mappings)
        candidates = select_process_candidates("Anaerobic Natural", vocab, limit=1)
        assert len(candidates) == 1 + FAMILY_TOPUP


class TestCandidateDescriptions:
    def test_includes_canonical_and_aliases(self, vocabulary):
        descriptions = candidate_descriptions(vocabulary, ["Washed"])
        assert descriptions["Washed"] == (
            'Canonical processing method "Washed". Previously used for: "Washed", "Fully Washed".'
        )

    def test_max_aliases_folds_the_tail(self, vocabulary):
        descriptions = candidate_descriptions(vocabulary, ["Anaerobic Natural"], max_aliases=1)
        assert descriptions["Anaerobic Natural"] == (
            'Canonical processing method "Anaerobic Natural". Previously used for: "Anaerobic Natural" (and 2 more).'
        )

    def test_long_aliases_are_clipped(self):
        long_alias = "A" * 60
        vocab = build_vocabulary([{"original_name": long_alias, "common_name": "Mystery"}])
        descriptions = candidate_descriptions(vocab, ["Mystery"], alias_max_len=10)
        assert f'"{"A" * 10}..."' in descriptions["Mystery"]

    def test_short_alias_is_not_clipped(self, vocabulary):
        descriptions = candidate_descriptions(vocabulary, ["Honey"], alias_max_len=42)
        assert '"Honey"' in descriptions["Honey"]
        assert "..." not in descriptions["Honey"]

    def test_no_aliases_omits_the_clause(self):
        vocab = ProcessVocabulary(canonicals=["Mystery"], aliases={}, counts={})
        assert candidate_descriptions(vocab, ["Mystery"]) == {"Mystery": 'Canonical processing method "Mystery".'}


# ---------------------------------------------------------------------------
# Jev question / state composition
# ---------------------------------------------------------------------------


class TestBuildCategorizeQuestion:
    def test_includes_the_input_string(self):
        question = build_categorize_question("48 hrs Anaerobic Natural")
        assert '"48 hrs Anaerobic Natural"' in question

    def test_requires_exact_identity(self):
        question = build_categorize_question("Washed")
        assert "EXACTLY the same process" in question
        assert "merely similar candidates must NOT be selected" in question

    def test_none_of_the_above_option(self):
        assert NONE_OF_THE_ABOVE in build_categorize_question("Washed")

    def test_lists_non_mergeable_distinctions(self):
        question = build_categorize_question("Washed")
        for fragment in (
            "Natural vs Washed vs Honey",
            "aerobic vs anaerobic",
            "Swiss Water vs EA",
            "Black vs Red vs Yellow",
            "lychee vs mango",
        ):
            assert fragment in question

    def test_lists_merge_irrelevant_differences(self):
        question = build_categorize_question("Washed")
        for fragment in ("step order", "time/duration info", "48hrs", "adverbs", "punctuation", "Coco", "Fully Washed"):
            assert fragment in question

    def test_instructions_share_the_rules(self):
        assert NONE_OF_THE_ABOVE in CATEGORIZE_INSTRUCTIONS
        assert "EXACTLY the same process" in CATEGORIZE_INSTRUCTIONS
        assert "Swiss Water vs EA" in CATEGORIZE_INSTRUCTIONS
        assert "lychee vs mango" in CATEGORIZE_INSTRUCTIONS
        assert "Coco = Coconut" in CATEGORIZE_INSTRUCTIONS

    def test_prefers_plainer_canonical_over_duration_variant(self):
        for text in (build_categorize_question("Washed"), CATEGORIZE_INSTRUCTIONS):
            assert "plainer" in text
            assert "defining difference" in text

    def test_none_contract_rejects_merely_resembling_candidates(self):
        assert "only resembles the input" in build_categorize_question("Washed")
        assert "only resembles the input" in CATEGORIZE_INSTRUCTIONS


class TestBuildCategorizeState:
    def test_numbered_list(self):
        state = build_categorize_state(["Washed", "Natural"])
        assert state == 'Normalize these coffee processing methods:\n1. "Washed"\n2. "Natural"'

    def test_empty_methods(self):
        assert build_categorize_state([]) == "Normalize these coffee processing methods:"


# ---------------------------------------------------------------------------
# Answer composition
# ---------------------------------------------------------------------------


class TestComposeCategorizeAnswers:
    def _meta(self) -> dict:
        return {
            "field_methods": {
                "m0": "48 hrs Anaerobic Natural",
                "m1": "Dripper",
                "m2": "Washed",
                "m3": "Mystery Blend",
            },
            "field_candidates": {
                "m0": ["Anaerobic Natural", NONE_OF_THE_ABOVE],
                "m1": ["Unknown", NONE_OF_THE_ABOVE],
                "m2": ["Washed", NONE_OF_THE_ABOVE],
                "m3": [NONE_OF_THE_ABOVE],
            },
        }

    def test_choice_becomes_a_pick(self):
        result = compose_categorize_answers(
            ["48 hrs Anaerobic Natural"],
            {"m0": _choice("Anaerobic Natural", confidence=0.95)},
            self._meta(),
        )
        assert result["picks"] == [
            {"original_name": "48 hrs Anaerobic Natural", "common_name": "Anaerobic Natural", "confidence": 0.95}
        ]
        assert result["review"] == []
        assert result["needs_composition"] == []

    def test_none_of_the_above_needs_composition(self):
        result = compose_categorize_answers(["Dripper"], {"m1": _choice(NONE_OF_THE_ABOVE)}, self._meta())
        assert result["picks"] == []
        assert result["needs_composition"] == ["Dripper"]

    def test_missing_answer_needs_composition(self):
        result = compose_categorize_answers(["Washed"], {}, self._meta())
        assert result["needs_composition"] == ["Washed"]

    def test_method_without_a_field_needs_composition(self):
        result = compose_categorize_answers(["No Field Method"], {}, self._meta())
        assert result["needs_composition"] == ["No Field Method"]

    def test_needs_composition_preserves_input_order(self):
        result = compose_categorize_answers(
            ["Washed", "Dripper", "48 hrs Anaerobic Natural"],
            {"m0": _choice("Anaerobic Natural")},
            self._meta(),
        )
        assert result["needs_composition"] == ["Washed", "Dripper"]

    def test_low_confidence_answer_goes_to_review(self):
        result = compose_categorize_answers(["Washed"], {"m2": _choice("Washed", confidence=0.5)}, self._meta())
        assert len(result["picks"]) == 1
        assert result["review"] == result["picks"]
        assert result["review"][0]["confidence"] == 0.5

    def test_confidence_override_by_field(self):
        result = compose_categorize_answers(
            ["48 hrs Anaerobic Natural"],
            {"m0": _choice("Anaerobic Natural", confidence=0.95)},
            self._meta(),
            confidences={"m0": 0.4},
        )
        assert result["picks"][0]["confidence"] == 0.4
        assert len(result["review"]) == 1

    def test_confidence_override_by_method(self):
        result = compose_categorize_answers(
            ["Washed"],
            {"m2": _choice("Washed", confidence=0.9)},
            self._meta(),
            confidences={"Washed": 0.3},
        )
        assert result["picks"][0]["confidence"] == 0.3

    def test_missing_confidence_defaults_to_one(self):
        result = compose_categorize_answers(["Washed"], {"m2": {"type": "choice", "choice": "Washed"}}, self._meta())
        assert result["picks"][0]["confidence"] == 1.0

    def test_empty_inputs(self):
        assert compose_categorize_answers([], {}, {}) == {"picks": [], "review": [], "needs_composition": []}


# ---------------------------------------------------------------------------
# Canonical sanitize / match
# ---------------------------------------------------------------------------


class TestCanonicalSanitize:
    def test_collapses_whitespace_and_trims_period(self):
        assert canonical_sanitize("  Washed   Honey. ") == "Washed Honey"

    def test_strips_surrounding_quotes(self):
        assert canonical_sanitize('"Washed"') == "Washed"
        assert canonical_sanitize("'Washed Honey.'") == "Washed Honey"

    def test_null_ish_values_become_none(self):
        for value in (None, "", "  ", "null", "none", "*"):
            assert canonical_sanitize(value) is None

    def test_over_120_chars_is_rejected(self):
        assert canonical_sanitize("A" * 121) is None
        assert canonical_sanitize("A" * 120) == "A" * 120

    def test_non_str_is_stringified(self):
        assert canonical_sanitize(12.5) == "12.5"


class TestMappingMatches:
    def test_canonical_equality(self):
        assert mapping_matches("EA Decaf", "ea decaf") is True
        assert mapping_matches("Wet-Hulled", "Wet Hulled") is True
        assert mapping_matches("Washed", "Honey") is False

    def test_empty_values(self):
        assert mapping_matches("", "") is True
        assert mapping_matches(None, None) is True
        assert mapping_matches("Washed", "") is False


# ---------------------------------------------------------------------------
# Merge pair generation
# ---------------------------------------------------------------------------


class TestGenerateMergePairs:
    def test_same_family_pair(self, vocabulary):
        pairs = _pair_set(generate_merge_pairs(vocabulary))
        assert frozenset(("Natural", "Anaerobic Natural")) in pairs

    def test_alias_link_pair(self):
        vocab = build_vocabulary(
            [
                {"original_name": "Honey", "common_name": "Honey"},
                {"original_name": "PN", "common_name": "Pulped Natural"},
                {"original_name": "Pulped Natural", "common_name": "Honey"},
            ]
        )
        pairs = _pair_set(generate_merge_pairs(vocab))
        assert frozenset(("Honey", "Pulped Natural")) in pairs

    def test_initialism_pair(self):
        vocab = build_vocabulary(
            [
                {"original_name": "EA Decaf", "common_name": "EA Decaf"},
                {"original_name": "Ethyl Acetate Decaf", "common_name": "Ethyl Acetate Decaf"},
            ]
        )
        pairs = _pair_set(generate_merge_pairs(vocab))
        assert frozenset(("EA Decaf", "Ethyl Acetate Decaf")) in pairs

    def test_unrelated_canonicals_are_excluded(self, vocabulary):
        pairs = _pair_set(generate_merge_pairs(vocabulary))
        assert frozenset(("Unknown", "Natural")) not in pairs
        assert frozenset(("Wet Hulled", "Washed")) not in pairs

    def test_per_name_cap(self, vocabulary):
        pairs = generate_merge_pairs(vocabulary, per_name=1, max_pairs=100)
        degree: dict[str, int] = {}
        for a, b in pairs:
            degree[a] = degree.get(a, 0) + 1
            degree[b] = degree.get(b, 0) + 1
        assert all(count <= 1 for count in degree.values())

    def test_global_cap(self, vocabulary):
        assert len(generate_merge_pairs(vocabulary, max_pairs=1)) == 1

    def test_deterministic_ordering(self, vocabulary):
        assert generate_merge_pairs(vocabulary) == generate_merge_pairs(vocabulary)

    def test_too_small_vocabulary(self, vocabulary):
        vocab = ProcessVocabulary(canonicals=["Natural"], aliases={"Natural": ["Natural"]}, counts={"Natural": 1})
        assert generate_merge_pairs(vocab) == []
        assert generate_merge_pairs(vocabulary, max_pairs=0) == []
        assert generate_merge_pairs(vocabulary, per_name=0) == []


# ---------------------------------------------------------------------------
# Merge score aggregation
# ---------------------------------------------------------------------------


class TestAggregateMergeScores:
    def test_same_edge_merges_with_popularity_target(self):
        vocab = build_vocabulary(
            [
                {"original_name": "Washed", "common_name": "Washed"},
                {"original_name": "Fully Washed", "common_name": "Washed"},
                {"original_name": "Wet Process", "common_name": "Washed"},
                {"original_name": "Fully Washed", "common_name": "Fully Washed"},
            ]
        )
        result = aggregate_merge_scores([("Washed", "Fully Washed")], {("Washed", "Fully Washed"): 2}, vocab)
        assert result["merges"] == {"Fully Washed": "Washed"}
        assert result["components"] == [["Fully Washed", "Washed"]]
        assert result["review_pairs"] == []
        assert result["review_components"] == []

    def test_counts_tiebreak_by_casefold_name(self):
        vocab = build_vocabulary(
            [
                {"original_name": "Zeta", "common_name": "Zeta"},
                {"original_name": "Alpha", "common_name": "Alpha"},
            ]
        )
        result = aggregate_merge_scores([("Zeta", "Alpha")], [2], vocab)
        assert result["merges"] == {"Zeta": "Alpha"}

    def test_without_vocabulary_casefold_name_wins(self):
        result = aggregate_merge_scores([("Zeta", "Alpha")], [2])
        assert result["merges"] == {"Zeta": "Alpha"}

    def test_review_edge_inside_a_component_blocks_the_merge(self):
        pairs = [("A", "B"), ("B", "C"), ("A", "C")]
        result = aggregate_merge_scores(pairs, {("A", "B"): 2, ("B", "C"): 2, ("A", "C"): 1})
        assert result["merges"] == {}
        assert result["components"] == [["A", "B", "C"]]
        assert result["review_components"] == [["A", "B", "C"]]
        assert ("A", "C", 1) in result["review_pairs"]

    def test_missing_score_is_review(self):
        result = aggregate_merge_scores([("Natural", "Anaerobic Natural")], {})
        assert result["merges"] == {}
        assert result["review_pairs"] == [("Natural", "Anaerobic Natural", None)]
        assert result["review_components"] == []

    def test_none_score_is_review(self):
        result = aggregate_merge_scores([("Natural", "Anaerobic Natural")], {("Natural", "Anaerobic Natural"): None})
        assert result["review_pairs"] == [("Natural", "Anaerobic Natural", None)]

    def test_different_score_is_not_reviewed(self):
        result = aggregate_merge_scores([("Natural", "Washed")], {("Natural", "Washed"): 0})
        assert result == {"merges": {}, "components": [], "review_pairs": [], "review_components": []}

    def test_reversed_tuple_key_is_accepted(self, vocabulary):
        result = aggregate_merge_scores([("Washed", "Fully Washed")], {("Fully Washed", "Washed"): 2}, vocabulary)
        assert result["merges"] == {"Fully Washed": "Washed"}

    def test_scores_accept_a_parallel_sequence(self, vocabulary):
        result = aggregate_merge_scores([("Washed", "Fully Washed")], [2], vocabulary)
        assert result["merges"] == {"Fully Washed": "Washed"}

    def test_components_are_deterministic(self):
        pairs = [("B", "A"), ("C", "D")]
        scores = {("B", "A"): 2, ("C", "D"): 2}
        first = aggregate_merge_scores(pairs, scores)
        assert first == aggregate_merge_scores(pairs, scores)


# ---------------------------------------------------------------------------
# Conflict decisions
# ---------------------------------------------------------------------------


class TestComposeConflictDecisions:
    def test_keep_score_keeps_the_merge(self):
        result = compose_conflict_decisions(
            {"Natural": ["Natural", "Natural Process"]},
            {"Natural": _score(0)},
        )
        assert result["resolved"] == {}
        assert result["kept"] == {"Natural": ["Natural", "Natural Process"]}
        assert result["notes"]["Natural"] == "confirmed: same process"

    def test_split_score_resolves(self):
        result = compose_conflict_decisions(
            {"Anaerobic Natural": ["Natural", "Anaerobic Natural"]},
            {"Anaerobic Natural": _score(2)},
        )
        assert result["resolved"] == {"Anaerobic Natural": ["Natural", "Anaerobic Natural"]}
        assert result["kept"] == {}
        assert "split" in result["notes"]["Anaerobic Natural"]

    def test_review_score_resolves_as_manual_review(self):
        result = compose_conflict_decisions(
            {"Honey": ["Honey", "Black Honey"]},
            {"Honey": _score(1)},
        )
        assert result["resolved"] == {"Honey": ["Honey", "Black Honey"]}
        assert "review" in result["notes"]["Honey"]

    def test_missing_score_keeps_the_group(self):
        result = compose_conflict_decisions({"Washed": ["Washed", "Fully Washed"]}, {})
        assert result["kept"] == {"Washed": ["Washed", "Fully Washed"]}
        assert "missing" in result["notes"]["Washed"]

    def test_bare_numeric_answer_is_accepted(self):
        result = compose_conflict_decisions({"Washed": ["Washed", "Fully Washed"]}, {"Washed": 2})
        assert result["resolved"] == {"Washed": ["Washed", "Fully Washed"]}

    def test_protected_name_is_never_demoted(self):
        result = compose_conflict_decisions(
            {"Natural": ["Natural", "Anaerobic Natural"]},
            {"Natural": _score(2)},
            protected_common_names={"natural"},
        )
        assert result["resolved"] == {}
        assert result["kept"] == {"Natural": ["Natural", "Anaerobic Natural"]}
        assert "reviewed name never demoted" in result["notes"]["Natural"]

    def test_protected_low_score_is_still_kept(self):
        result = compose_conflict_decisions(
            {"Natural": ["Natural", "Natural Process"]},
            {"Natural": _score(0)},
            protected_common_names={"natural"},
        )
        assert result["kept"] == {"Natural": ["Natural", "Natural Process"]}

    def test_originals_are_copied_not_aliased(self):
        originals = ["Washed", "Fully Washed"]
        result = compose_conflict_decisions({"Washed": originals}, {"Washed": _score(0)})
        result["kept"]["Washed"].append("Mutated")
        assert originals == ["Washed", "Fully Washed"]

    def test_notes_are_deterministic(self):
        groups = {"Natural": ["Natural", "Natural Process"]}
        answers = {"Natural": _score(1)}
        assert compose_conflict_decisions(groups, answers) == compose_conflict_decisions(groups, answers)


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------


class TestBenchmarkHelpers:
    def test_sample_is_deterministic(self):
        assert build_categorize_benchmark(MAPPINGS, limit=5, seed=42) == build_categorize_benchmark(
            MAPPINGS, limit=5, seed=42
        )

    def test_sample_has_exactly_the_expected_fields(self):
        sample = build_categorize_benchmark(MAPPINGS, limit=5)
        assert len(sample) == 5
        assert all(set(entry) == {"original_name", "common_name"} for entry in sample)

    def test_sample_limit_larger_than_file(self):
        sample = build_categorize_benchmark(MAPPINGS, limit=1000)
        assert len(sample) == len(MAPPINGS)

    def test_zero_limit_is_empty(self):
        assert build_categorize_benchmark(MAPPINGS, limit=0) == []

    def test_empty_entries_are_skipped(self):
        sample = build_categorize_benchmark(
            [
                {"original_name": "", "common_name": "Washed"},
                {"original_name": "Washed", "common_name": ""},
                {"original_name": "Washed", "common_name": "Washed"},
            ],
            limit=10,
        )
        assert sample == [{"original_name": "Washed", "common_name": "Washed"}]

    def test_prepare_benchmark_removes_held_out_lookup(self):
        sample = [{"original_name": "EA Decaf", "common_name": "Ethyl Acetate Decaf"}]
        _, lookup = prepare_benchmark(MAPPINGS, sample)
        assert "ea decaf" not in lookup
        assert lookup["fully washed"]["common_name"] == "Washed"

    def test_prepare_benchmark_removes_held_out_aliases(self):
        sample = [{"original_name": "48 hrs Anaerobic Natural", "common_name": "Anaerobic Natural"}]
        vocab, _ = prepare_benchmark(MAPPINGS, sample)
        assert "48 hrs Anaerobic Natural" not in vocab.aliases["Anaerobic Natural"]
        assert vocab.aliases["Anaerobic Natural"] == ["Anaerobic Natural", "Anaerobic Natural 72h"]

    def test_prepare_benchmark_keeps_expected_canonical_by_default(self):
        sample = [{"original_name": "EA Decaf", "common_name": "Ethyl Acetate Decaf"}]
        vocab, _ = prepare_benchmark(MAPPINGS, sample)
        assert "Ethyl Acetate Decaf" in vocab.canonicals

    def test_prepare_benchmark_cold_removes_expected_canonical(self):
        sample = [{"original_name": "EA Decaf", "common_name": "Ethyl Acetate Decaf"}]
        vocab, _ = prepare_benchmark(MAPPINGS, sample, cold=True)
        assert "Ethyl Acetate Decaf" not in vocab.canonicals

    def test_prepare_benchmark_no_leakage_from_other_entry(self):
        sample = [{"original_name": "Washed", "common_name": "Washed"}]
        vocab, lookup = prepare_benchmark(MAPPINGS, sample)
        assert "washed" not in lookup
        # The held-out original is gone from every alias list, not just its own.
        assert all("Washed" not in aliases for aliases in vocab.aliases.values())


# ---------------------------------------------------------------------------
# Golden sets / constants
# ---------------------------------------------------------------------------


class TestGoldenSets:
    def test_merge_golden_set_shape(self):
        assert len(MERGE_GOLDEN_SET) == 16
        for entry in MERGE_GOLDEN_SET:
            assert set(entry) == {"a", "b", "expected"}
            assert entry["expected"] in {"same", "review", "different"}

    def test_merge_golden_set_expected_cases(self):
        expectations = {frozenset((entry["a"], entry["b"])): entry["expected"] for entry in MERGE_GOLDEN_SET}
        assert expectations[frozenset(("Natural", "Natural Process"))] == "same"
        assert expectations[frozenset(("EA Decaf", "Ethyl Acetate Decaffeinated"))] == "same"
        assert expectations[frozenset(("Pulped Natural", "Honey Process"))] == "same"
        assert expectations[frozenset(("Fully Washed", "Washed"))] == "same"
        assert expectations[frozenset(("Natural", "Anaerobic Natural"))] == "different"
        assert expectations[frozenset(("Yellow Honey", "Red Honey"))] == "different"
        assert expectations[frozenset(("Swiss Water Decaf", "EA Decaf"))] == "different"
        assert expectations[frozenset(("Black Honey", "Honey"))] == "review"

    def test_conflict_golden_set_shape(self):
        assert len(CONFLICT_GOLDEN_SET) == 7
        for entry in CONFLICT_GOLDEN_SET:
            assert set(entry) == {"common_name", "originals", "expected"}
            assert entry["expected"] in {0, 1, 2}
            assert entry["originals"]
        names = [entry["common_name"] for entry in CONFLICT_GOLDEN_SET]
        assert len(names) == len(set(names))

    def test_conflict_golden_set_expected_cases(self):
        expectations = {entry["common_name"]: entry["expected"] for entry in CONFLICT_GOLDEN_SET}
        assert expectations["Natural"] == 0
        assert expectations["Washed"] == 0
        assert expectations["Anaerobic Natural"] == 2
        assert expectations["Honey"] == 1


class TestConstants:
    def test_constant_values(self):
        assert NONE_OF_THE_ABOVE == "none_of_the_above"
        assert DEFAULT_CANDIDATE_LIMIT == 16
        assert FAMILY_TOPUP == 4
        assert PROCESS_FUZZY_MIN == 0.82
        assert ALIAS_FUZZY_MIN == 0.78
        assert REVIEW_CONFIDENCE == 0.6
        assert DEFAULT_BATCH_SIZE == 15
        assert DEFAULT_MERGE_BATCH == 30
        assert DEFAULT_CONFLICT_BATCH == 15

    def test_tracked_metrics(self):
        assert CATEGORIZE_TRACKED_METRICS == [
            "deterministic",
            "candidate_recall",
            "jev_correct",
            "false_merge",
            "none_of_the_above",
            "composition_match",
            "overall_match",
        ]


class TestModulePurity:
    def test_no_network_or_db_imports(self):
        # The stage-2 adapter must be able to import this module without pulling
        # in pydantic_ai / duckdb machinery.
        source = pc.__file__
        assert source is not None
        with open(source, encoding="utf-8") as handle:
            text = handle.read()
        assert "import duckdb" not in text
        assert "import pydantic_ai" not in text
        assert "from pydantic_ai" not in text
