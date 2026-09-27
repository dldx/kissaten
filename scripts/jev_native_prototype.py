"""TypeSafe Jev smart-search translator — native pydantic-ai TypeSafe adapter.

The Jev smart-search prototype: a drop-in alternative to the Gemini-powered
``AISearchAgent.translate_query`` pipeline in ``src/kissaten/ai/search_agent.py``.
It uses pydantic-ai's TypeSafe adapter (``Agent('typesafe:jev-latest',
output_type=<pydantic model>)``) to run TypeSafe's Jev System One model.  The
output model is built per-query with ``pydantic.create_model`` — static
``Literal``/``bool`` fields plus dynamic ``Choices(...)`` candidate sets — and
the adapter's primitive mapping guarantees the model answers with structured
semantics:

    pydantic type                        Jev primitive
    ---------------------------------    --------------
    bool                                 Noul
    Literal[str, ...] / Enum             Choice
    float = Field(ge=0, le=1)            probability
    IntEnum + UseEnumMemberDocstrings    Score
    list[Literal/Enum/Choices]           one Noul per option (multi-select)
    nested model fields                  dotted question paths
    Optional[Literal]                    Choice with auto-added ``None``

``Choices({name: desc, ...}, name=..., description=...)`` returns a TYPE usable
as a field annotation, so per-query candidate lists (roasters, varieties,
countries, ...) become per-run ``output_type=`` models.  State is derived from
the *user message* (the query + filtered-context text); ``instructions=``
becomes shared framing inside each question; per-field ``description`` IS the
question.

Then the SAME pure composition (``jev_common.compose_search_params`` +
deterministic regex extraction) turns the answers into an identical
``SearchParameters``/``search_url``.  The pure/deterministic logic and the
benchmark data (``GOLDEN_SET``/``TRACKED_FIELDS``) are shared from
``jev_common``.

Working run command (verified 2026-09-23; repo pins ``pydantic-ai>=1.107.1,<2``
so pydantic-ai 2.x is layered via ``uv run --with`` WITHOUT touching
pyproject.toml)::

    PYTHONPATH=src uv run --with "pydantic-ai[typesafe]>=2.45" \\
        python scripts/jev_native_prototype.py "fruity Ethiopian coffee under £25" --json

    PYTHONPATH=src uv run --with "pydantic-ai[typesafe]>=2.45" \\
        python scripts/jev_native_prototype.py --benchmark

    PYTHONPATH=src uv run --with "pydantic-ai[typesafe]>=2.45" \\
        python scripts/jev_native_prototype.py --serve --port 8765

  (pydantic-ai 2.48.0 + typesafe-sdk 0.7.1 resolve against the project env.)

Hybrid split: by default the wildcard-grammar ``tasting_notes_search`` field is
composed by a second small Gemini agent (``gemini-2.5-flash-lite``, the same
model the production ``AISearchAgent`` uses) instead of being derived from Jev
candidate picks — pass ``--no-regex-llm`` to disable the LLM and fall back to
the Jev note candidates, or ``--regex-model <name>`` to swap the model.  A Jev
``needs_tasting_notes`` noul gates that second call: when Jev says the query
has no taste intent (e.g. 'Standout ture waji', a roaster + producer lookup)
Gemini is skipped entirely and ``tasting_notes_search`` stays ``None``.

Candidate-choice gates: like ``needs_origin`` (in front of ``params.origin``),
three more nouls — ``needs_region`` / ``needs_variety`` / ``needs_farm`` —
sit in front of ``params.region`` / ``params.variety`` / ``params.farm``
composition in ``compose_search_params``.  Each only composes the field when
the query *names* it: a whole country ('el salvador') is the coffee's origin,
not a region; a farm/estate name ('Kotowa', 'Finca el paraiso' -> 'Paraiso')
is not a region/variety.  ``producer`` stays ungated.

``--serve`` runs a self-contained FastAPI + PicoCSS inspector on
``127.0.0.1:8765`` by default (``--host`` / ``--port`` override it).  Open the
page, type a query, and it shows EVERY model call the translation makes, each
with its raw request and raw response: the Jev ``/v1/systemone`` request
payload (``state`` + per-question ``instructions``/``criteria``/``type``), the
raw response (answers + probabilities + usage), and, when the regex LLM is on,
the Gemini ``generateContent`` request/response too — plus per-call latency and
the composed ``SearchParameters`` + ``search_url``.
The wire is captured by handing the ``TypeSafeProvider`` a custom
``httpx2.AsyncClient`` whose transport (a subclass of
``httpx2.AsyncHTTPTransport``) records every request/response body it carries —
no monkeypatching, and the same context-building / model-construction /
composition pipeline as the CLI paths (``run_for_demo`` only).  FastAPI, uvicorn
and httpx2 are imported only inside the serve path, so normal runs are
unchanged.

  Fully isolated (no project env at all)::

    PYTHONPATH=src uv run --no-project --with "pydantic-ai[typesafe]>=2.45" \\
        --with python-dotenv --with duckdb \\
        python scripts/jev_native_prototype.py "fruity Ethiopian coffee under £25" --json

Logfire tracing is ON by default (token from ``LOGFIRE_TOKEN`` in ``.env``).
The project-pinned logfire 4.39.0 works with pydantic-ai 2.x out of the box —
pydantic-ai 2.x still ships ``pydantic_ai.agent.InstrumentationSettings`` and
itself requires ``logfire[httpx]>=4.39.0``, so no ``--with logfire`` overlay is
needed.  The logfire console sink is routed to stderr so ``--json`` output on
stdout stays machine-readable.  Disable tracing with ``--no-logfire`` (or
``LOGFIRE_DISABLED=1``); this is also the fallback when logfire is not
installed, e.g. the ``--no-project`` variant without ``--with logfire``::

    PYTHONPATH=src uv run --with "pydantic-ai[typesafe]>=2.45" \\
        python scripts/jev_native_prototype.py "fruity Ethiopian coffee under £25" --json --no-logfire

NOTE: this script must NOT import ``kissaten.ai.search_agent`` (it imports
``pydantic_ai.models.gemini``, removed in 2.x).  ``jev_common`` loads the
schema module standalone when the ``kissaten`` package import chain breaks.

Requires ``TYPESAFE_API_KEY`` in ``.env`` (loaded via python-dotenv).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from typing import Any

import duckdb
from dotenv import load_dotenv

# Shared composition logic and the single Jev adapter implementation live in
# the installed package.
from kissaten.ai.jev import common as jev_common
from kissaten.ai.jev.agent import (
    MODEL_PIN_ALT,
    MODEL_PIN_DEFAULT,
    REGEX_MODEL_DEFAULT,
    _logfire_error,
    _logfire_info,
    _non_default_params,
    _optional_span,
    run_native,
    set_logfire_enabled,
)
from kissaten.ai.jev.common import (
    GOLDEN_SET,
    TRACKED_FIELDS,
    field_matches,
    filter_context_by_query,
    print_benchmark_results,
)

load_dotenv()


# ---------------------------------------------------------------------------
# Logfire tracing (optional — never breaks --json output)
# ---------------------------------------------------------------------------
# ``_setup_logfire`` parses ``--no-logfire`` / ``LOGFIRE_DISABLED`` and owns the
# ``logfire.configure`` / ``instrument_pydantic_ai`` calls; the adapter module
# (``kissaten.ai.jev.agent``) owns the manual span/info/error helpers and their
# enable flag.  logfire is imported lazily so the script still runs when it is
# absent (e.g. the fully-isolated `--no-project` variant without
# `--with logfire`).  When enabled, the logfire console sink is routed to
# stderr so the JSON result on stdout stays machine-readable.

try:
    import logfire as _logfire
except ImportError:  # pragma: no cover - exercised in the --no-project variant
    _logfire = None


def _setup_logfire(no_logfire: bool) -> bool:
    """Configure logfire and enable tracing; returns True when tracing is active.

    Honors ``--no-logfire`` and ``LOGFIRE_DISABLED=1``.  Missing logfire or a
    logfire/pydantic-ai mismatch only warns on stderr and falls back to an
    untraced run — the pipeline itself never crashes because of telemetry.
    """
    if no_logfire or os.environ.get("LOGFIRE_DISABLED") == "1":
        set_logfire_enabled(False)
        return False
    if _logfire is None:
        print(
            "warning: logfire is not installed; continuing without tracing "
            "(install it, or pass --no-logfire to silence this warning)",
            file=sys.stderr,
        )
        set_logfire_enabled(False)
        return False
    try:
        console_options = getattr(_logfire, "ConsoleOptions", None)
        console = console_options(output=sys.stderr, show_project_link=True) if console_options else False
        _logfire.configure(scrubbing=False, console=console)
    except Exception as exc:  # noqa: BLE001
        print(f"warning: logfire.configure failed ({exc}); continuing without tracing", file=sys.stderr)
        set_logfire_enabled(False)
        return False
    try:
        # pydantic-ai 2.x still exports InstrumentationSettings, so the
        # project-pinned logfire (>= 4.39.0, itself required by pydantic-ai
        # 2.x) auto-instruments out of the box.  Older/newer combos degrade
        # gracefully to manual spans only.
        _logfire.instrument_pydantic_ai()
    except (ImportError, AttributeError) as exc:
        print(
            "warning: logfire.instrument_pydantic_ai() is unavailable with this "
            f"logfire/pydantic-ai combination ({type(exc).__name__}: {exc}); "
            "continuing with manual spans only",
            file=sys.stderr,
        )
    set_logfire_enabled(True)
    return True


# ---------------------------------------------------------------------------
# Web inspector (--serve): minimal FastAPI + PicoCSS page
# ---------------------------------------------------------------------------
# The TypeSafe adapter hides the HTTP payload, so the inspector captures it at
# the transport layer: ``TypeSafeProvider(http_client=...)`` is given a custom
# ``httpx2.AsyncClient`` whose transport (a subclass of
# ``httpx2.AsyncHTTPTransport``) records every request/response body it
# carries.  A fresh (transport, client) pair is created per request so
# concurrent calls never clobber each other's capture.  ``httpx2``, fastapi and
# uvicorn are imported only inside the serve path — normal CLI/benchmark runs
# keep their exact import set.

_SERVE_HOST_DEFAULT = "127.0.0.1"
_SERVE_PORT_DEFAULT = 8765


def _new_capture_client(timeout: float = 120.0) -> tuple[Any, Any]:
    """Return (transport, httpx2.AsyncClient) where the transport records the wire."""

    import httpx2

    class _CaptureTransport(httpx2.AsyncHTTPTransport):
        """Wraps the real transport and records (url, request_body, response_body, duration_ms)."""

        def __init__(self) -> None:
            super().__init__()
            self.calls: list[dict[str, Any]] = []

        async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
            start = time.monotonic()
            response = await super().handle_async_request(request)
            await response.aread()
            duration_ms = (time.monotonic() - start) * 1000
            self.calls.append(
                {
                    "url": str(request.url),
                    "request_body": request.content.decode("utf-8", errors="replace") if request.content else None,
                    "response_body": response.content.decode("utf-8", errors="replace") if response.content else None,
                    "duration_ms": round(duration_ms, 1),
                }
            )
            return response

    transport = _CaptureTransport()
    client = httpx2.AsyncClient(transport=transport, timeout=timeout)
    return transport, client


def _parse_question_table(request: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse ``request.questions`` into ``{id, type, instructions, criteria/options}`` rows."""
    rows: list[dict[str, Any]] = []
    for qid, q in (request.get("questions") or {}).items():
        if not isinstance(q, dict):
            continue
        instructions = q.get("instructions")
        row: dict[str, Any] = {
            "id": qid,
            "type": q.get("type"),
            "instructions": instructions if isinstance(instructions, str | dict) else str(instructions),
        }
        if "criteria" in q:
            row["criteria"] = q["criteria"]
        if "options" in q:
            row["options"] = q["options"]
        rows.append(row)
    return rows


def _parse_body(body: str | None) -> Any:
    """Parse a captured body as JSON; keep the raw string when it is not JSON.

    Streaming Gemini responses may be SSE text, so a parse failure keeps the
    raw bytes-as-string for display rather than dropping the body.
    """
    if not body:
        return None
    try:
        return json.loads(body)
    except ValueError:
        return body


def _call_kind(url: str) -> str:
    """Classify a captured call by URL: 'jev', 'gemini', or 'other'."""
    if "systemone" in url:
        return "jev"
    if "generativelanguage" in url:
        return "gemini"
    return "other"


def _extract_capture(transport: Any | None) -> dict[str, Any]:
    """Pull every recorded wire call out of the transport.

    Returns a ``calls`` list with one entry per recorded HTTP call, in order,
    each carrying ``kind`` (``jev`` / ``gemini`` / ``other``), ``url``,
    ``duration_ms`` and parsed-or-raw ``request``/``response``.  The legacy
    ``request``/``response``/``question_table``/``request_url`` keys are kept
    for the Jev sections: they prefer the last ``/v1/systemone`` call (and
    only fall back to a non-Google call, then any call) so the Jev view keeps
    showing Jev even when the SAME capture client also carried the Gemini
    ``generateContent`` request.  On a retry the request body is identical,
    so the last matching call is the one that produced the response the SDK
    consumed.
    """
    calls = getattr(transport, "calls", None) if transport is not None else None
    if not calls:
        return {
            "request": None,
            "response": None,
            "question_table": [],
            "request_url": None,
            "calls": [],
        }
    captured = [
        {
            "kind": _call_kind(str(c.get("url", ""))),
            "url": str(c.get("url", "")),
            "duration_ms": c.get("duration_ms"),
            "request": _parse_body(c.get("request_body")),
            "response": _parse_body(c.get("response_body")),
        }
        for c in calls
    ]
    systemone = [c for c in calls if "systemone" in str(c.get("url", ""))]
    if systemone:
        call = systemone[-1]
    else:
        non_google = [c for c in calls if "generativelanguage" not in str(c.get("url", ""))]
        call = (non_google or calls)[-1]
    request = _parse_body(call.get("request_body"))
    response = _parse_body(call.get("response_body"))
    return {
        "request": request,
        "response": response,
        "question_table": _parse_question_table(request) if isinstance(request, dict) else [],
        "request_url": call["url"],
        "calls": captured,
    }


async def run_for_demo(
    query: str,
    context: Any,
    model_pin: str = MODEL_PIN_DEFAULT,
    top_notes: int = 8,
    use_regex_llm: bool = True,
    regex_model: str = REGEX_MODEL_DEFAULT,
) -> dict[str, Any]:
    """Run one query for the web inspector; returns the full inspect payload.

    Reuses the exact same pipeline as the CLI paths — ``filter_context_by_query``,
    ``build_native_model``, ``run_native``, ``compose_search_params``,
    ``generate_search_url`` — nothing is duplicated.  The agent + capturing
    client are constructed here, inside the caller's event loop (pydantic-ai
    2.x: one loop per client).  Logfire spans are emitted like the CLI path.
    """
    filtered = filter_context_by_query(query, context)
    with _optional_span(
        "jev.translate",
        query=query,
        backend="native",
        model=model_pin,
        mode="serve",
        regex_model=regex_model if use_regex_llm else None,
    ) as span:
        transport: Any | None = None
        client: Any | None = None
        try:
            transport, client = _new_capture_client()
            result = await run_native(
                query,
                filtered,
                context,
                model_pin,
                top_notes,
                http_client=client,
                use_regex_llm=use_regex_llm,
                regex_model=regex_model,
            )
        except Exception as exc:  # noqa: BLE001
            if span is not None:
                span.set_attribute("success", False)
                _logfire_error("jev.translate failed", query=query, error=str(exc), error_type=type(exc).__name__)
            return {"query": query, "error": str(exc), **_extract_capture(transport)}
        finally:
            if client is not None:
                await client.aclose()

        usage = _usage_dict(result["usage"])
        capture = _extract_capture(transport)
        if span is not None:
            span.set_attribute("model_name", result["model_name"])
            span.set_attribute("input_tokens", usage.get("input_tokens"))
            span.set_attribute("output_tokens", usage.get("output_tokens"))
            span.set_attribute("processing_time_ms", round(result["latency_ms"], 1))
            span.set_attribute("success", True)
            span.set_attribute("filtered_candidates", sum(len(v or []) for v in filtered.values()))
            span.set_attribute("search_url", result["url"])
            _logfire_info("jev.result", **_non_default_params(result["params"]))
        return {
            "query": query,
            **capture,
            "search_params": result["params"].model_dump(),
            "search_url": result["url"],
            "resolved_model": result["model_name"],
            "regex_fields": result["regex_fields"],
            "needs_tasting_notes": result["needs_tasting_notes"],
            "regex_llm_called": result["regex_llm_called"],
            "needs_origin": result["needs_origin"],
            "needs_region": result["needs_region"],
            "needs_variety": result["needs_variety"],
            "needs_farm": result["needs_farm"],
            "regex_model": regex_model if use_regex_llm else None,
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "processing_time_ms": round(result["latency_ms"], 1),
        }


_INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
<title>Jev Native Inspector</title>
<style>
  pre { max-height: 22rem; overflow: auto; }
  code.block { white-space: pre-wrap; }
</style>
</head>
<body>
<main class="container">
  <h1>Jev Native Inspector</h1>
  <p>
    Enter a query and inspect EVERY model call the translation makes — the Jev
    <code>/v1/systemone</code> request and (when the regex LLM is enabled) the
    Gemini <code>generateContent</code> request — each with its raw request and
    raw response, plus per-call latency and the composed
    <code>SearchParameters</code> + <code>search_url</code>.
  </p>
  <form id="translate-form">
    <label for="query">Query</label>
    <textarea id="query" name="query" rows="3" placeholder="e.g. fruity Ethiopian coffee under £25"></textarea>
    <button type="submit">Translate</button>
  </form>
  <details>
    <summary>Presets (golden set)</summary>
    <div id="presets"></div>
  </details>
  <section>
    <h2>Prompt structure (questions sent to Jev)</h2>
    <p id="meta-line"></p>
    <table id="question-table">
      <thead>
        <tr><th>id</th><th>type</th><th>instructions</th><th>criteria / options</th></tr>
      </thead>
      <tbody></tbody>
    </table>
  </section>
  <section>
    <h2>LLM calls</h2>
    <div id="llm-calls">(run a query)</div>
  </section>
  <section>
    <h2>Composed search parameters</h2>
    <pre id="search-params">(run a query)</pre>
  </section>
  <section>
    <h2>REGEX LLM (Gemini)</h2>
    <p id="regex-line">(run a query)</p>
    <pre id="regex-fields">(run a query)</pre>
  </section>
</main>
<script>
  async function translate() {
    const query = document.getElementById("query").value;
    const resp = await fetch("/api/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query }),
    });
    render(await resp.json());
  }

  function instructionsText(instructions) {
    if (typeof instructions === "string") return instructions;
    if (!instructions) return "";
    const parts = [];
    if (instructions.question) parts.push(instructions.question);
    if (instructions.field) parts.push("field: " + instructions.field);
    if (instructions.goal) parts.push("goal: " + instructions.goal);
    if (instructions.background) {
      parts.push(
        '<details><summary>background</summary><code class="block">'
        + instructions.background.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        + "</code></details>"
      );
    }
    return parts.join("<br>");
  }

  function criteriaCell(criteria, options) {
    const map = criteria || (options ? { options: options } : null);
    if (!map) return document.createTextNode("-");
    const keys = Object.keys(map);
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = keys.length + " options";
    const code = document.createElement("code");
    code.className = "block";
    code.textContent = JSON.stringify(map, null, 1);
    details.appendChild(summary);
    details.appendChild(code);
    return details;
  }

  function formatValue(value) {
    if (value === null || value === undefined) return "(none)";
    if (typeof value === "object") return JSON.stringify(value, null, 2);
    return String(value);
  }

  function labelledBlock(label, value) {
    const wrapper = document.createElement("div");
    const labelEl = document.createElement("strong");
    labelEl.textContent = label;
    const pre = document.createElement("pre");
    pre.textContent = formatValue(value);
    wrapper.appendChild(labelEl);
    wrapper.appendChild(pre);
    return wrapper;
  }

  function renderLlmCalls(calls) {
    const container = document.getElementById("llm-calls");
    container.innerHTML = "";
    if (!calls || calls.length === 0) {
      container.textContent = "(no calls captured)";
      return;
    }
    for (const call of calls) {
      const details = document.createElement("details");
      details.open = call.kind === "jev";
      const summary = document.createElement("summary");
      const badge = document.createElement("code");
      badge.textContent = "[" + (call.kind || "other") + "]";
      summary.appendChild(badge);
      summary.appendChild(document.createTextNode("  " + (call.url || "(no url)")));
      if (call.duration_ms != null) {
        summary.appendChild(document.createTextNode("  \\u00b7  " + Number(call.duration_ms).toFixed(1) + " ms"));
      }
      details.appendChild(summary);
      details.appendChild(labelledBlock("request", call.request));
      details.appendChild(labelledBlock("response", call.response));
      container.appendChild(details);
    }
  }

  function render(data) {
    renderLlmCalls(data.calls || []);
    document.getElementById("search-params").textContent =
      "origin gate: " + (data.needs_origin ? "origin named" : "no origin named") +
      "\\nregion gate: " + (data.needs_region ? "region named" : "no region named") +
      "\\nvariety gate: " + (data.needs_variety ? "variety named" : "no variety named") +
      "\\nfarm gate: " + (data.needs_farm ? "farm named" : "no farm named") +
      "\\n" + "search_url: " + (data.search_url ?? "(none)") +
      "\\n\\n" + JSON.stringify(data.search_params, null, 2);
    const regexFields = data.regex_fields || {};
    document.getElementById("regex-fields").textContent = JSON.stringify(regexFields, null, 2);
    if (data.error) {
      document.getElementById("meta-line").textContent = "ERROR: " + data.error;
      document.getElementById("regex-line").textContent = "ERROR: " + data.error;
    } else {
      document.getElementById("meta-line").textContent =
        "resolved model: " + data.resolved_model +
        "  \\u00b7  input tokens: " + data.input_tokens +
        "  \\u00b7  output tokens: " + data.output_tokens +
        "  \\u00b7  processing time: " + data.processing_time_ms + " ms" +
        (data.request_url ? "  \\u00b7  " + data.request_url : "");
      const gateText = data.needs_tasting_notes
        ? "Jev gate: taste intent"
        : "Jev gate: no taste intent";
      if (!data.regex_model) {
        document.getElementById("regex-line").textContent = "regex LLM disabled (--no-regex-llm)";
      } else if (!data.regex_llm_called) {
        document.getElementById("regex-line").textContent = gateText + " \\u2014 Gemini skipped";
      } else if (regexFields.tasting_notes_search) {
        document.getElementById("regex-line").textContent =
          gateText + " \\u2014 Gemini called \\u00b7 model: " + data.regex_model +
          " \\u00b7 tasting_notes_search='" + regexFields.tasting_notes_search +
          "' \\u2014 overrode the Jev candidate path";
      } else {
        document.getElementById("regex-line").textContent =
          gateText + " \\u2014 Gemini called \\u00b7 model: " + data.regex_model +
          " \\u00b7 no flavour preference detected (null) \\u2014 Jev candidates kept";
      }
    }
    const tbody = document.querySelector("#question-table tbody");
    tbody.innerHTML = "";
    for (const q of data.question_table || []) {
      const tr = document.createElement("tr");
      const tdId = document.createElement("td");
      tdId.textContent = q.id;
      const tdType = document.createElement("td");
      tdType.textContent = q.type;
      const tdInstr = document.createElement("td");
      tdInstr.innerHTML = instructionsText(q.instructions);
      const tdCrit = document.createElement("td");
      tdCrit.appendChild(criteriaCell(q.criteria, q.options));
      tr.appendChild(tdId);
      tr.appendChild(tdType);
      tr.appendChild(tdInstr);
      tr.appendChild(tdCrit);
      tbody.appendChild(tr);
    }
  }

  document.getElementById("translate-form").addEventListener("submit", (ev) => {
    ev.preventDefault();
    translate();
  });

  document.getElementById("query").value = "fruity Ethiopian coffee under £25";

  fetch("/api/presets")
    .then((r) => r.json())
    .then((data) => {
      const div = document.getElementById("presets");
      for (const q of data.presets) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "secondary outline small";
        btn.textContent = q;
        btn.addEventListener("click", () => {
          document.getElementById("query").value = q;
          translate();
        });
        div.appendChild(btn);
      }
    });
</script>
</body>
</html>
"""


def _patch_starlette_compat() -> None:
    """Guard against the fastapi/starlette version clash the pydantic-ai overlay causes.

    The project pins ``fastapi[all]>=0.100.0`` (no upper bound), so ``uv run
    --with pydantic-ai[typesafe]>=2.45`` keeps the base env's fastapi while the
    overlay's ``starlette>=1.3.1`` requirement bumps starlette to 1.x — and
    fastapi 0.116.x passes ``on_startup``/``on_shutdown`` to
    ``starlette.routing.Router`` (removed in 1.x) and never sets the
    ``max_body_size`` starlette 1.x's middleware builder reads.  Only when the
    mismatch is present do we shim those two spots; a compatible
    fastapi/starlette pair (or ``--with fastapi`` resolving 0.140+) is untouched.
    """
    import inspect

    import starlette.applications
    import starlette.routing

    if "on_startup" in inspect.signature(starlette.routing.Router.__init__).parameters:
        return  # starlette < 1.0: no clash, nothing to do

    original_router_init = starlette.routing.Router.__init__

    def _compat_router_init(
        self,
        routes=None,
        redirect_slashes=True,
        default=None,
        on_startup=None,
        on_shutdown=None,
        lifespan=None,
        **kwargs: Any,
    ) -> None:
        # fastapi's APIRouter merges on_startup/on_shutdown into its own
        # lifespan, so starlette only needs to accept (and drop) them here.
        original_router_init(
            self,
            routes=routes,
            redirect_slashes=redirect_slashes,
            default=default,
            lifespan=lifespan,
            **kwargs,
        )

    starlette.routing.Router.__init__ = _compat_router_init

    original_build = starlette.applications.Starlette.build_middleware_stack

    def _compat_build(self: Any) -> Any:
        if not hasattr(self, "max_body_size"):
            self.max_body_size = None
        return original_build(self)

    starlette.applications.Starlette.build_middleware_stack = _compat_build


def _serve(args: argparse.Namespace, context: Any) -> int:
    """Build the FastAPI app and serve it (imports fastapi/uvicorn only here)."""
    import uvicorn
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse

    _patch_starlette_compat()

    app = FastAPI(title="Jev Native Inspector")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return _INDEX_HTML

    @app.get("/api/presets")
    async def presets() -> dict[str, list[str]]:
        return {"presets": [example["query"] for example in GOLDEN_SET]}

    @app.post("/api/translate")
    async def api_translate(payload: dict) -> dict[str, Any]:
        # Note: a plain ``dict`` body param (not ``Request``) — the
        # fastapi/starlette compat shim means older fastapi misclassifies the
        # ``Request`` annotation as a query parameter, and the dict form is
        # also simpler.
        query = (payload or {}).get("query")
        if not query or not isinstance(query, str):
            raise HTTPException(status_code=400, detail="missing string field 'query'")
        return await run_for_demo(
            query,
            context,
            args.pin,
            args.top_notes,
            use_regex_llm=not args.no_regex_llm,
            regex_model=args.regex_model,
        )

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jev_native_prototype",
        description="TypeSafe Jev smart-search translator — native pydantic-ai adapter (Kissaten).",
    )
    parser.add_argument("query", nargs="?", default=None, help="Natural-language coffee search query")
    parser.add_argument(
        "--db-path", default="data/kissaten.duckdb", help="Read-only DuckDB path (default: data/kissaten.duckdb)"
    )
    parser.add_argument("--benchmark", action="store_true", help="Run the golden-set benchmark")
    parser.add_argument("--limit", type=int, default=None, help="Cap benchmark at the first N queries")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    parser.add_argument("--top-notes", type=int, default=8, help="Number of tasting-note candidates (default: 8)")
    parser.add_argument(
        "--pin",
        default=MODEL_PIN_DEFAULT,
        help=f"TypeSafe Jev model pin (default: {MODEL_PIN_DEFAULT}; alt: {MODEL_PIN_ALT})",
    )
    parser.add_argument(
        "--no-regex-llm",
        action="store_true",
        help="Disable the Gemini regex-field LLM; tasting_notes_search falls back to Jev note candidates",
    )
    parser.add_argument(
        "--regex-model",
        default=REGEX_MODEL_DEFAULT,
        help=f"Gemini model for the regex fields (default: {REGEX_MODEL_DEFAULT})",
    )
    parser.add_argument(
        "--no-logfire",
        action="store_true",
        help="Disable Logfire tracing for this run (also honored via LOGFIRE_DISABLED=1)",
    )
    parser.add_argument("--serve", action="store_true", help="Serve the web inspector (FastAPI + PicoCSS)")
    parser.add_argument("--host", default=_SERVE_HOST_DEFAULT, help=f"Serve bind host (default: {_SERVE_HOST_DEFAULT})")
    parser.add_argument(
        "--port",
        type=int,
        default=_SERVE_PORT_DEFAULT,
        help=f"Serve bind port (default: {_SERVE_PORT_DEFAULT})",
    )
    return parser


def _usage_dict(usage: Any) -> dict[str, Any]:
    """Normalise result.usage (pydantic-ai 2.x property) into a plain dict."""
    if usage is None:
        return {}
    return {
        "requests": getattr(usage, "requests", None),
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
    }


async def _run_single(query: str, context: Any, args: argparse.Namespace) -> int:
    filtered = filter_context_by_query(query, context)
    with _optional_span(
        "jev.translate",
        query=query,
        backend="native",
        model=args.pin,
    ) as span:
        try:
            result = await run_native(
                query,
                filtered,
                context,
                args.pin,
                args.top_notes,
                use_regex_llm=not args.no_regex_llm,
                regex_model=args.regex_model,
            )
        except Exception as exc:  # noqa: BLE001
            if span is not None:
                span.set_attribute("success", False)
                _logfire_error(
                    "jev.translate failed",
                    query=query,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
            print(f"native Jev pipeline failed: {exc}")
            return 1
        params = result["params"]
        usage = _usage_dict(result["usage"])

        if span is not None:
            span.set_attribute("model_name", result["model_name"])
            span.set_attribute("input_tokens", usage.get("input_tokens"))
            span.set_attribute("output_tokens", usage.get("output_tokens"))
            span.set_attribute("processing_time_ms", round(result["latency_ms"], 1))
            span.set_attribute("success", True)
            span.set_attribute(
                "filtered_candidates", sum(len(v or []) for v in filtered.values())
            )
            span.set_attribute("search_url", result["url"])
            _logfire_info("jev.result", **_non_default_params(params))
            confidences = (result["provider_details"] or {}).get("confidence")
            if confidences:
                _logfire_info("jev.confidences", **confidences)

        if args.json:
            out: dict[str, Any] = {
                "query": query,
                "success": True,
                "backend": "native",
                "model": result["model_name"],
                "usage": usage,
                "provider_details": result["provider_details"],
                "search_params": params.model_dump(),
                "search_url": result["url"],
                "regex_fields": result["regex_fields"],
                "needs_tasting_notes": result["needs_tasting_notes"],
                "regex_llm_called": result["regex_llm_called"],
                "needs_origin": result["needs_origin"],
                "needs_region": result["needs_region"],
                "needs_variety": result["needs_variety"],
                "needs_farm": result["needs_farm"],
                "processing_time_ms": round(result["latency_ms"], 1),
                "answers": result["answers"],
            }
            print(json.dumps(out, indent=2, default=str))
        else:
            print(f"query: {query}")
            print(
                f"model: {result['model_name']}  usage: {usage}  "
                f"latency: {result['latency_ms']:.0f} ms"
            )
            print(f"regex_fields: {json.dumps(result['regex_fields'], default=str)}")
            print(f"search_params: {json.dumps(params.model_dump(), default=str)}")
            print(f"search_url: {result['url']}")
            conf = result["provider_details"].get("confidence")
            if conf:
                print(f"provider confidence: {json.dumps(conf, default=str)}")
        return 0


async def _run_benchmark(context: Any, args: argparse.Namespace) -> int:
    golden = GOLDEN_SET[: args.limit] if args.limit else GOLDEN_SET
    valid_codes = {c.country_code for c in context.available_countries}
    results: list[dict[str, Any]] = []
    aggregate: dict[str, list[int]] = {f: [0, 0] for f in TRACKED_FIELDS}
    total_input_tokens = 0
    total_output_tokens = 0
    latencies: list[float] = []
    wall_start = time.monotonic()

    quiet = bool(args.json)
    if not quiet:
        print(f"running {len(golden)} golden queries against Jev ({args.pin}, native adapter)...")
    for i, example in enumerate(golden, 1):
        query = example["query"]
        expected = example["expected"]
        filtered = filter_context_by_query(query, context)
        try:
            result = await run_native(
                query,
                filtered,
                context,
                args.pin,
                args.top_notes,
                use_regex_llm=not args.no_regex_llm,
                regex_model=args.regex_model,
            )
        except Exception as exc:  # noqa: BLE001
            if not quiet:
                print(f"#{i:02d} {query!r} FAILED: {exc}")
            results.append(
                {
                    "query": query,
                    "error": str(exc),
                    "matched": 0,
                    "fields": len(expected),
                    "diffs": [],
                    "latency_ms": 0.0,
                    "input_tokens": 0,
                }
            )
            continue
        params = result["params"]
        usage = _usage_dict(result["usage"])
        total_input_tokens += int(usage.get("input_tokens") or 0)
        total_output_tokens += int(usage.get("output_tokens") or 0)
        latencies.append(result["latency_ms"])

        diffs = []
        matched = 0
        for field, exp in expected.items():
            if field not in TRACKED_FIELDS:
                continue
            got = getattr(params, field)
            if field == "origin" and isinstance(exp, list):
                exp = [c for c in exp if c in valid_codes]
            ok = field_matches(field, got, exp)
            aggregate[field][1] += 1
            if ok:
                matched += 1
                aggregate[field][0] += 1
            else:
                diffs.append((field, got, exp))
        results.append(
            {
                "query": query,
                "matched": matched,
                "fields": len([f for f in expected if f in TRACKED_FIELDS]),
                "diffs": diffs,
                "latency_ms": result["latency_ms"],
                "input_tokens": int(usage.get("input_tokens") or 0),
                "regex_fields": result["regex_fields"],
            }
        )
        if not quiet:
            print(
                f"#{i:02d} {query[:60]!r} matched {matched}/{len([f for f in expected if f in TRACKED_FIELDS])} "
                f"({result['latency_ms']:.0f} ms)"
            )

    total_matched = sum(v[0] for v in aggregate.values())
    total_fields = sum(v[1] for v in aggregate.values())
    timing = {
        "queries": len(results),
        "matched": total_matched,
        "fields": total_fields,
        "avg_latency_ms": (sum(latencies) / len(latencies)) if latencies else 0.0,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "wall_sec": time.monotonic() - wall_start,
    }
    if args.json:
        payload = {
            "benchmark": True,
            "backend": "native",
            "results": results,
            "aggregate": {f: {"matched": v[0], "total": v[1]} for f, v in aggregate.items()},
            "timing": timing,
        }
        print(json.dumps(payload, indent=2, default=str))
    else:
        print_benchmark_results(results, aggregate, timing, TRACKED_FIELDS)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.query and not args.benchmark and not args.serve:
        parser.error("a positional `query` (or --benchmark, or --serve) is required")

    _setup_logfire(args.no_logfire)

    conn = duckdb.connect(args.db_path, read_only=True)
    try:
        context = jev_common.build_search_context(conn)
        if args.serve:
            return _serve(args, context)
        if args.benchmark:
            return asyncio.run(_run_benchmark(context, args))
        return asyncio.run(_run_single(args.query or "", context, args))
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
