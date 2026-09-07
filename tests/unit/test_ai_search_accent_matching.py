"""Unit tests for accent-insensitive roaster matching in the AI search agent.

Typing "cafen" (no accents) must find the roaster "cafēn" even though the
context filter uses substring matching and the backend matches roaster names
exactly. These tests cover:
- ``_strip_accents``: diacritics are removed so "cafēn" → "cafen".
- ``_generate_query_ngrams``: query words are accent-stripped before matching.

- ``_filter_context_by_query``: an accent-free query surfaces the accented roaster.

- ``_resolve_canonical_roasters``: AI output like "cafen" is rewritten to the
  exact stored name "cafēn" for the backend's exact-match filter.

The tested methods are pure (no DB connection or API key needed), so the agent is
constructed via ``object.__new__`` to skip ``__init__``.

"""

import pytest

from kissaten.ai.search_agent import AISearchAgent
from kissaten.schemas.ai_search import SearchContext


@pytest.fixture
def agent():
    return object.__new__(AISearchAgent)


@pytest.fixture
def context():
    return SearchContext(
        available_roasters=["cafēn", "Coffee Collective", "KillBean"],
        available_tasting_notes=[],
        available_varietals=[],
        available_processes=[],
        available_roast_levels=[],
        available_countries=[],
        available_roaster_locations=[],
        available_farms=[],
        available_producers=[],
        available_regions=[],
    )


class TestStripAccents:
    def test_removes_diacritics(self, agent):
        assert agent._strip_accents("cafēn") == "cafen"
        assert agent._strip_accents("Nariño") == "Narino"
        assert agent._strip_accents("Sudán Rumé") == "Sudan Rume"

    def test_leaves_plain_text_unchanged(self, agent):
        assert agent._strip_accents("Coffee Collective") == "Coffee Collective"


class TestGenerateQueryNgrams:
    def test_words_are_accent_stripped(self, agent):
        ngrams = agent._generate_query_ngrams("find me cafen coffee")
        assert "cafen" in ngrams

    def test_accented_query_word_matches_plain_item(self, agent):
        # A query typed with the accent should also still work.

        ngrams = agent._generate_query_ngrams("cafēn")
        assert "cafen" in ngrams


class TestFilterContextByQuery:
    def test_accent_free_query_finds_accented_roaster(self, agent, context):
        filtered = agent._filter_context_by_query("cafen", context)
        assert "cafēn" in filtered["roasters"]

    def test_accented_query_finds_accented_roaster(self, agent, context):
        filtered = agent._filter_context_by_query("cafēn", context)
        assert "cafēn" in filtered["roasters"]

    def test_case_insensitive_roaster_match(self, agent, context):
        filtered = agent._filter_context_by_query("CAFEN", context)
        assert "cafēn" in filtered["roasters"]


class TestResolveCanonicalRoasters:
    def test_maps_accent_free_name_to_stored_name(self, agent):
        resolved = agent._resolve_canonical_roasters(
            ["cafen", "Coffee Collective"], ["cafēn", "Coffee Collective", "KillBean"]
        )
        assert resolved == ["cafēn", "Coffee Collective"]

    def test_case_insensitive_mapping(self, agent):
        resolved = agent._resolve_canonical_roasters(["CAFEN"], ["cafēn"])
        assert resolved == ["cafēn"]

    def test_unknown_names_pass_through(self, agent):
        resolved = agent._resolve_canonical_roasters(["Unknown Roaster"], ["cafēn"])
        assert resolved == ["Unknown Roaster"]
