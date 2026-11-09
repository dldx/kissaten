"""No-network unit tests for the Jev process-categorizer adapter (stage 2).

These tests exercise ``kissaten.ai.jev.process_agent`` — the per-batch output
models (Choices categorizer + Score rubrics), the adapter-output extraction and
the deterministic/no-candidate paths of ``run_categorize`` — with hand-built
vocabularies and fake outputs: no network, no DB, no model calls.

The deterministic-only paths (all methods resolved by ``deterministic_map`` or
with no candidates offered) never construct an Agent, so they run offline.
"""

from types import SimpleNamespace

import pytest
from pydantic_ai._utils import enum_member_docstrings

from kissaten.ai.jev import process_agent as pa
from kissaten.ai.jev.process_common import (
    NONE_OF_THE_ABOVE,
    ProcessVocabulary,
    build_vocabulary,
    existing_mapping_lookup,
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
    {"original_name": "Ethyl Acetate Decaf", "common_name": "Ethyl Acetate Decaf", "confidence": 1.0},
    {"original_name": "EA Decaf", "common_name": "Ethyl Acetate Decaf", "confidence": 1.0},
    {"original_name": "Honey", "common_name": "Honey", "confidence": 1.0},
    {"original_name": "Pulped Natural", "common_name": "Honey", "confidence": 1.0},
    {"original_name": "Unknown", "common_name": "Unknown", "confidence": 1.0},
    {"original_name": "Dripper", "common_name": "Unknown", "confidence": 0.5},
]

# Verified to match no canonical in the fixture vocabulary, so Jev is offered
# no candidates for it.
NO_CANDIDATE_METHOD = "qwertyuiop zxcvbnm"


@pytest.fixture()
def vocabulary() -> ProcessVocabulary:
    return build_vocabulary(MAPPINGS)


@pytest.fixture()
def lookup() -> dict[str, dict]:
    return existing_mapping_lookup(MAPPINGS)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestEnums:
    def test_merge_decision_members_and_docstrings(self):
        assert [int(member) for member in pa.MergeDecision] == [0, 1, 2]
        assert (pa.MergeDecision.DIFFERENT, pa.MergeDecision.REVIEW, pa.MergeDecision.SAME) == (0, 1, 2)
        for member in pa.MergeDecision:
            assert member.__doc__ and len(member.__doc__.strip()) > 10

    def test_conflict_decision_members_and_docstrings(self):
        assert [int(member) for member in pa.ConflictDecision] == [0, 1, 2]
        assert (pa.ConflictDecision.KEEP, pa.ConflictDecision.REVIEW, pa.ConflictDecision.SPLIT) == (0, 1, 2)
        # The adapter reads member docstrings from source (pydantic-ai's
        # enum_member_docstrings), so assert through the same extraction.
        docs = enum_member_docstrings(pa.ConflictDecision)
        assert set(docs) == {"KEEP", "REVIEW", "SPLIT"}
        for text in docs.values():
            assert len(text.strip()) > 10
        assert "honey level" in docs["REVIEW"] and "extended fermentation" in docs["REVIEW"]
        assert "aerobic vs anaerobic" in docs["SPLIT"] and "substrates" in docs["SPLIT"]


# ---------------------------------------------------------------------------
# build_categorize_model
# ---------------------------------------------------------------------------


class TestBuildCategorizeModel:
    def test_builds_fields_only_for_methods_with_candidates(self, vocabulary):
        model, meta = pa.build_categorize_model(["Washed", NO_CANDIDATE_METHOD], vocabulary)
        assert "map_0" in model.model_fields
        assert "map_1" not in model.model_fields
        assert meta["field_methods"] == {"map_0": "Washed"}
        assert meta["field_candidates"]["map_0"] == select_process_candidates("Washed", vocabulary)

    def test_field_names_track_batch_index(self, vocabulary):
        model, meta = pa.build_categorize_model([NO_CANDIDATE_METHOD, "Washed"], vocabulary)
        assert list(model.model_fields) == ["map_1"]
        assert meta["field_methods"] == {"map_1": "Washed"}

    def test_criteria_include_aliases_and_none_of_the_above(self, vocabulary):
        model, _meta = pa.build_categorize_model(["Fully washed"], vocabulary)
        options = model.model_json_schema()["properties"]["map_0"]["anyOf"]
        assert [option["const"] for option in options] == ["Washed", NONE_OF_THE_ABOVE]
        descriptions = {option["const"]: option.get("description", "") for option in options}
        assert "Fully Washed" in descriptions["Washed"]
        assert "new canonical name" in descriptions[NONE_OF_THE_ABOVE]

    def test_question_description_and_model_metadata(self, vocabulary):
        model, _meta = pa.build_categorize_model(["Washed"], vocabulary)
        question = model.model_fields["map_0"].description
        assert '"Washed"' in question and NONE_OF_THE_ABOVE in question
        assert model.__name__ == "JevProcessCategorize"
        assert "Categorize" in (model.__doc__ or "")

    def test_method_without_candidates_produces_empty_model(self, vocabulary):
        model, meta = pa.build_categorize_model([NO_CANDIDATE_METHOD], vocabulary)
        assert model.model_fields == {}
        assert meta == {"field_methods": {}, "field_candidates": {}}


# ---------------------------------------------------------------------------
# extract_choice_answers
# ---------------------------------------------------------------------------


class TestExtractChoiceAnswers:
    def test_adapter_shape_and_provider_confidence(self):
        output = SimpleNamespace(map_0="Washed", map_1=NONE_OF_THE_ABOVE)
        meta = {"field_methods": {"map_0": "Fully washed", "map_1": "moonbeam"}}
        provider_details = {"confidence": {"map_0": 0.72, "map_1": 0.31}}
        answers, confidences = pa.extract_choice_answers(output, meta, provider_details)
        assert answers["map_0"] == {"type": "choice", "choice": "Washed", "confidence": 0.72}
        assert answers["map_1"] == {"type": "choice", "choice": NONE_OF_THE_ABOVE, "confidence": 0.31}
        assert confidences == {"map_0": 0.72, "map_1": 0.31}

    @pytest.mark.parametrize("provider_details", [None, {"confidence": {}}, {"confidence": {"map_0": "high"}}])
    def test_missing_or_unusable_provider_confidence_defaults_to_one(self, provider_details):
        output = SimpleNamespace(map_0="Washed")
        meta = {"field_methods": {"map_0": "Fully washed"}}
        answers, confidences = pa.extract_choice_answers(output, meta, provider_details)
        assert answers["map_0"]["confidence"] == 1.0
        assert confidences == {"map_0": 1.0}

    def test_fields_absent_on_output_are_skipped(self):
        output = SimpleNamespace(map_0="Washed")
        meta = {"field_methods": {"map_0": "Fully washed", "map_1": "moonbeam"}}
        answers, confidences = pa.extract_choice_answers(output, meta)
        assert set(answers) == {"map_0"}
        assert set(confidences) == {"map_0"}


# ---------------------------------------------------------------------------
# build_merge_model / build_conflict_model
# ---------------------------------------------------------------------------


class TestBuildMergeModel:
    def test_field_names_and_meta(self):
        pairs = [("Natural", "Natural Process"), ("Washed", "Honey")]
        model, meta = pa.build_merge_model(pairs)
        assert list(model.model_fields) == ["pair_0", "pair_1"]
        assert meta["field_pairs"] == {"pair_0": ["Natural", "Natural Process"], "pair_1": ["Washed", "Honey"]}

    def test_description_names_the_pair(self):
        model, _meta = pa.build_merge_model([("EA Decaf", "Ethyl Acetate Decaffeinated")])
        description = model.model_fields["pair_0"].description
        assert "EA Decaf" in description
        assert "Ethyl Acetate Decaffeinated" in description
        assert "same processing method" in description

    def test_field_annotation_is_merge_decision(self):
        model, _meta = pa.build_merge_model([("Washed", "Honey")])
        assert model.model_fields["pair_0"].annotation is pa.MergeDecision


class TestBuildConflictModel:
    def test_field_names_meta_and_start_index(self):
        groups = {"Natural": ["Natural", "Natural Process"], "Washed": ["Washed", "Fully Washed"]}
        model, meta = pa.build_conflict_model(groups)
        assert list(model.model_fields) == ["group_0", "group_1"]
        assert meta["field_groups"] == {
            "group_0": ["Natural", ["Natural", "Natural Process"]],
            "group_1": ["Washed", ["Washed", "Fully Washed"]],
        }
        # run_conflicts passes a global offset so field ids stay unique per batch.
        offset_model, offset_meta = pa.build_conflict_model({"Honey": ["Honey"]}, start_index=15)
        assert list(offset_model.model_fields) == ["group_15"]
        assert offset_meta["field_groups"]["group_15"] == ["Honey", ["Honey"]]

    def test_description_includes_common_name_and_originals(self):
        model, _meta = pa.build_conflict_model({"Anaerobic Natural": ["Natural", "Anaerobic Natural"]})
        description = model.model_fields["group_0"].description
        assert "Anaerobic Natural" in description
        assert '"Natural"' in description
        assert "fundamentally" in description

    def test_originals_clipped_to_first_15_with_remainder(self):
        originals = [f"Original {index}" for index in range(20)]
        model, meta = pa.build_conflict_model({"Big Group": originals})
        description = model.model_fields["group_0"].description
        assert "(and 5 more)" in description
        assert "Original 14" in description
        assert "Original 15" not in description
        assert meta["field_groups"]["group_0"][1] == originals

    def test_field_annotation_is_conflict_decision(self):
        model, _meta = pa.build_conflict_model({"Natural": ["Natural"]})
        assert model.model_fields["group_0"].annotation is pa.ConflictDecision


# ---------------------------------------------------------------------------
# run_categorize: offline deterministic / no-candidate paths
# ---------------------------------------------------------------------------


class TestRunCategorizeOffline:
    async def test_all_methods_resolved_deterministically_skips_jev(self, vocabulary, lookup):
        result = await pa.run_categorize(["Washed", "Natural"], vocabulary, lookup, use_llm=False)
        assert result["sources"] == {"Washed": "deterministic", "Natural": "deterministic"}
        assert [mapping["common_name"] for mapping in result["mappings"]] == ["Washed", "Natural"]
        assert result["batches"] == []
        assert result["usage_totals"] == {"input_tokens": 0, "output_tokens": 0, "requests": 0}
        assert result["model_name"] is None
        assert result["review"] == []

    async def test_lookup_hit_keeps_input_name_and_recorded_canonical(self, vocabulary, lookup):
        result = await pa.run_categorize(["ea decaf"], vocabulary, lookup, use_llm=False)
        mapping = result["mappings"][0]
        assert mapping["original_name"] == "ea decaf"
        assert mapping["common_name"] == "Ethyl Acetate Decaf"
        assert result["sources"]["ea decaf"] == "deterministic"

    async def test_no_candidate_and_llm_disabled_falls_back_without_network(self, vocabulary):
        result = await pa.run_categorize([NO_CANDIDATE_METHOD], vocabulary, {}, use_llm=False)
        mapping = result["mappings"][0]
        assert mapping == {"original_name": NO_CANDIDATE_METHOD, "common_name": NO_CANDIDATE_METHOD, "confidence": 0.5}
        assert result["sources"][NO_CANDIDATE_METHOD] == "fallback"
        assert result["candidates"] == {}
        # The batch is recorded (no fields -> no Jev call, no error).
        assert len(result["batches"]) == 1
        assert result["batches"][0]["error"] is None
        assert result["batches"][0]["model_name"] is None
        assert result["needs_composition"] == [NO_CANDIDATE_METHOD]

    async def test_empty_inputs_return_identity_without_a_call(self, vocabulary):
        empty = await pa.run_categorize([], vocabulary, {}, use_llm=False)
        assert empty["mappings"] == [] and empty["sources"] == {} and empty["batches"] == []
        blank = await pa.run_categorize(["  "], vocabulary, {}, use_llm=False)
        assert blank["mappings"][0]["common_name"] == ""
        assert blank["sources"][""] == "fallback"
        assert blank["batches"] == []
