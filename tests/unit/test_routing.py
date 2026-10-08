"""Pure routing / guard decisions: every branch."""

from hermes.config import Budgets
from hermes.graph.routing import (
    best_design,
    decide_after_verify,
    route_after_architect,
    route_after_replan,
)


def record(i, status="FAIL", score=-0.5, cost=1000.0, fp=None, rationale=None):
    return {"iteration": i, "fingerprint": fp or f"P-{i}x1", "bom": {"total_cost_sar": cost},
            "verification": {"status": status, "score": 0.0 if status == "PASS" else score},
            "proposal": {"rationale": rationale or f"rationale number {i} with distinct words {i * 7}"}}


B = Budgets()


def test_pass_routes_to_critic():
    v = decide_after_verify([record(1, "PASS")], "economy", 5, B)
    assert v.route == "critic" and v.final_status is None


def test_fail_routes_to_replanner():
    v = decide_after_verify([record(1, score=-0.4)], "economy", 5, B)
    assert v.route == "replanner" and v.strategy == "economy"


def test_repeated_design_escalates_strategy():
    v = decide_after_verify([record(1, score=-0.9, fp="A;B"), record(2, score=-0.5, fp="A;B")], "economy", 9, B)
    assert v.repeated and v.strategy == "balanced" and v.route == "replanner"
    assert any("REPETITION" in m for _, m in v.messages)


def test_metric_stagnation_escalates_then_stops_at_top_of_ladder():
    hist = [record(i, score=-0.40) for i in (1, 2, 3)]
    v = decide_after_verify(hist, "balanced", 12, B)
    assert v.stagnated and v.strategy == "performance" and v.route == "replanner"
    v2 = decide_after_verify(hist, "relax_soft_preferences", 12, B)
    assert v2.route == "reporter" and v2.final_status == "STAGNATED"


def test_design_budget_exhausted():
    hist = [record(i, score=-1.0 + 0.2 * i) for i in range(1, 6)]  # improving, no stagnation
    v = decide_after_verify(hist, "economy", 20, B)
    assert v.route == "reporter" and v.final_status == "BUDGET_EXHAUSTED"


def test_step_budget_exhausted():
    v = decide_after_verify([record(1)], "economy", B.max_total_steps, B)
    assert v.final_status == "BUDGET_EXHAUSTED"


def test_edge_functions():
    assert route_after_architect({"final_status": "FAILED"}) == "reporter"
    assert len(route_after_architect({})) == 4
    assert route_after_replan({"research_requests": {"battery": "x"}}) == ["research_battery"]
    assert route_after_replan({"research_requests": {}}) == "designer"


def test_best_design_prefers_score_then_cost():
    designs = [record(1, score=-0.5), record(2, "PASS", cost=1400), record(3, "PASS", cost=1300)]
    assert best_design(designs)["iteration"] == 3
    assert best_design([]) is None


def test_repeated_passing_design_is_finalised_not_re_reviewed():
    v = decide_after_verify([record(1, "PASS", fp="A;B"), record(2, "PASS", fp="A;B")], "balanced", 20, B)
    assert v.route == "reporter" and v.final_status == "VERIFIED" and v.repeated
    assert any("already reviewed by the critic" in m for _, m in v.messages)
