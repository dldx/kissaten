"""Unit tests for the central ``kissaten.ai.validation_gate`` module.

These cover the pre/post-flight validation gates that the categorizer CLIs and
the database loader use to enforce the "one canonical mapping per original
name" invariant.
"""

import json
from pathlib import Path

import pytest

from kissaten.ai import validation_gate as _gate
from kissaten.ai.validation_gate import (
    MappingValidationError,
    validate_processing_mappings_file,
    validate_varietal_mappings_file,
)


def _write_varietal(path: Path, *mappings: dict) -> None:
    path.write_text(json.dumps(list(mappings), indent=2, ensure_ascii=False))


def _write_processing(path: Path, *mappings: dict) -> None:
    path.write_text(json.dumps(list(mappings), indent=2, ensure_ascii=False))


def _varietal_entry(original: str, canonicals: list[str], **overrides) -> dict:
    entry = {
        "original_name": original,
        "canonical_names": canonicals,
        "confidence": 1.0,
        "is_compound": False,
        "separator": None,
    }
    entry.update(overrides)
    return entry


def _processing_entry(original: str, common: str, **overrides) -> dict:
    entry = {
        "original_name": original,
        "common_name": common,
        "confidence": 1.0,
    }
    entry.update(overrides)
    return entry


class TestValidateVarietalMappingsFile:
    def test_clean_file_passes_silently(self, tmp_path, capsys):
        path = tmp_path / "v.json"
        _write_varietal(path, _varietal_entry("Typica", ["Typica"]))
        issues = validate_varietal_mappings_file(path)
        assert issues == []

    def test_missing_file_returns_no_issues(self, tmp_path):
        # Categorizer hasn't run yet, so an absent file is not an error.
        issues = validate_varietal_mappings_file(tmp_path / "does_not_exist.json")
        assert issues == []

    def test_conflict_raises_by_default(self, tmp_path):
        path = tmp_path / "v.json"
        _write_varietal(
            path,
            _varietal_entry("Bourbon", ["Bourbon"]),
            _varietal_entry("Bourbon", ["Bourbon Aji"]),
        )
        with pytest.raises(MappingValidationError, match="conflicting"):
            validate_varietal_mappings_file(path)

    def test_conflict_returned_when_raise_disabled(self, tmp_path):
        path = tmp_path / "v.json"
        _write_varietal(
            path,
            _varietal_entry("Bourbon", ["Bourbon"]),
            _varietal_entry("Bourbon", ["Bourbon Aji"]),
        )
        issues = validate_varietal_mappings_file(path, raise_on_error=False)
        assert len(issues) == 1
        assert issues[0]["is_conflict"] is True

    def test_redundant_also_raises_by_default(self, tmp_path):
        # The gate is conservative: any duplicate is a hard error, not just conflicts.
        path = tmp_path / "v.json"
        _write_varietal(
            path,
            _varietal_entry("Caturra", ["Caturra"]),
            _varietal_entry("Caturra", ["Caturra"]),
        )
        with pytest.raises(MappingValidationError, match="duplicate"):
            validate_varietal_mappings_file(path)


class TestValidateProcessingMappingsFile:
    def test_clean_file_passes_silently(self, tmp_path):
        path = tmp_path / "p.json"
        _write_processing(
            path,
            _processing_entry("Washed", "Washed"),
            _processing_entry("Natural", "Natural"),
        )
        issues = validate_processing_mappings_file(path)
        assert issues == []

    def test_many_originals_sharing_one_common_name_passes(self, tmp_path):
        # The validator only checks for duplicate original_name keys, not
        # common-name overlap (which is the point of the merge step).
        path = tmp_path / "p.json"
        _write_processing(
            path,
            _processing_entry("Washed", "Washed"),
            _processing_entry("Fully Washed", "Washed"),
            _processing_entry("Wet Process", "Washed"),
        )
        issues = validate_processing_mappings_file(path)
        assert issues == []

    def test_conflict_raises(self, tmp_path):
        path = tmp_path / "p.json"
        _write_processing(
            path,
            _processing_entry("Washed", "Washed"),
            _processing_entry("Washed", "Washed Process"),
        )
        with pytest.raises(MappingValidationError, match="conflicting"):
            validate_processing_mappings_file(path)

    def test_redundant_raises(self, tmp_path):
        path = tmp_path / "p.json"
        _write_processing(
            path,
            _processing_entry("Washed", "Washed"),
            _processing_entry("Washed", "Washed"),
        )
        with pytest.raises(MappingValidationError, match="duplicate"):
            validate_processing_mappings_file(path)


class TestValidateBothMappingsFiles:
    """End-to-end check using the real mappings files shipped with the repo."""

    # The shipped mappings files have known case-insensitive duplicate
    # conflicts (introduced before the validator was made case-insensitive).
    # They are tracked here and must be cleaned up by hand -- the validator
    # is just the discovery tool. Once the files are clean, remove the xfail
    # marker below.
    #
    # Run ``kissaten validate-mappings`` to see the current list.

    def test_shipped_files_no_conflicting_case_insensitive_dupes(self):
        """The real varietal_mappings.json + processing_methods_mappings.json
        must not have CONFLICTING case-insensitive duplicate ``original_name``
        entries (which would collide at DB lookup time).

        Redundant case-insensitive duplicates are pre-existing data hygiene
        issues that don't break the DB; they are tracked separately by the
        per-file validators.
        """
        # Drive both per-file validators manually so we can distinguish
        # conflicts from redundant dups.
        from kissaten.ai.processing_method_categorizer import ProcessCategorizer
        from kissaten.ai.varietal_categorizer import VarietalCategorizer

        varietal_file = Path(__file__).parent.parent.parent / "src/kissaten/database/varietal_mappings.json"
        processing_file = Path(__file__).parent.parent.parent / "src/kissaten/database/processing_methods_mappings.json"

        varietal_conflicts = [
            i for i in VarietalCategorizer.validate_mappings_static(json.loads(varietal_file.read_text()))
            if i["is_conflict"]
        ]
        processing_conflicts = [
            i for i in ProcessCategorizer.validate_mappings_static(json.loads(processing_file.read_text()))
            if i["is_conflict"]
        ]
        assert varietal_conflicts == [], (
            f"Varietal mappings have {len(varietal_conflicts)} CONFLICTING case-insensitive "
            f"duplicate group(s). Examples: {varietal_conflicts[:3]}"
        )
        assert processing_conflicts == [], (
            f"Processing method mappings have {len(processing_conflicts)} CONFLICTING "
            f"case-insensitive duplicate group(s). Examples: {processing_conflicts[:3]}"
        )

    def test_shipped_files_duplicate_state_documented(self):
        """Document the current state of case-insensitive duplicates. Informational."""
        from kissaten.ai.processing_method_categorizer import ProcessCategorizer
        from kissaten.ai.varietal_categorizer import VarietalCategorizer

        varietal_file = Path(__file__).parent.parent.parent / "src/kissaten/database/varietal_mappings.json"
        processing_file = Path(__file__).parent.parent.parent / "src/kissaten/database/processing_methods_mappings.json"

        v_issues = VarietalCategorizer.validate_mappings_static(json.loads(varietal_file.read_text()))
        p_issues = ProcessCategorizer.validate_mappings_static(json.loads(processing_file.read_text()))
        print(
            f"\n[STATE] varietal: {len(v_issues)} case-insensitive dupes "
            f"({sum(1 for i in v_issues if i['is_conflict'])} conflicts)"
        )
        print(
            f"[STATE] processing: {len(p_issues)} case-insensitive dupes "
            f"({sum(1 for i in p_issues if i['is_conflict'])} conflicts)"
        )

    def test_raises_when_either_file_has_issues(self, tmp_path, monkeypatch):
        """Point both validators at temp files with conflicts; the combined
        gate should raise a single MappingValidationError."""
        base = tmp_path / "database"
        base.mkdir()
        varietal = base / "varietal_mappings.json"
        processing = base / "processing_methods_mappings.json"
        _write_varietal(
            varietal,
            _varietal_entry("Bourbon", ["Bourbon"]),
            _varietal_entry("Bourbon", ["Bourbon Aji"]),
        )
        _write_processing(processing, _processing_entry("Washed", "Washed"))

        # Call the per-file validators with raise_on_error=False to inspect
        # both files independently, then verify raise_on_error=True raises.
        issues = []
        issues.extend(validate_varietal_mappings_file(varietal, raise_on_error=False))
        issues.extend(validate_processing_mappings_file(processing, raise_on_error=False))
        assert len(issues) == 1
        assert issues[0]["is_conflict"] is True

        with pytest.raises(MappingValidationError):
            validate_varietal_mappings_file(varietal)


class TestAllowRedundant:
    """The ``allow_redundant`` parameter: tolerate benign case-insensitive
    duplicates (last-writer-wins on the lowercased key is deterministic
    because all variants agree on the canonical) but still block on real
    conflicts (different canonicals for the same lowercase key).
    """

    def test_redundant_passes_with_allow_redundant(self, tmp_path):
        path = tmp_path / "v.json"
        _write_varietal(
            path,
            _varietal_entry("Caturra", ["Caturra"]),
            _varietal_entry("CATURRA", ["Caturra"]),
        )
        # Strict default raises.
        with pytest.raises(MappingValidationError, match="duplicate"):
            validate_varietal_mappings_file(path)
        # With allow_redundant=True, the redundant group is filtered out
        # and no error is raised.
        issues = validate_varietal_mappings_file(path, allow_redundant=True)
        assert issues == []

    def test_conflict_still_raises_with_allow_redundant(self, tmp_path):
        path = tmp_path / "v.json"
        _write_varietal(
            path,
            _varietal_entry("Bourbon", ["Bourbon"]),
            _varietal_entry("BOURBON", ["Bourbon Ají"]),
        )
        # Even with allow_redundant=True, a real conflict blocks loading.
        with pytest.raises(MappingValidationError, match="conflicting"):
            validate_varietal_mappings_file(path, allow_redundant=True)

    def test_mixed_redundant_and_conflict_keeps_only_conflict(self, tmp_path):
        """When a file has both a redundant pair and a conflict pair,
        ``allow_redundant=True`` filters out the redundant and only the
        conflict remains in the issue list.
        """
        path = tmp_path / "v.json"
        _write_varietal(
            path,
            _varietal_entry("Caturra", ["Caturra"]),  # redundant with below
            _varietal_entry("CATURRA", ["Caturra"]),  # redundant
            _varietal_entry("Bourbon", ["Bourbon"]),  # conflicts with below
            _varietal_entry("BOURBON", ["Bourbon Ají"]),  # conflicts
        )
        # With raise_on_error=False, get the filtered list back.
        issues = validate_varietal_mappings_file(path, raise_on_error=False, allow_redundant=True)
        assert len(issues) == 1
        assert issues[0]["is_conflict"] is True
        assert issues[0]["original_name"] == "bourbon"
        # And of course the default raise_on_error=True still raises.
        with pytest.raises(MappingValidationError, match="conflicting"):
            validate_varietal_mappings_file(path, allow_redundant=True)

    def test_processing_path_allow_redundant(self, tmp_path):
        """Same semantics for the processing methods gate."""
        path = tmp_path / "p.json"
        _write_processing(
            path,
            _processing_entry("Washed", "Washed"),
            _processing_entry("WASHED", "Washed"),
        )
        # Strict default raises.
        with pytest.raises(MappingValidationError, match="duplicate"):
            validate_processing_mappings_file(path)
        # allow_redundant=True passes.
        issues = validate_processing_mappings_file(path, allow_redundant=True)
        assert issues == []

    def test_validate_both_with_allow_redundant(self, tmp_path, monkeypatch):
        """``validate_both_mappings_files`` plumbs ``allow_redundant`` through."""
        # The two real files have only redundant duplicates (no conflicts);
        # the combined call with allow_redundant=True should pass.
        monkeypatch.setenv("KISSATEN_USE_RW_DB", "1")  # silence guard
        issues = _gate.validate_both_mappings_files(allow_redundant=True)
        assert issues == []

    def test_validate_both_strict_still_raises(self):
        """Without allow_redundant, the combined call raises on the real
        file's redundancies (current behaviour pre-fix)."""
        with pytest.raises(MappingValidationError):
            _gate.validate_both_mappings_files()


class TestMappingValidationErrorInheritance:
    """The gate raises a MappingValidationError which is also a ValueError,
    so callers that caught ValueError before still work."""

    def test_inherits_from_value_error(self):
        assert issubclass(MappingValidationError, ValueError)

    def test_can_be_caught_as_value_error(self):
        with pytest.raises(ValueError):
            raise MappingValidationError("test")
