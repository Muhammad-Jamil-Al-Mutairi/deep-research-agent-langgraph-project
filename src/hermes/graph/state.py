"""Typed LangGraph state for a HERMES mission.

Values are plain JSON-compatible dicts (Pydantic ``model_dump()``) so the checkpointer
can persist every step. Keys written by the parallel research branches use reducers;
without them LangGraph raises ``InvalidUpdateError`` on concurrent writes.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict


def merge_dict(left: dict | None, right: dict | None) -> dict:
    """Shallow merge: later research for a domain replaces earlier research."""
    return {**(left or {}), **(right or {})}


def add_usage(left: dict | None, right: dict | None) -> dict:
    """Sum numeric usage counters (tokens, cost, agent runs, research calls, steps)."""
    out = dict(left or {})
    for key, value in (right or {}).items():
        out[key] = round(out.get(key, 0) + value, 6)
    return out


class HermesState(TypedDict, total=False):
    # mission input and plan
    mission_id: str
    user_request: str
    spec: dict  # MissionSpec
    research_plan: dict  # domain -> objective
    # research (written by four parallel branches)
    research_results: Annotated[dict, merge_dict]  # domain -> ResearchFindings
    research_requests: dict  # domain -> objective, set by the replanner for targeted re-research
    evidence: Annotated[list, operator.add]  # EvidenceNote dicts with domain
    # design loop
    strategy: str
    pending_proposal: dict | None  # DesignProposal from the designer
    pending_analysis: dict | None  # {"bom": ..., "analysis": ...} from the calculator
    designs: Annotated[list, operator.add]  # iteration history: one record per verified design
    current: dict  # latest design record
    replan: dict | None  # latest ReplanDecision
    critic_feedback: Annotated[list, operator.add]
    # reliability
    loop_flags: dict  # latest guard verdicts (repetition / stagnation / budget)
    route: str  # guard decision: critic | replanner | reporter
    final_status: str
    # observability
    events: Annotated[list, operator.add]
    usage: Annotated[dict, add_usage]
    errors: Annotated[list, operator.add]
    # output
    report_md: str
    final_design: dict | None
