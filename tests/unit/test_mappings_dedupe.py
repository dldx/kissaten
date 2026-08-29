"""Unit tests for the ``dedupe_mappings_static`` helpers.

These verify that both ``VarietalCategorizer.dedupe_mappings_static`` and
``ProcessCategorizer.dedupe_mappings_static`` correctly collapse redundant
case-variant duplicates (entries that differ only by case and map to IDENTICAL
canonicals) while leaving genuine conflicts (different canonicals) fully intact
for human review.
"""

from kissaten.ai.processing_method_categorizer import ProcessCategorizer
from kissaten.ai.varietal_categorizer import VarietalCategorizer


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def _varietal(original: str, canonicals: list[str], **overrides) -> dict:
    entry = {
        "original_name": original,
        "canonical_names": canonicals,
        "confidence": 1.0,
        "is_compound": False,
        "separator": None,
    }
    entry.update(overrides)
    return entry


def _processing(original: str, common: str, **overrides) -> dict:
    entry = {
        "original_name": original,
        "common_name": common,
        "confidence": 1.0,
    }
    entry.update(overrides)
    return entry


# ---------------------------------------------------------------------------
# Varietal
# ---------------------------------------------------------------------------
class TestVarietalDedupe:
    def test_redundant_group_collapsed(self):
        """Case-variants mapping to identical canonicals collapse to one entry."""
        data = [
            _varietal("BOURBON PIMIENTA", ["Bourbon Pimienta"]),
            _varietal("Bourbon Pimienta", ["Bourbon Pimienta"]),
            _varietal("Typica", ["Typica"]),
        ]
        deduped, dropped = VarietalCategorizer.dedupe_mappings_static(data)
        assert [d["original_name"] for d in deduped] == ["Bourbon Pimienta", "Typica"]
        # The all-caps variant is dropped, the title-case one is kept.
        assert [d["original_name"] for d in dropped] == ["BOURBON PIMIENTA"]

    def test_conflicting_group_left_intact(self):
        """Different canonicals => conflict; no entry is dropped."""
        data = [
            _varietal("Bourbon", ["Bourbon"]),
            _varietal("BOURBON", ["Bourbon Ají"]),
        ]
        deduped, dropped = VarietalCategorizer.dedupe_mappings_static(data)
        assert len(deduped) == 2
        assert dropped == []
        # Both entries survive unchanged.
        canonicals = {tuple(d["canonical_names"]) for d in deduped}
        assert canonicals == {("Bourbon",), ("Bourbon Ají",)}

    def test_three_way_conflict_left_intact(self):
        data = [
            _varietal("X", ["A"]),
            _varietal("x", ["B"]),
            _varietal("X", ["C"]),
        ]
        deduped, dropped = VarietalCategorizer.dedupe_mappings_static(data)
        assert len(deduped) == 3
        assert dropped == []

    def test_mixed_group_with_any_disagreement_is_conflict(self):
        """If even one entry disagrees, the whole group is a conflict."""
        data = [
            _varietal("X", ["A"]),
            _varietal("x", ["A"]),
            _varietal("X", ["B"]),
        ]
        deduped, dropped = VarietalCategorizer.dedupe_mappings_static(data)
        assert len(deduped) == 3
        assert dropped == []

    def test_compound_canonical_order_does_not_matter(self):
        """Same canonicals in different orders are redundant (sorted signature)."""
        data = [
            _varietal("A, B", ["B", "A"], is_compound=True, separator=","),
            _varietal("A, b", ["A", "B"], is_compound=True, separator=","),
        ]
        deduped, dropped = VarietalCategorizer.dedupe_mappings_static(data)
        assert len(deduped) == 1
        assert len(dropped) == 1

    def test_representative_prefers_non_allocaps(self):
        """Given an ALL-CAPS and a title-case variant of equal confidence, the
        title-case (lowercase-containing) one is kept."""
        data = [
            _varietal("GEISHA", ["Gesha"]),
            _varietal("Geisha", ["Gesha"]),
        ]
        deduped, dropped = VarietalCategorizer.dedupe_mappings_static(data)
        assert deduped[0]["original_name"] == "Geisha"
        assert [d["original_name"] for d in dropped] == ["GEISHA"]

    def test_representative_prefers_higher_confidence(self):
        """When both variants contain lowercase, higher confidence wins."""
        data = [
            _varietal("Heirloom", ["Heirloom"], confidence=0.7),
            _varietal("heirloom", ["Heirloom"], confidence=1.0),
        ]
        deduped, _ = VarietalCategorizer.dedupe_mappings_static(data)
        assert deduped[0]["original_name"] == "heirloom"

    def test_order_preserved(self):
        """Kept entries retain their original file order."""
        data = [
            _varietal("Typica", ["Typica"]),
            _varietal("BOURBON", ["Bourbon"]),
            _varietal("Bourbon", ["Bourbon"]),
            _varietal("Caturra", ["Caturra"]),
        ]
        deduped, _ = VarietalCategorizer.dedupe_mappings_static(data)
        assert [d["original_name"] for d in deduped] == ["Typica", "Bourbon", "Caturra"]

    def test_round_trip_has_zero_redundant_groups(self):
        """Re-validating the deduped output leaves no redundant groups."""
        data = [
            _varietal("HEIRLOOM", ["Heirloom"]),
            _varietal("Heirloom", ["Heirloom"]),
            _varietal("heirloom", ["Heirloom"]),
            _varietal("Bourbon", ["Bourbon"]),
            _varietal("BOURBON", ["Bourbon Ají"]),  # conflict, left intact
        ]
        deduped, _ = VarietalCategorizer.dedupe_mappings_static(data)
        issues = VarietalCategorizer.validate_mappings_static(deduped)
        conflicts = [i for i in issues if i["is_conflict"]]
        redundant = [i for i in issues if not i["is_conflict"]]
        assert redundant == []
        assert len(conflicts) == 1
        assert conflicts[0]["original_name"] == "bourbon"


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------
class TestProcessingDedupe:
    def test_redundant_group_collapsed(self):
        data = [
            _processing("ANAEROBIC HONEY CO-FERMENTED", "Anaerobic Honey Co-Fermented"),
            _processing("Anaerobic Honey Co-Fermented", "Anaerobic Honey Co-Fermented"),
            _processing("Washed", "Washed"),
        ]
        deduped, dropped = ProcessCategorizer.dedupe_mappings_static(data)
        assert [d["original_name"] for d in deduped] == [
            "Anaerobic Honey Co-Fermented",
            "Washed",
        ]
        assert [d["original_name"] for d in dropped] == ["ANAEROBIC HONEY CO-FERMENTED"]

    def test_conflicting_group_left_intact(self):
        data = [
            _processing("Washed", "Washed"),
            _processing("WASHED", "Washed Process"),
        ]
        deduped, dropped = ProcessCategorizer.dedupe_mappings_static(data)
        assert len(deduped) == 2
        assert dropped == []
        assert {d["common_name"] for d in deduped} == {"Washed", "Washed Process"}

    def test_representative_prefers_non_allocaps(self):
        data = [
            _processing("FULLY WASHED", "Fully Washed"),
            _processing("Fully Washed", "Fully Washed"),
        ]
        deduped, dropped = ProcessCategorizer.dedupe_mappings_static(data)
        assert deduped[0]["original_name"] == "Fully Washed"
        assert [d["original_name"] for d in dropped] == ["FULLY WASHED"]

    def test_representative_prefers_higher_confidence(self):
        data = [
            _processing("natural", "Natural", confidence=0.8),
            _processing("Natural", "Natural", confidence=1.0),
        ]
        deduped, _ = ProcessCategorizer.dedupe_mappings_static(data)
        assert deduped[0]["original_name"] == "Natural"

    def test_order_preserved(self):
        data = [
            _processing("Washed", "Washed"),
            _processing("HONEY", "Honey"),
            _processing("Honey", "Honey"),
            _processing("Natural", "Natural"),
        ]
        deduped, _ = ProcessCategorizer.dedupe_mappings_static(data)
        assert [d["original_name"] for d in deduped] == ["Washed", "Honey", "Natural"]

    def test_round_trip_has_zero_redundant_groups(self):
        data = [
            _processing("anaerobic honey", "Anaerobic Honey"),
            _processing("Anaerobic Honey", "Anaerobic Honey"),
            _processing("Washed", "Washed"),
            _processing("WASHED", "Washed Process"),  # conflict, left intact
        ]
        deduped, _ = ProcessCategorizer.dedupe_mappings_static(data)
        issues = ProcessCategorizer.validate_mappings_static(deduped)
        conflicts = [i for i in issues if i["is_conflict"]]
        redundant = [i for i in issues if not i["is_conflict"]]
        assert redundant == []
        assert len(conflicts) == 1
        assert conflicts[0]["original_name"] == "washed"
