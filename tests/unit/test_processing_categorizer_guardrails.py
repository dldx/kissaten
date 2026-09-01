"""Guardrail unit tests for the processing-method categorizer.

These verify the provenance-protected conflict resolution and the
case-insensitive + protected-aware batch categorization, mirroring the varietal
categorizer's guardrails. The goal is that a rejected merge (AI disagreement)
can never flag a pre-existing reviewed ``common_name`` for manual review, and
that case-variant duplicates (such as "EA Decaf" + "ea decaf") are no longer
manufactured by the batch phase.

The real LLM is never invoked: ``conflict_agent`` / ``agent`` are replaced with
fakes that return canned ``ConflictResolution`` / ``ProcessingMethodBatch``
outputs.
"""

from types import SimpleNamespace

from kissaten.ai.processing_method_categorizer import (
    ConflictResolution,
    ProcessCategorizer,
    ProcessingMethodBatch,
    ProcessingMethodMapping,
)


def _mapping(original_name: str, common_name: str, **overrides) -> ProcessingMethodMapping:
    """Build a minimal mapping, optionally overriding fields."""
    entry = {
        "original_name": original_name,
        "common_name": common_name,
        "confidence": 1.0,
    }
    entry.update(overrides)
    return ProcessingMethodMapping(**entry)


def _rejection(original_names: list[str], common_name: str, reason: str = "distinct process") -> ConflictResolution:
    """Build a ``should_merge=False`` resolution."""
    return ConflictResolution(
        original_names=original_names,
        common_name=common_name,
        should_merge=False,
        reason=reason,
    )


class _FakeAgent:
    """Stand-in for a pydantic-ai Agent that returns canned outputs in order."""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = 0

    async def run(self, prompt):
        self.calls += 1
        return SimpleNamespace(output=self.outputs.pop(0))


def _make_categorizer(tmp_path) -> ProcessCategorizer:
    return ProcessCategorizer(
        database_path=tmp_path / "unused.duckdb",
        mappings_file=tmp_path / "processing_methods_mappings.json",
    )


def _by_name(mappings: list[ProcessingMethodMapping]) -> dict[str, ProcessingMethodMapping]:
    return {m.original_name: m for m in mappings}


class TestResolveConflicts:
    """Provenance-protected conflict resolution."""

    async def test_resolve_conflicts_respects_protected_common_names(self, tmp_path, caplog):
        """An AI reject of a protected common_name is NOT added to the resolved set.

        A reject under a protected (pre-existing, reviewed) common name is
        suppressed and logged; a reject under an unprotected common name is
        still flagged for manual review.
        """
        cat = _make_categorizer(tmp_path)
        fake = _FakeAgent(
            [
                _rejection(["Fully Washed", "Anaerobic Washed"], "Washed"),
                _rejection(["Honey Process", "Pulped Natural"], "Honey"),
            ]
        )
        cat.conflict_agent = fake

        with caplog.at_level("INFO", logger="kissaten.ai.processing_method_categorizer"):
            resolved = await cat.resolve_conflicts(
                {
                    "Washed": ["Fully Washed", "Anaerobic Washed"],
                    "Honey": ["Honey Process", "Pulped Natural"],
                },
                protected_common_names={"washed"},
            )

        # Protected reject suppressed; non-protected reject still flagged.
        assert resolved == {"Honey": ["Honey Process", "Pulped Natural"]}
        assert fake.calls == 2
        assert any("Protected common name 'Washed' kept" in r.getMessage() for r in caplog.records)

    async def test_resolve_conflicts_unprotected_still_flagged(self, tmp_path):
        """An AI reject of a non-protected common name IS included in resolved."""
        cat = _make_categorizer(tmp_path)
        fake = _FakeAgent([_rejection(["Natural", "Coconut Natural"], "Natural")])
        cat.conflict_agent = fake

        resolved = await cat.resolve_conflicts(
            {"Natural": ["Natural", "Coconut Natural"]},
            protected_common_names={"washed"},
        )

        assert resolved == {"Natural": ["Natural", "Coconut Natural"]}
        assert fake.calls == 1

    async def test_no_protection_preserves_original_behaviour(self, tmp_path):
        """With ``protected_common_names`` unset every reject is still returned."""
        cat = _make_categorizer(tmp_path)
        fake = _FakeAgent([_rejection(["Fully Washed", "Anaerobic Washed"], "Washed")])
        cat.conflict_agent = fake

        resolved = await cat.resolve_conflicts({"Washed": ["Fully Washed", "Anaerobic Washed"]})

        assert resolved == {"Washed": ["Fully Washed", "Anaerobic Washed"]}
        assert fake.calls == 1


class TestBatchCategorization:
    """Case-insensitive, protected-aware batch categorization."""

    async def test_batch_skips_case_variant_input(self, tmp_path):
        """Input names that already have a (reviewed) mapping in ANY case are not re-sent."""
        reviewed = _mapping("EA Decaf", "Ethyl Acetate Decaf")
        cat = _make_categorizer(tmp_path)
        fake = _FakeAgent([ProcessingMethodBatch(mappings=[_mapping("Fully Washed", "Washed")])])
        cat.agent = fake

        result = await cat.categorize_methods_batched(
            ["ea decaf", "Fully Washed", "EA Decaf"],
            batch_size=20,
            existing_mappings={"EA Decaf": reviewed},
        )

        # Only the new method reached the AI; the case-variants were skipped.
        assert fake.calls == 1
        by_name = _by_name(result)
        assert set(by_name) == {"EA Decaf", "Fully Washed"}
        # The reviewed object is kept, and no case-variant duplicate is added.
        assert by_name["EA Decaf"] is reviewed
        assert by_name["EA Decaf"].common_name == "Ethyl Acetate Decaf"
        assert by_name["Fully Washed"].common_name == "Washed"
        assert sorted(m.original_name.lower() for m in result) == ["ea decaf", "fully washed"]

    async def test_batch_collision_guard_keeps_reviewed(self, tmp_path):
        """An LLM echo of a reviewed name is dropped; the reviewed mapping wins."""
        reviewed = _mapping("EA Decaf", "Ethyl Acetate Decaf")
        cat = _make_categorizer(tmp_path)
        fake = _FakeAgent(
            [
                ProcessingMethodBatch(
                    mappings=[
                        _mapping("EA Decaf", "Ethyl Acetate Decaf"),  # LLM echo -> collides with reviewed
                        _mapping("Fully Washed", "Washed"),
                    ]
                )
            ]
        )
        cat.agent = fake

        result = await cat.categorize_methods_batched(
            ["EA Decaf", "Fully Washed"],
            batch_size=20,
            existing_mappings={"EA Decaf": reviewed},
        )

        by_name = _by_name(result)
        assert set(by_name) == {"EA Decaf", "Fully Washed"}
        # The reviewed object is the one kept, byte-identical.
        assert by_name["EA Decaf"] is reviewed
        assert by_name["EA Decaf"].common_name == "Ethyl Acetate Decaf"
        assert by_name["Fully Washed"].common_name == "Washed"
        assert not any(m.original_name == "ea decaf" for m in result)
