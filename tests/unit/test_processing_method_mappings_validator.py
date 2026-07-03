"""Unit tests for the processing method mappings validator.

These tests verify that ``ProcessCategorizer.validate_mappings`` correctly
enforces the invariant: each ``original_name`` appears at most once in
``processing_methods_mappings.json``, with a single consistent ``common_name``.

Note: multiple *original* names legitimately map to the same ``common_name``
(that's the whole point of the merge step). The validator only checks for
duplicate ``original_name`` keys.
"""

import json
from pathlib import Path

import pytest

from kissaten.ai.processing_method_categorizer import ProcessCategorizer

MAPPINGS_FILE = (
    Path(__file__).parent.parent.parent
    / "src"
    / "kissaten"
    / "database"
    / "processing_methods_mappings.json"
)


def _base_mapping(original_name: str, common_name: str, **overrides) -> dict:
    """Build a minimal valid mapping entry, optionally overriding fields."""
    entry = {
        "original_name": original_name,
        "common_name": common_name,
        "confidence": 1.0,
    }
    entry.update(overrides)
    return entry


class TestValidateMappings:
    """Tests for ``ProcessCategorizer.validate_mappings_static``."""

    def test_clean_data_has_no_issues(self):
        """A list of distinct original_names returns no issues, even if many
        share the same common_name (the whole point of the merge step)."""
        data = [
            _base_mapping("Washed", "Washed"),
            _base_mapping("Fully Washed", "Washed"),
            _base_mapping("Wet Process", "Washed"),
            _base_mapping("Natural", "Natural"),
            _base_mapping("Dry Process", "Natural"),
        ]
        assert ProcessCategorizer.validate_mappings_static(data) == []

    def test_redundant_duplicate_is_detected(self):
        """Same original_name + same common_name => one redundant issue."""
        data = [
            _base_mapping("Washed", "Washed"),
            _base_mapping("Washed", "Washed"),
        ]
        issues = ProcessCategorizer.validate_mappings_static(data)
        assert len(issues) == 1
        issue = issues[0]
        # original_name is the case-folded lookup key.
        assert issue["original_name"] == "washed"
        # original_names preserves the actual case variants.
        assert issue["original_names"] == ["Washed", "Washed"]
        assert issue["occurrences"] == 2
        assert issue["common_names"] == ["Washed", "Washed"]
        assert issue["is_conflict"] is False
        assert issue["indexes"] == [0, 1]

    def test_conflicting_duplicate_is_detected(self):
        """Same original_name + different common_name => a conflict."""
        data = [
            _base_mapping("Washed", "Washed"),
            _base_mapping("Washed", "Washed Process"),
        ]
        issues = ProcessCategorizer.validate_mappings_static(data)
        assert len(issues) == 1
        issue = issues[0]
        assert issue["original_name"] == "washed"
        assert issue["occurrences"] == 2
        assert issue["common_names"] == ["Washed", "Washed Process"]
        assert issue["is_conflict"] is True
        assert issue["indexes"] == [0, 1]

    def test_three_way_conflict_is_detected(self):
        """Three duplicate entries with three different common names => a conflict."""
        data = [
            _base_mapping("X", "A"),
            _base_mapping("X", "B"),
            _base_mapping("X", "C"),
        ]
        issues = ProcessCategorizer.validate_mappings_static(data)
        assert len(issues) == 1
        assert issues[0]["original_name"] == "x"
        assert issues[0]["occurrences"] == 3
        assert issues[0]["is_conflict"] is True
        assert issues[0]["indexes"] == [0, 1, 2]

    def test_two_of_three_redundant_is_a_conflict(self):
        """If even one duplicate disagrees, the whole group is a conflict."""
        data = [
            _base_mapping("X", "A"),
            _base_mapping("X", "A"),
            _base_mapping("X", "B"),
        ]
        issues = ProcessCategorizer.validate_mappings_static(data)
        assert len(issues) == 1
        assert issues[0]["is_conflict"] is True

    def test_confidence_does_not_affect_conflict(self):
        """Two duplicates with the same common_name but different confidence
        are still a redundant (non-conflict) issue, not a conflict."""
        data = [
            _base_mapping("Washed", "Washed", confidence=1.0),
            _base_mapping("Washed", "Washed", confidence=0.7),
        ]
        issues = ProcessCategorizer.validate_mappings_static(data)
        assert len(issues) == 1
        assert issues[0]["is_conflict"] is False

    def test_case_insensitive_duplicate_is_detected(self):
        """Two entries that differ only in case are duplicates (DB matches case-insensitively)."""
        data = [
            _base_mapping("WASHED", "Washed"),
            _base_mapping("Washed", "Washed Process"),
        ]
        issues = ProcessCategorizer.validate_mappings_static(data)
        assert len(issues) == 1
        issue = issues[0]
        assert issue["original_name"] == "washed"
        assert issue["original_names"] == ["WASHED", "Washed"]
        assert issue["is_conflict"] is True

    def test_case_insensitive_redundant(self):
        """Two case variants with the same common_name => redundant, not conflict."""
        data = [
            _base_mapping("Washed", "Washed"),
            _base_mapping("WASHED", "Washed"),
        ]
        issues = ProcessCategorizer.validate_mappings_static(data)
        assert len(issues) == 1
        assert issues[0]["original_name"] == "washed"
        assert issues[0]["original_names"] == ["Washed", "WASHED"]
        assert issues[0]["is_conflict"] is False

    def test_multiple_independent_duplicates(self):
        """Validator returns one issue per distinct duplicate lookup key."""
        data = [
            _base_mapping("Washed", "Washed"),
            _base_mapping("Natural", "Natural"),
            _base_mapping("Washed", "Washed"),
            _base_mapping("Natural", "Dry Process"),
        ]
        issues = ProcessCategorizer.validate_mappings_static(data)
        assert len(issues) == 2
        by_name = {issue["original_name"]: issue for issue in issues}
        assert by_name["washed"]["is_conflict"] is False
        assert by_name["natural"]["is_conflict"] is True

    def test_empty_data_has_no_issues(self):
        assert ProcessCategorizer.validate_mappings_static([]) == []


class TestLoaderIntegration:
    """Verify the loader surfaces duplicates instead of silently overwriting."""

    def test_loader_raises_on_duplicates(self, tmp_path):
        mappings_file = tmp_path / "mappings.json"
        mappings_file.write_text(
            json.dumps(
                [
                    _base_mapping("Washed", "Washed"),
                    _base_mapping("Washed", "Washed Process"),
                ]
            )
        )

        cat = ProcessCategorizer(database_path=tmp_path / "unused.duckdb", mappings_file=mappings_file)
        with pytest.raises(ValueError, match="duplicate original_name"):
            cat.load_mappings()

    def test_loader_succeeds_on_clean_file(self, tmp_path):
        mappings_file = tmp_path / "mappings.json"
        mappings_file.write_text(
            json.dumps(
                [
                    _base_mapping("Washed", "Washed"),
                    _base_mapping("Natural", "Natural"),
                ]
            )
        )

        cat = ProcessCategorizer(database_path=tmp_path / "unused.duckdb", mappings_file=mappings_file)
        loaded = cat.load_mappings()
        assert set(loaded) == {"Washed", "Natural"}


class TestMappingsFile:
    """End-to-end check against the real mappings file shipped with the repo."""

    # The shipped mappings file has known case-insensitive duplicate conflicts
    # in the processing data (introduced before the validator was made
    # case-insensitive). They are tracked here and must be cleaned up by
    # hand -- the validator is just the discovery tool. Once the file is
    # clean, remove the xfail markers below.
    #
    # Run ``kissaten validate-mappings`` to see the current list.

    @pytest.mark.xfail(
        reason="Shipped file has known case-insensitive conflicting duplicates -- see validate-mappings output",
        strict=True,
    )
    def test_shipped_mappings_file_has_no_conflicting_case_insensitive_dupes(self):
        """The committed mappings file must not have CONFLICTING case-insensitive
        duplicate ``original_name`` entries (different common names that would
        collide at lookup time).

        Redundant case-insensitive duplicates (same common name under different
        case) are also detected by the validator but are not asserted here --
        they are pre-existing data hygiene issues tracked separately and do
        not break the DB.
        """
        if not MAPPINGS_FILE.exists():
            pytest.skip(f"Mappings file not found: {MAPPINGS_FILE}")
        with open(MAPPINGS_FILE) as f:
            data = json.load(f)
        issues = ProcessCategorizer.validate_mappings_static(data)
        conflicts = [i for i in issues if i["is_conflict"]]
        assert conflicts == [], (
            f"Found {len(conflicts)} CONFLICTING case-insensitive duplicate group(s) "
            f"in {MAPPINGS_FILE}. These collide at lookup time and produce "
            f"non-deterministic common names. Examples: {conflicts[:3]}"
        )

    def test_shipped_mappings_file_duplicate_count_documented(self):
        """Document the current state of case-insensitive duplicates in the
        shipped file. Informational."""
        if not MAPPINGS_FILE.exists():
            pytest.skip(f"Mappings file not found: {MAPPINGS_FILE}")
        with open(MAPPINGS_FILE) as f:
            data = json.load(f)
        issues = ProcessCategorizer.validate_mappings_static(data)
        conflicts = [i for i in issues if i["is_conflict"]]
        redundant = [i for i in issues if not i["is_conflict"]]
        print(
            f"\n[MAPPINGS FILE STATE] {len(issues)} case-insensitive duplicate group(s): "
            f"{len(conflicts)} CONFLICTING, {len(redundant)} redundant"
        )
        for issue in issues[:5]:
            label = "CONFLICT" if issue["is_conflict"] else "redundant"
            print(f"  [{label}] {issue['original_name']!r}: {issue['original_names']}")
