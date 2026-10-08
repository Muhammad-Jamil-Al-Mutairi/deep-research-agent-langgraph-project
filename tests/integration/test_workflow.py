"""End-to-end LangGraph workflow tests (offline).

The graph, tools, calculator, verifier, routing, loop detection, budgets and checkpointer
are the production code. Agents are either scripted or real ``create_agent`` agents driven
by a scripted fake chat model.
"""

from __future__ import annotations

import asyncio

import pytest
from langchain_core.messages import AIMessage

from hermes.agents.scripted import ScriptedChatModel as ToolCapableFakeModel
from hermes.agents.scripted import ScriptedTeam
from hermes.agents.team import LLMTeam
from hermes.config import Budgets
from hermes.demo import (
    BALANCED_OVER_BUDGET,
    DELIVERY_ROBOT_REQUEST,
    ECONOMY_DESIGN,
    MARGIN_CRITIQUE,
    PASSING_DESIGN,
    REFINED_DESIGN,
    SCRIPTED_REPLANS,
    delivery_robot_spec,
)
from hermes.graph import build_graph, mission_config, run_mission
from hermes.models import Critique, DesignProposal, ResearchFindings
from hermes.observability.events import MissionLog


def run(team, budgets=None, mission_id="test"):
    budgets = budgets or Budgets()
    graph = build_graph(team, budgets=budgets, log=MissionLog(verbose=False))
    final = asyncio.run(run_mission(graph, DELIVERY_ROBOT_REQUEST, mission_id=mission_id, budgets=budgets))
    return graph, final


def messages(final, kind=None):
    return [e["message"] for e in final["events"] if kind is None or e["kind"] == kind]


@pytest.fixture
def demo_team():
    return ScriptedTeam(delivery_robot_spec(), [ECONOMY_DESIGN, BALANCED_OVER_BUDGET, PASSING_DESIGN, REFINED_DESIGN],
                        critiques=[MARGIN_CRITIQUE, Critique(verdict="PASS", summary="no further issues")],
                        replans=SCRIPTED_REPLANS)


def test_full_mission_fail_replan_pass_critic_revise(demo_team):
    graph, final = run(demo_team)
    statuses = [d["verification"]["status"] for d in final["designs"]]
    assert statuses == ["FAIL", "FAIL", "PASS", "PASS"]
    assert final["final_status"] == "VERIFIED"
    assert final["final_design"]["iteration"] == 4
    assert [c["verdict"] for c in final["critic_feedback"]] == ["REVISE", "PASS"]
    # planner fan-out: all four research branches ran before the first design
    first_design = demo_team.calls.index("design")
    assert sorted(demo_team.calls[1:first_design]) == ["research:battery", "research:electronics",
                                                       "research:mechanical", "research:motor"]
    # replanner escalated the strategy after the first failure
    assert [d["strategy"] for d in final["designs"]] == ["economy", "balanced", "balanced", "balanced"]
    assert any("Strategy escalated: economy -> balanced" in m for m in messages(final))
    # every research branch attaches cited datasheet passages for its shortlist (deterministic RAG)
    tagged = {e["domain"] for e in final["evidence"] if e.get("component_id") and e.get("url")}
    assert tagged == {"motor", "battery", "mechanical", "electronics"}
    report = final["report_md"]
    assert "not a certified engineering design" in report and "Physical validation" in report
    assert "Datasheet evidence retrieved" in report
    assert " is safe" not in report.lower()


def test_checkpointer_persists_every_step(demo_team):
    graph, final = run(demo_team, mission_id="ckpt")
    config = mission_config("ckpt")
    snapshot = asyncio.run(graph.aget_state(config))
    assert snapshot.values["final_status"] == "VERIFIED"

    async def collect():
        return [s async for s in graph.aget_state_history(config)]

    history = asyncio.run(collect())
    assert len(history) > 20  # one checkpoint per superstep
    designs_over_time = {len(s.values.get("designs") or []) for s in history}
    assert designs_over_time >= {0, 1, 2, 3, 4}


def test_repeated_design_triggers_loop_detection_and_graceful_stop():
    team = ScriptedTeam(delivery_robot_spec(), [ECONOMY_DESIGN])  # keeps proposing the same failing design
    _, final = run(team, mission_id="loop")
    loop_events = messages(final, "loop")
    assert any("rejected before calculation" in m for m in loop_events)  # designer re-prompted first
    assert any("REPETITION DETECTED" in m for m in loop_events)  # then the guard catches the repeat
    assert any("Changing strategy" in m for m in loop_events)
    assert final["final_status"] in ("STAGNATED", "BUDGET_EXHAUSTED")
    assert "Human review required" in final["report_md"]
    assert final["final_design"] is not None  # best candidate still reported


def test_design_budget_is_enforced():
    budgets = Budgets(max_design_iterations=2)
    team = ScriptedTeam(delivery_robot_spec(), [ECONOMY_DESIGN, BALANCED_OVER_BUDGET])
    _, final = run(team, budgets=budgets, mission_id="budget")
    assert len(final["designs"]) == 2
    assert final["final_status"] == "BUDGET_EXHAUSTED"
    assert any("DESIGN BUDGET EXHAUSTED" in m for m in messages(final, "budget"))


def test_research_agent_failure_falls_back_to_database(demo_team):
    demo_team.fail_research = {"battery"}
    _, final = run(demo_team, mission_id="fallback")
    assert final["final_status"] == "VERIFIED"
    assert any("falling back to structured DB query" in m for m in messages(final, "error"))
    assert final["research_results"]["battery"]["candidates"]


def test_planner_failure_ends_gracefully():
    class BrokenPlanner(ScriptedTeam):
        async def plan(self, request):
            raise RuntimeError("model returned garbage")

    _, final = run(BrokenPlanner(delivery_robot_spec(), [PASSING_DESIGN]), mission_id="broken")
    assert final["final_status"] == "FAILED"
    assert "could not be planned" in final["report_md"]


# ---- real create_agent agents driven by a scripted fake chat model --------------------------


def _tool_call(name, args, call_id):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}])


def test_create_agent_designer_returns_validated_structured_output():
    model = ToolCapableFakeModel(responses=[_tool_call("DesignProposal", PASSING_DESIGN.model_dump(), "d1")])
    team = LLMTeam(model, use_web=False)
    proposal, usage = asyncio.run(team.design("brief"))
    assert isinstance(proposal, DesignProposal)
    assert proposal.lines == PASSING_DESIGN.lines
    assert usage["llm_runs"] == 1


def test_create_agent_researcher_loop_guard_blocks_repeated_tool_calls():
    args = {"category": "battery", "filters": ["capacity_mah >= 4000"]}
    findings = {"domain": "battery", "summary": "two LiPo packs",
                "candidates": [{"component_id": "OVO-3S-6000-80C", "suitability": "66.6 Wh"}]}
    model = ToolCapableFakeModel(responses=[
        _tool_call("search_components", args, "s1"),
        _tool_call("search_components", args, "s2"),
        _tool_call("search_components", args, "s3"),  # third identical call -> blocked by LoopDetector
        _tool_call("ResearchFindings", findings, "f1"),
    ])
    loops = []
    team = LLMTeam(model, use_web=False, on_tool_loop=lambda domain, tool, msg: loops.append((domain, tool)))
    result, _ = asyncio.run(team.research("battery", "find >= 40 Wh", "mission"))
    assert isinstance(result, ResearchFindings) and result.candidates[0].component_id == "OVO-3S-6000-80C"
    assert loops == [("battery", "search_components")]


def test_checkpoint_pause_before_critic_and_resume(demo_team):
    graph = build_graph(demo_team, log=MissionLog(verbose=False), interrupt_before=["critic"])
    config = mission_config("resume")
    from hermes.graph import initial_state

    paused = asyncio.run(graph.ainvoke(initial_state(DELIVERY_ROBOT_REQUEST, "resume"), config=config))
    snapshot = asyncio.run(graph.aget_state(config))
    assert snapshot.next == ("critic",)  # paused at the human-review gate
    assert paused["designs"][-1]["verification"]["status"] == "PASS"
    while asyncio.run(graph.aget_state(config)).next:  # resume from the checkpoint (twice: two critic visits)
        final = asyncio.run(graph.ainvoke(None, config=config))
    assert final["final_status"] == "VERIFIED"


def test_failed_revision_falls_back_to_last_verified_design():
    """Critic sends a passing design back; the revision fails and the budget ends the loop."""
    team = ScriptedTeam(delivery_robot_spec(), [PASSING_DESIGN, ECONOMY_DESIGN], critiques=[MARGIN_CRITIQUE])
    _, final = run(team, budgets=Budgets(max_design_iterations=2), mission_id="fallback")
    assert [d["verification"]["status"] for d in final["designs"]] == ["PASS", "FAIL"]
    assert final["final_status"] == "VERIFIED" and final["final_design"]["iteration"] == 1
    assert any("reporting the last verified design #1" in m for m in messages(final))


def test_vague_critic_revise_is_not_actionable():
    """A REVISE that names no catalogue replacement must not trigger another design iteration."""
    from hermes.models import CriticIssue

    vague = Critique(verdict="REVISE", summary="Could be better.",
                     issues=[CriticIssue(severity="medium", category="evidence", finding="IMU current not stated",
                                         recommendation="Find a better-documented IMU.")])
    team = ScriptedTeam(delivery_robot_spec(), [PASSING_DESIGN], critiques=[vague])
    _, final = run(team, mission_id="vague-critic")
    assert len(final["designs"]) == 1 and final["final_status"] == "VERIFIED"
    assert any("REVISE not actionable" in m for m in messages(final))
    assert "IMU current not stated" in final["report_md"]  # kept as a limitation


def test_provider_out_of_credits_stops_the_mission_cleanly():
    """A fatal provider error (HTTP 402) ends the loop at once: no further LLM calls, best candidate reported."""
    from hermes.agents.common import ProviderError

    class CreditsRunOut(ScriptedTeam):
        async def replan(self, brief):
            self.calls.append("replan")
            raise ProviderError("LLM provider refused the request (HTTP 402): requires more credits")

    team = CreditsRunOut(delivery_robot_spec(), [ECONOMY_DESIGN, PASSING_DESIGN])
    _, final = run(team, mission_id="credits")
    assert final["final_status"] == "PROVIDER_ERROR"
    assert team.calls.count("design") == 1 and team.calls.count("replan") == 1  # nothing after the failure
    assert "summarize" not in team.calls  # deterministic summary fallback, no LLM call
    assert final["final_design"]["iteration"] == 1  # best candidate still reported
    assert "LLM PROVIDER UNAVAILABLE" in final["report_md"]
