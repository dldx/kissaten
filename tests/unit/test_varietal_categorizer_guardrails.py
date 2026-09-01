"""Guardrail unit tests for the varietal categorizer.

These verify the provenance-protected conflict resolution and the
case-insensitive + protected-aware batch categorization. The goal is that a
rejected merge (AI disagreement) can only ever revert NEW mappings, never the
pre-existing human-reviewed ones, and that case-variant duplicates (such as
"Mixed" + "mixed") are no longer manufactured by the batch phase.

The real LLM is never invoked: ``conflict_agent`` / ``agent`` are replaced with
fakes that return canned ``ConflictResolution`` / ``VarietalBatch`` outputs.
"""

import json
from types import SimpleNamespace

from kissaten.ai.varietal_categorizer import ConflictResolution, VarietalBatch, VarietalCategorizer, VarietalMapping


def _mapping(original_name: str, canonical_names: list[str], **overrides) -> VarietalMapping:
    """Build a minimal mapping, optionally overriding fields."""
    entry = {
        "original_name": original_name,
        "canonical_names": canonical_names,
        "confidence": 1.0,
        "is_compound": False,
        "separator": None,
    }
    entry.update(overrides)
    return VarietalMapping(**entry)


def _rejection(
    original_names: list[str], canonical_name: str, revert_original_names: list[str], reason: str = "distinct varietal"
) -> ConflictResolution:
    """Build a ``should_merge=False`` resolution with the given revert list."""
    return ConflictResolution(
        original_names=original_names,
        canonical_name=canonical_name,
        should_merge=False,
        reason=reason,
        revert_original_names=revert_original_names,
    )


def _approval(original_names: list[str], canonical_name: str, reason: str = "synonyms") -> ConflictResolution:
    """Build a ``should_merge=True`` resolution."""
    return ConflictResolution(
        original_names=original_names,
        canonical_name=canonical_name,
        should_merge=True,
        reason=reason,
        revert_original_names=[],
    )


class _FakeAgent:
    """Stand-in for a pydantic-ai Agent that returns canned outputs in order."""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = 0

    async def run(self, prompt):
        self.calls += 1
        return SimpleNamespace(output=self.outputs.pop(0))


class _RaisingAgent:
    """Agent that raises if invoked — proves an AI call was skipped entirely."""

    def __init__(self):
        self.calls = 0

    async def run(self, prompt):
        self.calls += 1
        raise AssertionError("agent must not be called for a fully protected group")


def _make_categorizer(tmp_path) -> VarietalCategorizer:
    return VarietalCategorizer(
        database_path=tmp_path / "unused.duckdb",
        mappings_file=tmp_path / "varietal_mappings.json",
    )


def _by_name(mappings: list[VarietalMapping]) -> dict[str, VarietalMapping]:
    return {m.original_name: m for m in mappings}


class TestResolveConflicts:
    """Provenance-protected conflict resolution."""

    async def test_rejected_group_reverts_only_named_new_member(self, tmp_path):
        """A rejected merge reverts ONLY the AI-named, non-protected member."""
        mappings = [
            _mapping("SL-28", ["SL28"]),  # protected, human-reviewed
            _mapping("SL 28", ["SL28"]),  # protected, human-reviewed
            _mapping("SL28-32", ["SL28"], confidence=0.8),  # new, polluted the group
        ]
        cat = _make_categorizer(tmp_path)
        fake = _FakeAgent([_rejection(["SL-28", "SL 28", "SL28-32"], "SL28", ["SL28-32"])])
        cat.conflict_agent = fake

        result = await cat.resolve_conflicts(
            {"SL28": ["SL-28", "SL 28", "SL28-32"]},
            mappings,
            protected_names={"sl-28", "sl 28"},
        )

        by_name = _by_name(result)
        assert by_name["SL-28"].canonical_names == ["SL28"]
        assert by_name["SL-28"].confidence == 1.0
        assert by_name["SL-28"].is_compound is False
        assert by_name["SL 28"].canonical_names == ["SL28"]
        assert by_name["SL 28"].confidence == 1.0
        assert by_name["SL28-32"].canonical_names == ["SL28-32"]
        assert by_name["SL28-32"].confidence == 0.5
        assert by_name["SL28-32"].is_compound is False
        assert fake.calls == 1

    async def test_rejected_group_leaves_disputed_protected_untouched_and_writes_report(self, tmp_path):
        """The Geisha Inca case: an AI dispute of a protected mapping is logged, never applied."""
        report_path = tmp_path / "review_report.json"
        mappings = [
            _mapping("Geisha Inca", ["SL9"], confidence=1.0),  # protected, human-reviewed
            _mapping("SL-9", ["SL9"], confidence=0.8),  # new
        ]
        cat = _make_categorizer(tmp_path)
        fake = _FakeAgent([_rejection(["Geisha Inca", "SL-9"], "SL9", ["Geisha Inca"])])
        cat.conflict_agent = fake

        result = await cat.resolve_conflicts(
            {"SL9": ["Geisha Inca", "SL-9"]},
            mappings,
            protected_names={"geisha inca"},
            report_path=report_path,
        )

        by_name = _by_name(result)
        # Protected mapping untouched, despite being named for revert.
        assert by_name["Geisha Inca"].canonical_names == ["SL9"]
        assert by_name["Geisha Inca"].confidence == 1.0
        # New member NOT named -> left alone (its stem equals the canonical stem).
        assert by_name["SL-9"].canonical_names == ["SL9"]
        assert by_name["SL-9"].confidence == 0.8

        report = json.loads(report_path.read_text())
        assert {
            "canonical_name": "SL9",
            "original_name": "Geisha Inca",
            "reason": "distinct varietal",
            "status": "disputed",
        } in report

    async def test_fully_protected_group_skips_ai(self, tmp_path):
        """A group whose members are ALL protected never reaches the AI."""
        mappings = [
            _mapping("SL-28", ["SL28"]),
            _mapping("SL 28", ["SL28"]),
        ]
        cat = _make_categorizer(tmp_path)
        fake = _RaisingAgent()
        cat.conflict_agent = fake

        result = await cat.resolve_conflicts(
            {"SL28": ["SL-28", "SL 28"]},
            mappings,
            protected_names={"sl-28", "sl 28"},
        )

        assert fake.calls == 0
        by_name = _by_name(result)
        assert by_name["SL-28"].canonical_names == ["SL28"]
        assert by_name["SL 28"].canonical_names == ["SL28"]
        # No dispute -> no report written.
        assert not (tmp_path / "varietal_review_report.json").exists()

    async def test_fallback_stem_rule_reverts_only_revertible(self, tmp_path):
        """Empty revert list falls back to a deterministic stem rule over revertible members."""
        mappings = [
            _mapping("SL-28", ["SL28"]),  # protected
            _mapping("SL28-32", ["SL28"], confidence=0.8),  # new
        ]
        cat = _make_categorizer(tmp_path)
        fake = _FakeAgent([_rejection(["SL-28", "SL28-32"], "SL28", [])])
        cat.conflict_agent = fake

        result = await cat.resolve_conflicts(
            {"SL28": ["SL-28", "SL28-32"]},
            mappings,
            protected_names={"sl-28"},
        )

        by_name = _by_name(result)
        assert by_name["SL-28"].canonical_names == ["SL28"]
        assert by_name["SL-28"].confidence == 1.0
        assert by_name["SL28-32"].canonical_names == ["SL28-32"]
        assert by_name["SL28-32"].confidence == 0.5

    async def test_approved_group_nothing_reverted(self, tmp_path):
        """An approved merge leaves every mapping untouched."""
        mappings = [
            _mapping("SL-28", ["SL28"]),
            _mapping("SL28-32", ["SL28"], confidence=0.8),
        ]
        cat = _make_categorizer(tmp_path)
        fake = _FakeAgent([_approval(["SL-28", "SL28-32"], "SL28")])
        cat.conflict_agent = fake

        result = await cat.resolve_conflicts(
            {"SL28": ["SL-28", "SL28-32"]},
            mappings,
            protected_names={"sl-28"},
        )

        by_name = _by_name(result)
        assert by_name["SL-28"].canonical_names == ["SL28"]
        assert by_name["SL-28"].confidence == 1.0
        assert by_name["SL28-32"].canonical_names == ["SL28"]
        assert by_name["SL28-32"].confidence == 0.8


class TestBatchCategorization:
    """Case-insensitive, protected-aware batch categorization."""

    async def test_batch_skips_case_variant_input(self, tmp_path):
        """Input names that already have a (reviewed) mapping in ANY case are not re-sent."""
        reviewed = _mapping("Mixed", ["Field Blend"])
        existing_mappings = {"Mixed": reviewed}
        cat = _make_categorizer(tmp_path)
        fake = _FakeAgent([VarietalBatch(mappings=[_mapping("SL28", ["SL28"])])])
        cat.agent = fake

        result = await cat.categorize_varietals_batched(
            ["mixed", "SL28", "Mixed"],
            batch_size=20,
            existing_mappings=existing_mappings,
        )

        assert fake.calls == 1
        assert set(_by_name(result)) == {"Mixed", "SL28"}
        # No case-variant duplicate of the reviewed entry is manufactured.
        assert sorted(m.original_name.lower() for m in result) == ["mixed", "sl28"]
        assert not any(m.original_name == "mixed" for m in result)

    async def test_batch_collision_guard_keeps_reviewed(self, tmp_path):
        """An LLM echo of a reviewed name is dropped; the reviewed mapping wins."""
        reviewed = _mapping("SL28", ["SL28"])
        cat = _make_categorizer(tmp_path)
        fake = _FakeAgent(
            [
                VarietalBatch(
                    mappings=[
                        _mapping("SL28", ["SL28"]),  # LLM echo -> collides with reviewed
                        _mapping("Heirloom", ["Heirloom"]),
                    ]
                )
            ]
        )
        cat.agent = fake

        result = await cat.categorize_varietals_batched(
            ["SL28", "Heirloom"],
            batch_size=20,
            existing_mappings={"SL28": reviewed},
        )

        by_name = _by_name(result)
        assert set(by_name) == {"SL28", "Heirloom"}
        # The reviewed object is the one kept, byte-identical.
        assert by_name["SL28"] is reviewed
        assert by_name["SL28"].canonical_names == ["SL28"]
        assert by_name["Heirloom"].canonical_names == ["Heirloom"]

    async def test_suspicious_compound_demoted_to_single(self, tmp_path):
        """A compound without separator punctuation is demoted to a single mapping."""
        cat = _make_categorizer(tmp_path)
        fake = _FakeAgent(
            [
                VarietalBatch(
                    mappings=[
                        _mapping(
                            "Pache San Ramon",
                            ["Pache", "San Ramon"],
                            confidence=0.8,
                            is_compound=True,
                            separator=None,
                        )
                    ]
                )
            ]
        )
        cat.agent = fake

        result = await cat.categorize_varietals_batched(["Pache San Ramon"], batch_size=20)

        assert len(result) == 1
        mapping = result[0]
        assert mapping.original_name == "Pache San Ramon"
        assert mapping.canonical_names == ["Pache San Ramon"]
        assert mapping.is_compound is False
        assert mapping.separator is None
        assert mapping.confidence == 0.8

    async def test_word_separator_compound_not_demoted(self, tmp_path):
        """A compound with a standalone word separator (" and ") stays split."""
        cat = _make_categorizer(tmp_path)
        fake = _FakeAgent(
            [
                VarietalBatch(
                    mappings=[
                        _mapping(
                            "74110 and 74112",
                            ["74110", "74112"],
                            confidence=0.8,
                            is_compound=True,
                            separator=None,
                        )
                    ]
                )
            ]
        )
        cat.agent = fake

        result = await cat.categorize_varietals_batched(["74110 and 74112"], batch_size=20)

        assert len(result) == 1
        mapping = result[0]
        assert mapping.original_name == "74110 and 74112"
        assert mapping.canonical_names == ["74110", "74112"]
        assert mapping.is_compound is True
        assert mapping.separator is None
        assert mapping.confidence == 0.8


class TestSystemPrompts:
    """Reference/alternates context and the revert protocol appear in the prompts."""

    def test_main_agent_prompt(self, tmp_path):
        cat = _make_categorizer(tmp_path)
        known, alternates = cat._reference_context()
        prompt = cat._categorizer_system_prompt(known, alternates)

        assert "REFERENCE VARIETALS" in prompt
        assert '"Cattura" -> "Caturra"' in prompt
        assert '"Geisha" -> "Gesha"' not in prompt
        assert "Geisha (Panama)" in prompt
        # Alternates block is optional: empty for the shipped reference file, so it is omitted.
        assert "COMMON ALTERNATE NAMES" not in prompt
        assert "COMMON ALTERNATE NAMES" in cat._categorizer_system_prompt(known, "Java, Kona")

    def test_conflict_agent_prompt(self, tmp_path):
        cat = _make_categorizer(tmp_path)
        known, alternates = cat._reference_context()
        prompt = cat._conflict_system_prompt(known, alternates)

        assert "REFERENCE VARIETALS" in prompt
        assert "COMMON ALTERNATE NAMES" in prompt
        assert "revert_original_names" in prompt
        assert "Be conservative" in prompt
        assert "Geisha Inca" in prompt

    def test_merge_agent_prompt(self, tmp_path):
        cat = _make_categorizer(tmp_path)
        known, alternates = cat._reference_context()
        prompt = cat._merge_system_prompt(known, alternates)

        assert "REFERENCE VARIETALS" in prompt
        assert "COMMON ALTERNATE NAMES" in prompt

    def test_reference_context_has_no_duplicate_known_names(self, tmp_path):
        cat = _make_categorizer(tmp_path)
        known, _ = cat._reference_context()
        items = [x.strip() for x in known.split(",") if x.strip()]
        # No dupes despite the lookup dict holding both name and lowercase keys.
        assert len(items) == len(set(items))
