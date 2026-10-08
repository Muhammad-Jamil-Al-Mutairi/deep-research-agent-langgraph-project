"""Shared agent plumbing: the LLM, the given ``run_agent`` runner, and loop-guard middleware."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import wrap_model_call, wrap_tool_call
from langchain_core.messages import HumanMessage, ToolMessage
from pydantic import BaseModel, ValidationError

from hermes.config import DEFAULT_MODEL, OPENROUTER_BASE_URL
from hermes.observability.tracing import langfuse_context, observe
from hermes.tools.verification.loop_detector import LoopDetector


class AgentOutputError(RuntimeError):
    """The agent finished without a valid structured answer."""


class ProviderError(RuntimeError):
    """The LLM provider refused the request (bad key, no credits, forbidden). Retrying cannot help."""


_FATAL_STATUS = {401, 402, 403}


def is_transient(exc: Exception) -> bool:
    """Retry rate limits, 5xx and network errors; never retry auth/credit errors."""
    status = getattr(exc, "status_code", None)
    if status is not None:
        return status == 429 or status >= 500
    return not isinstance(exc, (ValueError, TypeError, AgentOutputError))


def as_provider_error(exc: Exception) -> ProviderError | None:
    """Classify an exception as a fatal provider error (out of credits, invalid key)."""
    status = getattr(exc, "status_code", None)
    text = str(exc)
    if status in _FATAL_STATUS or "requires more credits" in text or "Insufficient credits" in text:
        return ProviderError(f"LLM provider refused the request (HTTP {status or '?'}): {text[:160]}")
    return None


def make_llm(model_name: str = DEFAULT_MODEL, api_key: str | None = None, temperature: float = 0.2,
             max_tokens: int = 8192):
    """ChatOpenAI pointed at OpenRouter (same setup as the SDAIA starter notebook)."""
    from langchain_openai import ChatOpenAI

    key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise ValueError("Set OPENROUTER_API_KEY (Colab Secrets, .env, or environment variable)")
    # Structured answers are short; capping max_tokens also stops OpenRouter reserving the model's full
    # output window against the account balance on every call.
    return ChatOpenAI(model=model_name, base_url=OPENROUTER_BASE_URL, api_key=key, temperature=temperature,
                      max_tokens=max_tokens)


# ---- GIVEN by the SDAIA starter (section 4), extended -----------------------------------
# HERMES change: the model name is a parameter instead of a notebook global, and the result
# additionally carries `structured_response` and `cost_usd` (marked "HERMES" below).
@observe(name='agent_run', as_type='agent')
async def run_agent(agent, query: str, max_steps: int = 10, model_name: str = DEFAULT_MODEL) -> dict:
    result = await agent.ainvoke(
        {'messages': [('user', query)]},
        config={'recursion_limit': 2 * max_steps + 1},
    )
    messages = result['messages']
    answer = messages[-1].content
    total_tokens = sum((m.usage_metadata or {}).get('total_tokens', 0) for m in messages if getattr(m, 'usage_metadata', None))
    langfuse_context.update_current_observation(usage={'total_tokens': total_tokens}, model=model_name)
    # Real cost in USD: OpenRouter returns it in each response's usage object.
    total_cost = sum((m.response_metadata or {}).get('token_usage', {}).get('cost') or 0.0 for m in messages)
    langfuse_context.update_current_observation(metadata={'cost_usd': round(total_cost, 6)})
    return {'answer': answer, 'metadata': {'total_messages': len(messages), 'total_tokens': total_tokens},
            # HERMES additions:
            'structured_response': result.get('structured_response'),
            'cost_usd': round(total_cost, 6), 'messages': messages}


def parse_structured(result: dict, schema: type[BaseModel]) -> BaseModel:
    """Return the structured answer; fall back to JSON in the final message; else raise."""
    sr = result.get("structured_response")
    if isinstance(sr, schema):
        return sr
    if isinstance(sr, dict):
        return schema.model_validate(sr)
    text = result.get("answer") or ""
    if isinstance(text, list):  # some providers return content blocks
        text = "".join(part.get("text", "") for part in text if isinstance(part, dict))
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return schema.model_validate_json(text[start:end + 1])
        except ValidationError as exc:
            raise AgentOutputError(f"{schema.__name__} JSON did not validate: {exc.errors()[:2]}") from exc
    raise AgentOutputError(f"agent returned no {schema.__name__}")


def usage_of(result: dict) -> dict:
    return {"llm_runs": 1, "tokens": result["metadata"]["total_tokens"], "cost_usd": result.get("cost_usd", 0.0)}


# ---- LoopDetector wired into tool execution --------------------------------------------


def loop_guard_middleware(detector: LoopDetector, on_loop: Callable[[str, str], Any] | None = None):
    """Run the given ``LoopDetector.check_tool_call`` BEFORE every tool call.

    On a repeat the tool is not executed; the agent receives a warning message instead,
    which is the visible reaction ("retry with a different approach").
    """

    @wrap_tool_call(name="LoopGuard")
    async def loop_guard(request, handler):
        call = request.tool_call
        args = json.dumps(call.get("args", {}), sort_keys=True)
        check = detector.check_tool_call(call["name"], args)
        if check.is_looping:
            if on_loop:
                on_loop(call["name"], check.message)
            return ToolMessage(
                content=(f"LOOP DETECTED ({check.strategy}): {check.message} The call was NOT executed. "
                         "Use the results you already have, change the query, or finish your answer."),
                tool_call_id=call["id"], name=call["name"], status="error")
        return await handler(request)

    return loop_guard


# ---- convergence guard: a step budget that ends in an answer, not in a dead end ----------

_STUCK_MARKERS = ("Tool call limit exceeded", "LOOP DETECTED")


def converge_middleware(finalize_after: int, on_converge: Callable[[str], Any] | None = None):
    """Force the agent to submit its structured answer once it is out of budget or looping.

    Observed live: after a tool's budget was spent, the model kept re-issuing the blocked call
    until the model-call cap ended the run with no answer. This guard removes the data tools
    (leaving only the structured-output tool, which ToolStrategy binds with tool_choice="any")
    when a tool limit / loop message has appeared or the agent has used `finalize_after` model calls.
    """

    @wrap_model_call(name="ConvergeGuard")
    async def converge(request, handler):
        msgs = request.messages
        model_calls = sum(1 for m in msgs if m.type == "ai")
        stuck = any(m.type == "tool" and isinstance(m.content, str) and m.content.startswith(_STUCK_MARKERS)
                    for m in msgs)
        if request.tools and (stuck or model_calls >= finalize_after):
            reason = "tool budget exhausted / loop detected" if stuck else f"{model_calls} model calls used"
            if on_converge:
                on_converge(reason)
            request = request.override(tools=[], messages=[*msgs, HumanMessage(
                "Your tool budget for this stage is spent. Do not call any more data tools. Submit your final "
                "structured answer now, using only the evidence already gathered above.")])
        return await handler(request)

    return converge


# ---- structured-output loop guard ---------------------------------------------------------

_PARSE_ERROR = "Error: Failed to parse structured output"


def output_loop_middleware(stop_after: int = 3, on_loop: Callable[[str], Any] | None = None):
    """Catch a model that re-submits the SAME rejected structured answer.

    Observed live: the planner set a required speed to 0 for "up to 0.8 m/s", the validator rejected it,
    and the model re-sent identical arguments until the model-call cap. The rejected attempts are replayed
    through the given LoopDetector (exact matching). On the first repeat the model is told precisely which
    field to change; after `stop_after` identical attempts the run stops early instead of burning the budget.
    """

    @wrap_model_call(name="OutputLoopGuard")
    async def guard(request, handler):
        msgs = request.messages
        calls = {tc["id"]: tc for m in msgs if m.type == "ai" for tc in (m.tool_calls or [])}
        rejected = [(calls[m.tool_call_id], m.content) for m in msgs
                    if m.type == "tool" and isinstance(m.content, str) and m.content.startswith(_PARSE_ERROR)
                    and m.tool_call_id in calls]
        detector, check, repeats = LoopDetector(exact_threshold=1, fuzzy_threshold=1.01), None, 1
        for call, _ in rejected:
            check = detector.check_tool_call(call["name"], json.dumps(call["args"], sort_keys=True))
            repeats = repeats + 1 if check.is_looping else 1
        if check is not None and check.is_looping:
            error = rejected[-1][1].split("\n For further")[0][:600]
            if on_loop:
                on_loop(f"{check.message} ({repeats} identical rejected answers)")
            if repeats >= stop_after:
                raise AgentOutputError(f"structured-output loop: {repeats} identical invalid answers. {error[:300]}")
            request = request.override(messages=[*msgs, HumanMessage(
                f"LOOP DETECTED: you sent the same rejected answer {repeats} times. The validator said:\n{error}\n"
                "Change the field(s) named above to valid values. Do not resend the same values.")])
        return await handler(request)

    return guard


# ---- evidence harvesting: citations come from tool output, not from LLM transcription ------

_HIT_HEADER = re.compile(r"^\[\d+\] source: (?P<source>[^|]+) \| section: (?P<section>[^|]+) \| page: (?P<page>[^|]+) \| "
                         r"url: (?P<url>[^|]+) \| relevance: [\d.]+$", re.MULTILINE)


def harvest_datasheet_evidence(messages: list, max_items: int = 8) -> list[dict]:
    """Extract cited passages from the agent's own `search_datasheets` tool results."""
    found, seen = [], set()
    for m in messages:
        if getattr(m, "type", "") != "tool" or getattr(m, "name", "") != "search_datasheets":
            continue
        text = m.content if isinstance(m.content, str) else str(m.content)
        headers = list(_HIT_HEADER.finditer(text))
        for i, h in enumerate(headers):
            body = text[h.end(): headers[i + 1].start() if i + 1 < len(headers) else len(text)].strip()
            passage = body.split("\n", 1)[-1].strip()  # drop the "title - section" prefix line
            key = (h["source"].strip(), h["section"].strip())
            if key in seen or not passage:
                continue
            seen.add(key)
            found.append({"claim": f"[{h['section'].strip()}] {passage[:400]}", "source": h["source"].strip(),
                          "page": h["page"].strip(), "url": h["url"].strip()})
    return found[:max_items]
