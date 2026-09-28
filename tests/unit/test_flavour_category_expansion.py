#!/usr/bin/env python3
"""Unit tests for hierarchy-aware tasting-note category expansion.

``parse_boolean_search_query_for_field(..., expand_flavour_categories=True)``
widens each bare (non-quoted) term so it also matches tasting-note categories
(primary/secondary/tertiary). Quoted terms remain literal-only.
"""

from kissaten.api.main import parse_boolean_search_query_for_field

ARRAY_FIELD = "array_to_string(cb.tasting_notes, ' ')"


def _count_placeholders(sql: str) -> int:
    return sql.count("?")


def test_expansion_enabled_adds_category_join():
    sql, params = parse_boolean_search_query_for_field("fruity", ARRAY_FIELD, expand_flavour_categories=True)

    assert "JOIN tasting_notes_categories" in sql
    assert "primary_category" in sql
    assert "secondary_category" in sql
    assert "tertiary_category" in sql
    assert len(params) == 4
    assert _count_placeholders(sql) == 4


def test_expansion_disabled_stays_literal_only():
    sql, params = parse_boolean_search_query_for_field("fruity", ARRAY_FIELD, expand_flavour_categories=False)

    assert "tasting_notes_categories" not in sql
    assert "primary_category" not in sql
    assert "ILIKE" in sql
    assert len(params) == 1
    assert params == ["%fruity%"]
    assert _count_placeholders(sql) == 1


def test_quoted_term_stays_literal_only_even_when_expansion_enabled():
    sql, params = parse_boolean_search_query_for_field('"Fruity"', ARRAY_FIELD, expand_flavour_categories=True)

    assert "tasting_notes_categories" not in sql
    assert "JOIN" not in sql
    assert len(params) == 1
    assert params == ["Fruity"]
    assert _count_placeholders(sql) == 1


def test_non_tasting_notes_field_is_unchanged():
    sql, params = parse_boolean_search_query_for_field("fruity", "o.region", expand_flavour_categories=True)

    assert "tasting_notes_categories" not in sql
    assert "unnest(cb.tasting_notes)" not in sql
    assert len(params) == 1
    assert params == ["%fruity%"]


def test_boolean_composition_counts_params():
    sql, params = parse_boolean_search_query_for_field("fruity&!berry", ARRAY_FIELD, expand_flavour_categories=True)

    # 2 bare terms, each contributing 1 literal + 3 category params.
    assert len(params) == 8
    assert _count_placeholders(sql) == 8
    assert " AND " in sql
    assert "NOT " in sql
    assert sql.count("JOIN tasting_notes_categories") == 2


def test_granular_scoring_includes_category_bonus():
    sql, params = parse_boolean_search_query_for_field(
        "fruity",
        "cb.tasting_notes",
        use_granular_scoring=True,
        expand_flavour_categories=True,
    )

    assert "JOIN tasting_notes_categories" in sql
    # Bean-level bonus wrapped around the granular note-level score.
    assert "CASE WHEN EXISTS" in sql
    assert "+ (CASE WHEN EXISTS" in sql
    # 2 note-level params (%... wildcard branch) + 3 category params.
    assert len(params) == 5
    assert _count_placeholders(sql) == 5
