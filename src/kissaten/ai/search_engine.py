"""Switchable AI search engine facade.

Keeps both engine implementations alongside each other and selects one via the
``KISSATEN_AI_SEARCH_ENGINE`` environment variable:

* ``llm`` (default) — the Gemini/PydanticAI :class:`AISearchAgent`.
* ``jev`` — the hybrid TypeSafe :class:`JevSearchAgent`; falls back to the LLM
  engine when Jev is unavailable (missing ``TYPESAFE_API_KEY`` or any init
  error).

Both engines share ONE :class:`AISearchCache` instance; two DuckDB connections
to the same cache file would contend.
"""

from __future__ import annotations

import logging
import os

from .search_agent import AISearchAgent, BaseSearchTranslator

logger = logging.getLogger(__name__)

# "llm" | "jev".  Read from the environment at import time; ``SearchTranslator``
# also consults the env var at construction time so the module attribute can be
# monkeypatched in tests while the live smoke can set the env after import.
AI_SEARCH_ENGINE = os.getenv("KISSATEN_AI_SEARCH_ENGINE", "llm").strip().lower()


def _resolve_engine() -> str:
    """Return the configured engine, preferring the env var over the module attr."""
    engine = os.getenv("KISSATEN_AI_SEARCH_ENGINE", "").strip().lower()
    return engine or AI_SEARCH_ENGINE


class SearchTranslator:
    """Facade routing translations to the configured engine.

    Image queries (and any query when Jev is unavailable) go to the Gemini
    ``AISearchAgent``; text queries go to Jev when it is the configured engine.
    """

    def __init__(self, database_connection, cache_db_path: str | None = None):
        # One cache instance shared by both engines (built here, passed to Jev).
        self._llm: BaseSearchTranslator = AISearchAgent(database_connection, cache_db_path=cache_db_path)
        self._jev: BaseSearchTranslator | None = None

        if _resolve_engine() == "jev":
            try:
                # Lazy import keeps ``search_agent`` free of a Jev dependency and
                # avoids any import cycle.
                from .jev.agent import JevSearchAgent

                self._jev = JevSearchAgent(
                    database_connection,
                    cache=self._llm.cache,
                    cache_db_path=cache_db_path,
                )
                logger.info("AI search engine: Jev (hybrid TypeSafe)")
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    f"Failed to initialize the Jev search engine ({type(exc).__name__}: {exc}); "
                    "falling back to the LLM engine"
                )
                self._jev = None
        else:
            logger.info("AI search engine: LLM (Gemini)")

    @property
    def cache(self):
        """The shared ``AISearchCache`` (API endpoints use ``ai_agent.cache`` heavily)."""
        return self._llm.cache

    async def translate_query(self, query: str | None = None, image_data: bytes | None = None):
        """Route the translation to the appropriate engine."""
        if image_data is not None or self._jev is None:
            return await self._llm.translate_query(query=query, image_data=image_data)
        return await self._jev.translate_query(query=query)


def get_search_translator(database_connection, cache_db_path: str | None = None) -> SearchTranslator:
    """Build a :class:`SearchTranslator` for the configured engine."""
    return SearchTranslator(database_connection, cache_db_path=cache_db_path)
