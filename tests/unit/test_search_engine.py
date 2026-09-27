"""Unit tests for the switchable AI search engine facade (``search_engine.py``).

Hermetic: no network, no real API keys, no real DuckDB.  The engine classes are
monkeypatched with lightweight stubs so routing can be asserted directly.  The
real ``JevSearchAgent`` is also exercised for its constructor guard and its
text-only contract (both fail before any model call).
"""

import pytest

import kissaten.ai.jev.agent as jev_agent
import kissaten.ai.search_engine as se
from kissaten.ai.search_agent import AISearchAgent, BaseSearchTranslator


class _FakeLLM:
    """Stand-in for ``AISearchAgent`` recording ``translate_query`` calls."""

    def __init__(self, database_connection, api_key=None, cache_db_path=None, cache=None):
        self.conn = database_connection
        self.cache = object()
        self.calls = []

    async def translate_query(self, query=None, image_data=None):
        self.calls.append((query, image_data))
        return "llm-result"


class _FakeJev:
    """Stand-in for ``JevSearchAgent`` recording ``translate_query`` calls."""

    def __init__(
        self,
        database_connection,
        api_key=None,
        cache_db_path=None,
        cache=None,
        model_pin=None,
        regex_model=None,
        top_notes=8,
    ):
        self.conn = database_connection
        self.cache = cache
        self.calls = []

    async def translate_query(self, query=None, image_data=None):
        self.calls.append((query, image_data))
        return "jev-result"


def test_default_engine_is_llm():
    # Module attribute is populated from the (unset) env at import time.
    assert se.AI_SEARCH_ENGINE == "llm"


def test_engines_are_base_subclasses():
    assert issubclass(AISearchAgent, BaseSearchTranslator)
    assert issubclass(jev_agent.JevSearchAgent, BaseSearchTranslator)
    assert jev_agent.JevSearchAgent is not AISearchAgent


async def test_engine_llm_routes_to_llm_and_shares_cache(monkeypatch):
    monkeypatch.delenv("KISSATEN_AI_SEARCH_ENGINE", raising=False)
    monkeypatch.setattr(se, "AI_SEARCH_ENGINE", "llm")
    monkeypatch.setattr(se, "AISearchAgent", _FakeLLM)

    translator = se.SearchTranslator(object())

    assert translator._jev is None
    assert translator.cache is translator._llm.cache
    assert await translator.translate_query("x") == "llm-result"
    assert translator._llm.calls == [("x", None)]
    # Image queries always go to the LLM engine.
    assert await translator.translate_query(query=None, image_data=b"img") == "llm-result"
    assert translator._llm.calls[-1] == (None, b"img")


async def test_engine_jev_routes_text_to_jev_images_to_llm(monkeypatch):
    monkeypatch.delenv("KISSATEN_AI_SEARCH_ENGINE", raising=False)
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(se, "AI_SEARCH_ENGINE", "jev")
    monkeypatch.setattr(se, "AISearchAgent", _FakeLLM)
    monkeypatch.setattr(jev_agent, "JevSearchAgent", _FakeJev)

    translator = se.SearchTranslator(object())

    assert isinstance(translator._jev, _FakeJev)
    # The Jev engine shares the LLM engine's cache instance.
    assert translator._jev.cache is translator._llm.cache

    assert await translator.translate_query("x") == "jev-result"
    assert translator._jev.calls == [("x", None)]

    # Images are routed to the LLM engine even when Jev is configured.
    assert await translator.translate_query(query=None, image_data=b"img") == "llm-result"
    assert translator._llm.calls == [(None, b"img")]


async def test_engine_jev_without_key_falls_back_to_llm(monkeypatch):
    monkeypatch.delenv("KISSATEN_AI_SEARCH_ENGINE", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(se, "AI_SEARCH_ENGINE", "jev")
    monkeypatch.setattr(se, "AISearchAgent", _FakeLLM)

    # The real JevSearchAgent is used here: its constructor raises on the
    # missing TYPESAFE_API_KEY, which the facade catches and falls back.
    translator = se.SearchTranslator(object())

    assert translator._jev is None
    assert await translator.translate_query("x") == "llm-result"


async def test_real_jev_engine_is_text_only(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    agent = jev_agent.JevSearchAgent(object(), cache=object())
    with pytest.raises(NotImplementedError):
        await agent._produce_search_params("x", b"img", object())


def test_get_search_translator_factory(monkeypatch):
    monkeypatch.delenv("KISSATEN_AI_SEARCH_ENGINE", raising=False)
    monkeypatch.setattr(se, "AI_SEARCH_ENGINE", "llm")
    monkeypatch.setattr(se, "AISearchAgent", _FakeLLM)

    translator = se.get_search_translator(object())
    assert isinstance(translator, se.SearchTranslator)
    assert translator._jev is None
