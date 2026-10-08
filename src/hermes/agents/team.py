"""The HERMES agent team. Every LLM role is a LangChain ``create_agent`` agent (SDAIA TODO #2).

The graph talks to agents through the small ``AgentTeam`` protocol, so the same graph
runs with real LLM agents (``LLMTeam``) or with deterministic scripted agents
(``hermes.agents.scripted.ScriptedTeam``) for offline tests and reliability demos.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ModelRetryMiddleware,
    ToolCallLimitMiddleware,
)
from langchain.agents.structured_output import ToolStrategy

from hermes.agents import prompts
from hermes.agents.common import (
    as_provider_error,
    converge_middleware,
    harvest_datasheet_evidence,
    is_transient,
    loop_guard_middleware,
    output_loop_middleware,
    parse_structured,
    run_agent,
    usage_of,
)
from hermes.config import DEFAULT_BUDGETS, DEFAULT_MODEL, Budgets
from hermes.models import (
    DOMAIN_CATEGORIES,
    DOMAINS,
    Critique,
    DesignProposal,
    EvidenceNote,
    MissionDraft,
    MissionSpec,
    ReplanDecision,
    ResearchFindings,
)
from hermes.observability.tracing import observe
from hermes.tools.research.tools import (
    ENGINEERING_TOOLS,
    RESEARCH_DB_TOOLS,
    get_component,
    search_components,
)
from hermes.tools.research.web import read_webpage, search_web
from hermes.tools.verification.loop_detector import LoopDetector

Usage = dict


class AgentTeam(Protocol):
    async def plan(self, request: str) -> tuple[MissionSpec, Usage]: ...
    async def research(self, domain: str, objective: str, mission: str) -> tuple[ResearchFindings, Usage]: ...
    async def design(self, brief: str) -> tuple[DesignProposal, Usage]: ...
    async def replan(self, brief: str) -> tuple[ReplanDecision, Usage]: ...
    async def critique(self, brief: str) -> tuple[Critique, Usage]: ...
    async def summarize(self, brief: str) -> tuple[str, Usage]: ...


def _limits(tool_names: list[str], per_tool: int, web: int) -> list:
    """Step budget per stage: one ToolCallLimitMiddleware per data tool.

    Limits are per tool (not global) so the structured-output tool call that ends the
    agent run is never blocked; exit_behavior='continue' lets the agent answer with
    what it already has once a tool's budget is spent.
    """
    out = []
    for name in tool_names:
        limit = web if name in ("search_web", "read_webpage") else per_tool
        out.append(ToolCallLimitMiddleware(tool_name=name, run_limit=limit, exit_behavior="continue"))
    return out


class LLMTeam:
    """Real agents: create_agent + tools + middleware (step budgets, retries, loop guard)."""

    def __init__(self, llm, model_name: str = DEFAULT_MODEL, budgets: Budgets = DEFAULT_BUDGETS,
                 on_tool_loop: Callable[[str, str, str], None] | None = None, use_web: bool = True,
                 on_converge: Callable[[str, str], None] | None = None):
        self.model_name = model_name
        self.budgets = budgets
        def common(name: str) -> list:
            """Fresh per-agent middleware: retry transient model errors, cap model calls, stop output loops."""
            return [ModelRetryMiddleware(max_retries=2, retry_on=is_transient, on_failure="error"),
                    ModelCallLimitMiddleware(run_limit=budgets.model_calls_per_run, exit_behavior="end"),
                    output_loop_middleware(on_loop=lambda msg: on_tool_loop and on_tool_loop(
                        name, "structured_output", msg))]

        # One LoopDetector per research domain: repeated searches across design iterations are caught too.
        self.tool_detectors = {d: LoopDetector() for d in DOMAINS}
        research_tools = RESEARCH_DB_TOOLS + ([search_web, read_webpage] if use_web else [])
        tool_names = [t.name for t in research_tools]
        finalize_after = max(2, budgets.model_calls_per_run - 3)

        def converge(agent_name: str):
            return converge_middleware(finalize_after,
                                       lambda reason: on_converge and on_converge(agent_name, reason))

        self.researchers = {}
        for domain in DOMAINS:
            def report(tool, message, _d=domain):
                if on_tool_loop:
                    on_tool_loop(_d, tool, message)
            self.researchers[domain] = create_agent(
                model=llm,
                tools=research_tools,
                system_prompt=prompts.RESEARCHER_PROMPT.format(
                    domain=domain, categories=", ".join(DOMAIN_CATEGORIES[domain])),
                middleware=[*common(domain), *_limits(tool_names, budgets.tool_calls_per_tool, budgets.web_tool_calls),
                            loop_guard_middleware(self.tool_detectors[domain], report),
                            converge(f"research_{domain}")],
                response_format=ToolStrategy(ResearchFindings),
                name=f"research_{domain}",
            )

        self.replan_detector = LoopDetector()
        replan_tools = [search_components, get_component, *ENGINEERING_TOOLS]
        self.architect = create_agent(model=llm, tools=[], system_prompt=prompts.MISSION_ARCHITECT_PROMPT,
                                      middleware=common("mission_architect"), response_format=ToolStrategy(MissionDraft),
                                      name="mission_architect")
        self.designer = create_agent(model=llm, tools=[search_components, get_component],
                                     system_prompt=prompts.DESIGNER_PROMPT,
                                     middleware=[*common("designer"), *_limits(["search_components", "get_component"],
                                                                   budgets.tool_calls_per_tool, 0),
                                                 converge("designer")],
                                     response_format=ToolStrategy(DesignProposal), name="designer")
        self.replanner = create_agent(
            model=llm, tools=replan_tools, system_prompt=prompts.REPLANNER_PROMPT,
            middleware=[*common("replanner"), *_limits([t.name for t in replan_tools], budgets.tool_calls_per_tool, 0),
                        loop_guard_middleware(self.replan_detector,
                                              lambda tool, msg: on_tool_loop and on_tool_loop("replanner", tool, msg)),
                        converge("replanner")],
            response_format=ToolStrategy(ReplanDecision), name="replanner")
        self.critic = create_agent(model=llm, tools=[], system_prompt=prompts.CRITIC_PROMPT, middleware=common("critic"),
                                   response_format=ToolStrategy(Critique), name="critic")
        self.writer = create_agent(model=llm, tools=[], system_prompt=prompts.REPORTER_PROMPT, middleware=common("reporter"),
                                   name="reporter")

    async def _run_full(self, agent, query: str, schema=None):
        """Run one agent; return (answer, usage, messages)."""
        # Each middleware hook adds graph steps inside create_agent, so the LangGraph recursion limit must be
        # far above the model-call budget; ModelCallLimitMiddleware is the real bound on LLM calls.
        try:
            result = await run_agent(agent, query, max_steps=10 * self.budgets.model_calls_per_run,
                                     model_name=self.model_name)
        except Exception as exc:
            fatal = as_provider_error(exc)
            if fatal:
                raise fatal from exc
            raise
        value = parse_structured(result, schema) if schema else str(result["answer"])
        return value, usage_of(result), result.get("messages", [])

    async def _run(self, agent, query: str, schema=None):
        value, usage, _ = await self._run_full(agent, query, schema)
        return value, usage

    @observe(name="agent:mission_architect")
    async def plan(self, request: str):
        draft, usage = await self._run(self.architect, f"Engineering request:\n{request}", MissionDraft)
        spec, rejected = draft.to_spec(request)
        usage["rejected_overrides"] = rejected
        return spec, usage

    async def research(self, domain: str, objective: str, mission: str):
        @observe(name=f"agent:research_{domain}")
        async def _go():
            query = f"{mission}\n\nRESEARCH OBJECTIVE ({domain}): {objective}"
            findings, usage, messages = await self._run_full(self.researchers[domain], query, ResearchFindings)
            # Citations are harvested from the agent's own tool results, so they cannot be mis-transcribed.
            harvested = [EvidenceNote(**e)
                         for e in harvest_datasheet_evidence(messages)]
            known = {(e.source, e.claim) for e in findings.evidence}
            findings = findings.model_copy(update={"evidence": [*findings.evidence,
                                                                *[e for e in harvested if (e.source, e.claim) not in known]]})
            return findings.model_copy(update={"domain": domain}), usage
        return await _go()

    @observe(name="agent:designer")
    async def design(self, brief: str):
        return await self._run(self.designer, brief, DesignProposal)

    @observe(name="agent:replanner")
    async def replan(self, brief: str):
        return await self._run(self.replanner, brief, ReplanDecision)

    @observe(name="agent:critic")
    async def critique(self, brief: str):
        return await self._run(self.critic, brief, Critique)

    @observe(name="agent:reporter")
    async def summarize(self, brief: str):
        return await self._run(self.writer, brief)
