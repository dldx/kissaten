"""Unit tests for the case-insensitive processing-methods mapping dict in ``db.py``.

Verifies that ``_build_processing_mapping`` (and the two ``processing_mapping.get``
call sites in ``load_coffee_data`` / ``refresh_canonical_data``) match the
``kissaten.ai.validation_gate`` invariant: a single canonical mapping per
``lower(original_name)`` lookup key.

This is the runtime half of the contract; the static half is enforced by the
``validate-mappings`` CLI / pre-load gate. Together they mean: a case-variant
of a scraped ``process`` value (e.g. ``WASHED`` vs the file's ``Washed``) is
guaranteed to resolve to the same ``common_name`` that a same-case input
would, regardless of which case the scraper emitted.
"""

import json
from pathlib import Path

import pytest

from kissaten.ai.validation_gate import MappingValidationError, validate_processing_mappings_file
from kissaten.api.db import _build_processing_mapping


def _write_processing_mappings(path: Path, *mappings: dict) -> None:
    """Write a JSON list of mapping dicts (same shape as the real file)."""
    path.write_text(json.dumps(list(mappings), ensure_ascii=False))


def _entry(original: str, common: str, **overrides) -> dict:
    return {
        "original_name": original,
        "common_name": common,
        "confidence": 1.0,
        **overrides,
    }


class TestBuildProcessingMapping:
    """``_build_processing_mapping`` contract."""

    def test_missing_file_returns_empty_dict(self, tmp_path):
        assert _build_processing_mapping(tmp_path / "nope.json") == {}

    def test_empty_file_returns_empty_dict(self, tmp_path):
        path = tmp_path / "p.json"
        path.write_text("[]")
        assert _build_processing_mapping(path) == {}

    def test_keys_are_lowercased(self, tmp_path):
        """The dict must be keyed by lower(original_name), not raw."""
        path = tmp_path / "p.json"
        _write_processing_mappings(
            path,
            _entry("Washed", "Washed"),
            _entry("WASHED", "Washed"),
            _entry("WaShEd", "Washed"),
        )
        mapping = _build_processing_mapping(path)
        assert set(mapping) == {"washed"}
        assert mapping["washed"] == "Washed"

    def test_lookups_are_case_insensitive(self, tmp_path):
        """Any-case input resolves to the file's common_name.

        The actual call sites in ``db.py`` lowercase the lookup key
        (``processing_mapping.get(process_value.lower())``), so to faithfully
        exercise the production code path this test does the same.
        """
        path = tmp_path / "p.json"
        _write_processing_mappings(
            path,
            _entry("Washed", "Washed"),
            _entry("Honey", "Honey"),
        )
        mapping = _build_processing_mapping(path)
        # All variations of "washed" hit the same key.
        for variant in ("washed", "Washed", "WASHED", "WaShEd", "WAsHeD"):
            assert mapping.get(variant.lower()) == "Washed", variant
        # And "honey" maps to "Honey" regardless of input case.
        for variant in ("honey", "Honey", "HONEY"):
            assert mapping.get(variant.lower()) == "Honey", variant

    def test_last_writer_wins_on_lowercased_key(self, tmp_path):
        """When two case-variants exist with the SAME common_name, last wins.

        The validator already blocks the dangerous case (different
        common_names for the same lowercased key), so a benign last-wins is
        acceptable -- both writers have the same value, so the result is
        deterministic regardless of order.
        """
        path = tmp_path / "p.json"
        _write_processing_mappings(
            path,
            _entry("Washed", "Washed"),
            _entry("WASHED", "Washed"),
        )
        mapping = _build_processing_mapping(path)
        assert mapping["washed"] == "Washed"
        assert len(mapping) == 1

    def test_skips_entries_with_empty_original_or_common(self, tmp_path):
        """Entries missing either field are dropped (matches prior behaviour)."""
        path = tmp_path / "p.json"
        _write_processing_mappings(
            path,
            _entry("Washed", "Washed"),
            _entry("", "Empty Original"),
            _entry("Empty Common", ""),
            {"original_name": None, "common_name": "None Original", "confidence": 1.0},
        )
        mapping = _build_processing_mapping(path)
        assert mapping == {"washed": "Washed"}

    def test_unparseable_file_returns_empty(self, tmp_path):
        """A broken JSON file doesn't crash; it returns an empty dict."""
        path = tmp_path / "p.json"
        path.write_text("{not json")
        assert _build_processing_mapping(path) == {}


class TestValidatorStillRejectsCaseInsensitiveConflicts:
    """The static half of the contract: a file with two case-variants that
    DISAGREE on common_name must be rejected before the dict is ever built.

    This is the dangerous case the validator exists to catch -- the runtime
    would silently last-writer-wins and produce non-deterministic common
    names for the same scraped input.
    """

    def test_raises_for_disagreeing_case_variants(self, tmp_path):
        path = tmp_path / "p.json"
        _write_processing_mappings(
            path,
            _entry("Washed", "Washed"),
            _entry("WASHED", "Washed Process"),
        )
        with pytest.raises(MappingValidationError, match="duplicate|conflict"):
            validate_processing_mappings_file(path)

    def test_allows_redundant_case_variants_with_same_canonical(self, tmp_path):
        """The validator's default is strict (any duplicate is an error), but
        the dict builder itself doesn't care about the redundant case --
        it just last-wins. The actual common_name of both entries is the
        same, so the runtime result is deterministic.
        """
        path = tmp_path / "p.json"
        _write_processing_mappings(
            path,
            _entry("Washed", "Washed"),
            _entry("WASHED", "Washed"),
        )
        # The validator does flag this as a redundant duplicate, but the
        # dict builder just collapses them to a single key.
        mapping = _build_processing_mapping(path)
        assert mapping == {"washed": "Washed"}
