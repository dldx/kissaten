"""Unit tests for the varietal mappings validator.

These tests verify that ``VarietalCategorizer.validate_mappings`` correctly
enforces the invariant: each ``original_name`` appears at most once in
``varietal_mappings.json``, with a single consistent ``canonical_names`` list.
"""

import json
from pathlib import Path

import pytest

from kissaten.ai.varietal_categorizer import VarietalCategorizer

MAPPINGS_FILE = Path(__file__).parent.parent.parent / "src" / "kissaten" / "database" / "varietal_mappings.json"


def _base_mapping(original_name: str, canonical_names: list[str], **overrides) -> dict:
    """Build a minimal valid mapping entry, optionally overriding fields."""
    entry = {
        "original_name": original_name,
        "canonical_names": canonical_names,
        "confidence": 1.0,
        "is_compound": False,
        "separator": None,
    }
    entry.update(overrides)
    return entry


class TestValidateMappings:
    """Tests for ``VarietalCategorizer.validate_mappings_static``."""

    def test_clean_data_has_no_issues(self):
        """A list of distinct original_names returns no issues."""
        data = [
            _base_mapping("Typica", ["Typica"]),
            _base_mapping("Bourbon", ["Bourbon"]),
            _base_mapping("Caturra, Typica", ["Caturra", "Typica"], is_compound=True, separator=","),
        ]
        assert VarietalCategorizer.validate_mappings_static(data) == []

    def test_redundant_duplicate_is_detected(self):
        """Same original_name + same canonical_names => one redundant issue."""
        data = [
            _base_mapping("Typica", ["Typica"]),
            _base_mapping("Typica", ["Typica"]),
        ]
        issues = VarietalCategorizer.validate_mappings_static(data)
        assert len(issues) == 1
        issue = issues[0]
        # original_name is the case-folded lookup key (DB uses LOWER()).
        assert issue["original_name"] == "typica"
        # original_names preserves the actual case variants from the file.
        assert issue["original_names"] == ["Typica", "Typica"]
        assert issue["occurrences"] == 2
        assert issue["canonical_names"] == [["Typica"], ["Typica"]]
        assert issue["is_conflict"] is False
        assert issue["indexes"] == [0, 1]

    def test_conflicting_duplicate_is_detected(self):
        """Same original_name + different canonical_names => a conflict."""
        data = [
            _base_mapping("Bourbon", ["Bourbon"]),
            _base_mapping("Bourbon", ["Bourbon Ají"]),
        ]
        issues = VarietalCategorizer.validate_mappings_static(data)
        assert len(issues) == 1
        issue = issues[0]
        assert issue["original_name"] == "bourbon"
        assert issue["occurrences"] == 2
        assert issue["canonical_names"] == [["Bourbon"], ["Bourbon Ají"]]
        assert issue["is_conflict"] is True
        assert issue["indexes"] == [0, 1]

    def test_three_way_conflict_is_detected(self):
        """Three duplicate entries with three different canonicals => a conflict."""
        data = [
            _base_mapping("X", ["A"]),
            _base_mapping("X", ["B"]),
            _base_mapping("X", ["C"]),
        ]
        issues = VarietalCategorizer.validate_mappings_static(data)
        assert len(issues) == 1
        assert issues[0]["original_name"] == "x"
        assert issues[0]["occurrences"] == 3
        assert issues[0]["is_conflict"] is True
        assert issues[0]["indexes"] == [0, 1, 2]

    def test_two_of_three_redundant_is_a_conflict(self):
        """If even one duplicate disagrees, the whole group is a conflict."""
        data = [
            _base_mapping("X", ["A"]),
            _base_mapping("X", ["A"]),
            _base_mapping("X", ["B"]),
        ]
        issues = VarietalCategorizer.validate_mappings_static(data)
        assert len(issues) == 1
        assert issues[0]["is_conflict"] is True

    def test_compound_canonical_order_does_not_matter(self):
        """Two compound entries with the same canonicals in different orders agree."""
        data = [
            _base_mapping("A, B", ["A", "B"], is_compound=True, separator=","),
            _base_mapping("A, B", ["B", "A"], is_compound=True, separator=","),
        ]
        issues = VarietalCategorizer.validate_mappings_static(data)
        assert len(issues) == 1
        assert issues[0]["is_conflict"] is False

    def test_case_insensitive_duplicate_is_detected(self):
        """Two entries that differ only in case are duplicates (DB uses LOWER())."""
        data = [
            _base_mapping("GEISHA", ["GEISHA"]),
            _base_mapping("Geisha", ["Geisha"]),
        ]
        issues = VarietalCategorizer.validate_mappings_static(data)
        assert len(issues) == 1
        issue = issues[0]
        # The case-folded lookup key.
        assert issue["original_name"] == "geisha"
        # But the case variants are preserved for the human reading the report.
        assert issue["original_names"] == ["GEISHA", "Geisha"]
        # Different cases of the same word produce different self-mapped
        # canonicals, so this is a conflict.
        assert issue["is_conflict"] is True

    def test_case_insensitive_redundant_passes_redundantly(self):
        """Two case variants with the SAME canonical_names => redundant, not conflict."""
        data = [
            _base_mapping("Washed", ["Washed"]),
            _base_mapping("WASHED", ["Washed"]),
        ]
        issues = VarietalCategorizer.validate_mappings_static(data)
        assert len(issues) == 1
        assert issues[0]["original_name"] == "washed"
        assert issues[0]["original_names"] == ["Washed", "WASHED"]
        assert issues[0]["is_conflict"] is False

    def test_multiple_independent_duplicates(self):
        """Validator returns one issue per distinct duplicate lookup key."""
        data = [
            _base_mapping("Typica", ["Typica"]),
            _base_mapping("Bourbon", ["Bourbon"]),
            _base_mapping("Typica", ["Typica"]),
            _base_mapping("Bourbon", ["Bourbon Ají"]),
        ]
        issues = VarietalCategorizer.validate_mappings_static(data)
        assert len(issues) == 2
        by_name = {issue["original_name"]: issue for issue in issues}
        assert by_name["typica"]["is_conflict"] is False
        assert by_name["bourbon"]["is_conflict"] is True

    def test_empty_data_has_no_issues(self):
        assert VarietalCategorizer.validate_mappings_static([]) == []


class TestLoaderIntegration:
    """Verify the loader surfaces duplicates instead of silently overwriting."""

    def test_loader_raises_on_duplicates(self, tmp_path):
        mappings_file = tmp_path / "mappings.json"
        mappings_file.write_text(
            json.dumps(
                [
                    _base_mapping("Bourbon", ["Bourbon"]),
                    _base_mapping("Bourbon", ["Bourbon Ají"]),
                ]
            )
        )

        cat = VarietalCategorizer(database_path=tmp_path / "unused.duckdb", mappings_file=mappings_file)
        with pytest.raises(ValueError, match="duplicate original_name"):
            cat.load_existing_mappings()

    def test_loader_succeeds_on_clean_file(self, tmp_path):
        mappings_file = tmp_path / "mappings.json"
        mappings_file.write_text(
            json.dumps(
                [
                    _base_mapping("Typica", ["Typica"]),
                    _base_mapping("Bourbon", ["Bourbon"]),
                ]
            )
        )

        cat = VarietalCategorizer(database_path=tmp_path / "unused.duckdb", mappings_file=mappings_file)
        loaded = cat.load_existing_mappings()
        assert set(loaded) == {"Typica", "Bourbon"}


class TestMappingsFile:
    """End-to-end check against the real mappings file shipped with the repo."""

    # The shipped mappings file has known case-insensitive duplicate conflicts
    # in the varietal data (introduced before the validator was made
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
        duplicate ``original_name`` entries (different canonicals that would
        collide at DB lookup time).

        Redundant case-insensitive duplicates (same canonical under different
        case) are also detected by the validator but are not asserted here --
        they are pre-existing data hygiene issues tracked separately and do
        not break the DB.
        """
        if not MAPPINGS_FILE.exists():
            pytest.skip(f"Mappings file not found: {MAPPINGS_FILE}")
        with open(MAPPINGS_FILE) as f:
            data = json.load(f)
        issues = VarietalCategorizer.validate_mappings_static(data)
        conflicts = [i for i in issues if i["is_conflict"]]
        assert conflicts == [], (
            f"Found {len(conflicts)} CONFLICTING case-insensitive duplicate group(s) "
            f"in {MAPPINGS_FILE}. These collide at DB lookup time and produce "
            f"non-deterministic canonicals. Examples: {conflicts[:3]}"
        )

    def test_shipped_mappings_file_duplicate_count_documented(self):
        """Document the current state of case-insensitive duplicates in the
        shipped file. Informational."""
        if not MAPPINGS_FILE.exists():
            pytest.skip(f"Mappings file not found: {MAPPINGS_FILE}")
        with open(MAPPINGS_FILE) as f:
            data = json.load(f)
        issues = VarietalCategorizer.validate_mappings_static(data)
        conflicts = [i for i in issues if i["is_conflict"]]
        redundant = [i for i in issues if not i["is_conflict"]]
        # Print so a human running this test sees the current state.
        print(
            f"\n[MAPPINGS FILE STATE] {len(issues)} case-insensitive duplicate group(s): "
            f"{len(conflicts)} CONFLICTING, {len(redundant)} redundant"
        )
        for issue in issues[:5]:
            label = "CONFLICT" if issue["is_conflict"] else "redundant"
            print(f"  [{label}] {issue['original_name']!r}: {issue['original_names']}")
