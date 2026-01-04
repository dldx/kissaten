"""Test invalid region detection in region selector."""

import pytest
from kissaten.ai.region_selector import RegionSelection


def test_region_selection_allows_none():
    """Test that RegionSelection model allows None for invalid regions."""
    # Valid region
    valid = RegionSelection(
        selected_index=0,
        canonical_state="Chiriquí",
        confidence=0.85,
        reasoning="Clear match with high confidence",
        metadata={},
    )
    assert valid.selected_index == 0
    assert valid.canonical_state == "Chiriquí"

    # Invalid region (None values)
    invalid = RegionSelection(
        selected_index=None,
        canonical_state=None,
        confidence=0.1,
        reasoning="No valid state found, appears to be a typo",
        metadata={},
    )
    assert invalid.selected_index is None
    assert invalid.canonical_state is None
    assert invalid.confidence == 0.1


def test_region_selection_defaults():
    """Test that RegionSelection has proper defaults."""
    minimal = RegionSelection(
        confidence=0.5,
        reasoning="Test region",
    )
    assert minimal.selected_index is None
    assert minimal.canonical_state is None
    assert minimal.metadata == {}


@pytest.mark.parametrize(
    "confidence,expected_valid",
    [
        (0.0, False),  # Very low confidence - likely invalid
        (0.1, False),  # Low confidence - possibly invalid
        (0.3, True),   # Some confidence - edge case
        (0.5, True),   # Medium confidence
        (0.7, True),   # High confidence
        (1.0, True),   # Perfect confidence
    ],
)
def test_confidence_thresholds(confidence, expected_valid):
    """Test that confidence scores are properly handled."""
    selection = RegionSelection(
        selected_index=0 if expected_valid else None,
        canonical_state="Test State" if expected_valid else None,
        confidence=confidence,
        reasoning=f"Confidence test at {confidence}",
    )
    assert selection.confidence == confidence
    assert (selection.canonical_state is not None) == expected_valid
