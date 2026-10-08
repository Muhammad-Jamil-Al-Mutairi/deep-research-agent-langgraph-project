"""The HERMES mission graph (SDAIA TODO #3, redesigned as a non-sequential multi-agent graph).

    START -> mission_architect -> [research_motor | research_battery | research_mechanical |
             research_electronics] (parallel) -> designer -> calculate -> verify -> guard
    guard   --FAIL-->  replanner --(targeted re-research | designer)
    guard   --PASS-->  critic    --REVISE--> replanner
                                 --PASS-->   reporter -> END
    guard   --budget exhausted / stagnation--> reporter
"""

from __future__ import annotations

import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from hermes.agents.team import AgentTeam
from hermes.config import DEFAULT_BUDGETS, Budgets
from hermes.graph.nodes import HermesNodes
from hermes.graph.routing import (
    RESEARCH_NODES,
    route_after_architect,
    route_after_critic,
    route_after_guard,
    route_after_replan,
)
from hermes.graph.state import HermesState
from hermes.models.requirements import DOMAINS
from hermes.observability.events import MissionLog
from hermes.observability.tracing import current_span, observe, span_totals
from hermes.tools.research.component_db import get_db
from hermes.tools.research.rag import get_index


def build_graph(team: AgentTeam, budgets: Budgets = DEFAULT_BUDGETS, log: MissionLog | None = None,
                checkpointer=None, interrupt_before: list[str] | None = None):
    """Assemble and compile the mission graph.

    ``checkpointer=None`` uses an in-memory checkpointer (resumable by thread_id within the
    process); ``False`` disables persistence. ``interrupt_before`` pauses before the named nodes
    (e.g. ``["critic"]`` for a human review gate); resume with ``graph.ainvoke(None, config)``.
    """
    nodes = HermesNodes(team, log=log, budgets=budgets)
    g = StateGraph(HermesState)

    g.add_node("mission_architect", nodes.mission_architect)
    for domain in DOMAINS:
        g.add_node(RESEARCH_NODES[domain], nodes.research_node(domain))
    g.add_node("designer", nodes.designer)
    g.add_node("calculate", nodes.calculate)
    g.add_node("verify", nodes.verify)
    g.add_node("guard", nodes.guard)
    g.add_node("replanner", nodes.replanner)
    g.add_node("critic", nodes.critic)
    g.add_node("reporter", nodes.reporter)

    g.add_edge(START, "mission_architect")
    # Planner decomposes the mission -> four research branches run in parallel (same superstep).
    g.add_conditional_edges("mission_architect", route_after_architect,
                            [*RESEARCH_NODES.values(), "reporter"])
    # Fan-in: the designer runs once after whichever research branches ran in the previous superstep.
    for node in RESEARCH_NODES.values():
        g.add_edge(node, "designer")
    g.add_edge("designer", "calculate")
    g.add_edge("calculate", "verify")
    g.add_edge("verify", "guard")
    g.add_conditional_edges("guard", route_after_guard, ["critic", "replanner", "reporter"])
    g.add_conditional_edges("replanner", route_after_replan, [*RESEARCH_NODES.values(), "designer"])
    g.add_conditional_edges("critic", route_after_critic, ["replanner", "reporter"])
    g.add_edge("reporter", END)

    if checkpointer is None:
        checkpointer = InMemorySaver()
    return g.compile(checkpointer=checkpointer or None, interrupt_before=interrupt_before)


def initial_state(request: str, mission_id: str | None = None) -> dict:
    return {"mission_id": mission_id or f"mission-{uuid.uuid4().hex[:8]}", "user_request": request,
            "strategy": "economy", "usage": {}, "events": [], "designs": [], "evidence": [], "errors": [],
            "critic_feedback": [], "research_results": {}}


def mission_config(mission_id: str, budgets: Budgets = DEFAULT_BUDGETS) -> dict:
    return {"configurable": {"thread_id": mission_id}, "recursion_limit": budgets.recursion_limit}


def warm_up_knowledge() -> None:
    """Build the component DB and the RAG index before the parallel research branches start."""
    get_db()
    try:
        get_index()
    except Exception as exc:  # RAG is optional at runtime: tools report it as unavailable
        print(f"[warn] datasheet index unavailable: {exc}")


@observe(name="hermes_mission", as_type="mission")
async def run_mission(graph, request: str, mission_id: str | None = None, budgets: Budgets = DEFAULT_BUDGETS) -> dict:
    """Run one mission end-to-end. The root span prints the full trace tree when it closes."""
    state = initial_state(request, mission_id)
    warm_up_knowledge()
    final = await graph.ainvoke(state, config=mission_config(state["mission_id"], budgets))
    span = current_span()
    if span is not None:
        totals = span_totals(span)
        span.metadata["cost_usd"] = totals["cost_usd"]
        span.usage["total_tokens"] = totals["total_tokens"]
        final["trace_totals"] = totals
    return final
