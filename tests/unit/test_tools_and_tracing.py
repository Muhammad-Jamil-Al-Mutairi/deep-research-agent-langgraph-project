"""Agent tools never raise; tracing totals; loop-guard middleware; no secrets in the repo."""

import asyncio
import re
from pathlib import Path
from types import SimpleNamespace

from langchain_core.messages import ToolMessage

from hermes.agents.common import loop_guard_middleware
from hermes.observability.tracing import (
    current_span,
    langfuse_context,
    observe,
    span_totals,
)
from hermes.tools.research.tools import (
    get_component,
    search_components,
    size_battery_for_runtime,
    usd_to_sar,
)
from hermes.tools.verification.loop_detector import LoopDetector

ROOT = Path(__file__).resolve().parents[2]


def test_tools_return_messages_for_bad_input():
    assert search_components.invoke({"category": "motor", "filters": ["notes = x"]}).startswith("Filter error")
    assert "No 'teleporter'" in search_components.invoke({"category": "teleporter"})
    assert "Unknown component_id" in get_component.invoke({"component_id": "FAKE-1"})
    assert "Cannot size battery" in size_battery_for_runtime.invoke(
        {"runtime_h": 2, "average_power_w": 5, "voltage_v": 0, "usable_fraction": 0.8})


def test_tools_return_specs_with_citations():
    out = search_components.invoke({"category": "battery", "filters": ["capacity_mah >= 6000"]})
    assert "OVO-3S-6000-80C" in out and "SAR" in out
    assert "pololu.com/product/4752" in get_component.invoke({"component_id": "POL-4752"})
    assert usd_to_sar.invoke({"amount_usd": 100}) == "100.00 USD = 375.00 SAR"


def test_span_totals_sum_children():
    @observe(name="child", as_type="agent")
    def child(cost):
        langfuse_context.update_current_observation(usage={"total_tokens": 100}, metadata={"cost_usd": cost})

    captured = {}

    @observe(name="root")
    def root():
        child(0.01)
        child(0.02)
        captured["totals"] = span_totals(current_span())

    root()
    assert captured["totals"] == {"total_tokens": 200, "cost_usd": 0.03, "agent_runs": 2}


def test_loop_guard_blocks_third_identical_call():
    detector, seen = LoopDetector(), []
    guard = loop_guard_middleware(detector, on_loop=lambda tool, msg: seen.append(tool))
    executed = []

    async def handler(request):
        executed.append(request.tool_call["name"])
        return ToolMessage(content="ok", tool_call_id=request.tool_call["id"])

    async def call():
        req = SimpleNamespace(tool_call={"name": "search_components", "args": {"category": "motor"}, "id": "1"})
        return await guard.awrap_tool_call(req, handler)

    results = [asyncio.run(call()) for _ in range(3)]
    assert len(executed) == 2  # the third call was NOT executed
    assert "LOOP DETECTED" in results[2].content and seen == ["search_components"]


def test_no_api_keys_committed():
    pattern = re.compile(r"sk-or-v1-[0-9a-f]{20,}|sk-[A-Za-z0-9]{32,}")
    for path in ROOT.rglob("*"):
        if any(part in {".venv", ".git", ".hermes", "__pycache__"} for part in path.parts) or not path.is_file():
            continue
        if path.name == ".env" or path.suffix not in {".py", ".md", ".ipynb", ".toml", ".csv", ".example", ".txt"}:
            continue
        assert not pattern.search(path.read_text(encoding="utf-8", errors="ignore")), path


def test_converge_guard_strips_tools_when_budget_is_spent():
    from langchain.agents.middleware import ModelRequest
    from langchain_core.messages import AIMessage, HumanMessage

    from hermes.agents.common import converge_middleware
    from hermes.agents.scripted import ScriptedChatModel

    reasons, seen = [], {}
    guard = converge_middleware(finalize_after=10, on_converge=reasons.append)

    async def handler(request):
        seen["tools"] = list(request.tools)
        seen["last"] = request.messages[-1].content
        return "ok"

    model = ScriptedChatModel(responses=[AIMessage(content="x")])
    healthy = ModelRequest(model=model, messages=[HumanMessage("go")], tools=[search_components])
    asyncio.run(guard.awrap_model_call(healthy, handler))
    assert seen["tools"] == [search_components] and not reasons  # untouched while within budget

    blocked = ToolMessage(content="Tool call limit exceeded. Do not call 'search_datasheets' again.", tool_call_id="1")
    stuck = ModelRequest(model=model, messages=[HumanMessage("go"), AIMessage(content=""), blocked],
                         tools=[search_components])
    asyncio.run(guard.awrap_model_call(stuck, handler))
    assert seen["tools"] == [] and "Submit your final structured answer" in seen["last"]
    assert reasons == ["tool budget exhausted / loop detected"]


def test_provider_errors_are_fatal_and_transient_errors_are_retried():
    from hermes.agents.common import ProviderError, as_provider_error, is_transient

    class Status(Exception):
        def __init__(self, code):
            super().__init__(f"Error code: {code}")
            self.status_code = code

    assert is_transient(Status(429)) and is_transient(Status(503)) and is_transient(ConnectionError("reset"))
    assert not is_transient(Status(402)) and not is_transient(Status(401))
    assert isinstance(as_provider_error(Status(402)), ProviderError)
    assert isinstance(as_provider_error(RuntimeError("This request requires more credits")), ProviderError)
    assert as_provider_error(Status(500)) is None


def test_output_loop_guard_corrects_then_stops_identical_rejected_answers():
    import pytest
    from langchain.agents.middleware import ModelRequest
    from langchain_core.messages import AIMessage, HumanMessage

    from hermes.agents.common import AgentOutputError, output_loop_middleware
    from hermes.agents.scripted import ScriptedChatModel

    loops, seen = [], {}
    guard = output_loop_middleware(stop_after=3, on_loop=loops.append)
    error = "Error: Failed to parse structured output for tool 'MissionDraft': max_speed_mps Input should be greater than 0"

    def attempt(i, speed):
        call = {"name": "MissionDraft", "args": {"max_speed_mps": speed}, "id": f"c{i}", "type": "tool_call"}
        return [AIMessage(content="", tool_calls=[call]), ToolMessage(content=error, tool_call_id=f"c{i}")]

    async def handler(request):
        seen["last"] = request.messages[-1].content
        return "ok"

    model = ScriptedChatModel(responses=[AIMessage(content="x")])
    run = lambda msgs: asyncio.run(guard.awrap_model_call(ModelRequest(model=model, messages=msgs, tools=[]), handler))

    run([HumanMessage("go"), *attempt(1, 0), *attempt(2, 0.5)])  # different answers: not a loop
    assert not loops and seen["last"] == error
    run([HumanMessage("go"), *attempt(1, 0), *attempt(2, 0)])  # identical rejected answer: corrective message
    assert "LOOP DETECTED" in seen["last"] and "max_speed_mps" in seen["last"] and len(loops) == 1
    with pytest.raises(AgentOutputError, match="structured-output loop"):  # third identical: stop early
        run([HumanMessage("go"), *attempt(1, 0), *attempt(2, 0), *attempt(3, 0)])
