"""Conditional routing and reliability decisions (pure functions, unit-tested).

The guard decision combines four inputs: the deterministic verification status, the
loop detectors (design repetition + text and metric stagnation), the strategy ladder
and the execution budgets.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hermes.config import STRATEGY_LADDER, Budgets
from hermes.models.requirements import DOMAINS
from hermes.tools.verification.loop_detector import (
    LoopDetector,
    MetricStagnationDetector,
)

RESEARCH_NODES = {d: f"research_{d}" for d in DOMAINS}


@dataclass
class GuardVerdict:
    route: str  # "critic" | "replanner" | "reporter"
    strategy: str
    final_status: str | None = None
    repeated: bool = False
    stagnated: bool = False
    messages: list[tuple[str, str]] = field(default_factory=list)  # (event kind, message)


def detect_design_repetition(fingerprints: list[str]) -> tuple[bool, str]:
    """Replay the given LoopDetector over the design history; flag an exact re-proposal."""
    detector = LoopDetector(exact_threshold=1, fuzzy_threshold=0.95)
    result = None
    for fp in fingerprints:
        result = detector.check_tool_call("propose_design", fp.replace(";", " "))
    if result and result.is_looping:
        return True, result.message
    return False, ""


def detect_stagnation(scores: list[float], rationales: list[str], budgets: Budgets) -> tuple[bool, str]:
    """Numeric stagnation (score not improving) OR text stagnation (near-identical rationales)."""
    metric = MetricStagnationDetector(budgets.stagnation_window, budgets.stagnation_epsilon).check(scores)
    if metric.is_looping:
        return True, metric.message
    text = LoopDetector(stagnation_window=budgets.stagnation_window, fuzzy_threshold=0.85)
    result = None
    for r in rationales:
        result = text.check_output_stagnation(r)
    if result and result.is_looping and any(s < 0 for s in scores[-budgets.stagnation_window:]):
        return True, result.message
    return False, ""


def next_strategy(current: str) -> str | None:
    idx = STRATEGY_LADDER.index(current) if current in STRATEGY_LADDER else -1
    return STRATEGY_LADDER[idx + 1] if idx + 1 < len(STRATEGY_LADDER) else None


def decide_after_verify(designs: list[dict], strategy: str, steps_used: int, budgets: Budgets) -> GuardVerdict:
    """Route after deterministic verification, applying loop detection and budgets."""
    current = designs[-1]
    status = current["verification"]["status"]
    verdict = GuardVerdict(route="replanner", strategy=strategy)

    if status == "PASS":
        reviewed = [d for d in designs[:-1] if d["fingerprint"] == current["fingerprint"]]
        if reviewed:  # identical to a verified design the critic already saw: no improvement is available
            verdict.repeated = True
            verdict.route, verdict.final_status = "reporter", "VERIFIED"
            verdict.messages.append(("loop", f"REPETITION DETECTED - design #{current['iteration']} repeats verified "
                                             f"design #{reviewed[-1]['iteration']}, already reviewed by the critic. "
                                             "Finalising instead of re-reviewing."))
            return verdict
        verdict.route = "critic"
        return verdict

    repeated, msg = detect_design_repetition([d["fingerprint"] for d in designs])
    if repeated:
        verdict.repeated = True
        verdict.messages.append(("loop", f"REPETITION DETECTED - design #{current['iteration']} repeats an earlier "
                                         f"design. {msg}"))

    stagnated, msg = detect_stagnation([d["verification"]["score"] for d in designs],
                                       [d["proposal"].get("rationale", "") for d in designs], budgets)
    if stagnated or repeated:
        verdict.stagnated = stagnated
        if stagnated:
            verdict.messages.append(("loop", f"STAGNATION DETECTED - {msg}"))
        new = next_strategy(strategy)
        if new is None:
            verdict.route, verdict.final_status = "reporter", "STAGNATED"
            verdict.messages.append(("loop", "No strategies left on the ladder - stopping with the best candidate. "
                                             "Human review required."))
            return verdict
        verdict.strategy = new
        verdict.messages.append(("loop", f"Changing strategy: {strategy} -> {new}."))

    if len(designs) >= budgets.max_design_iterations:
        verdict.route, verdict.final_status = "reporter", "BUDGET_EXHAUSTED"
        verdict.messages.append(("budget", f"DESIGN BUDGET EXHAUSTED - {len(designs)}/{budgets.max_design_iterations} "
                                           "design iterations used. Human review required."))
    elif steps_used >= budgets.max_total_steps:
        verdict.route, verdict.final_status = "reporter", "BUDGET_EXHAUSTED"
        verdict.messages.append(("budget", f"STEP BUDGET EXHAUSTED - {steps_used}/{budgets.max_total_steps} "
                                           "graph steps used. Human review required."))
    return verdict


def best_design(designs: list[dict]) -> dict | None:
    """Best candidate: highest verification score (0 = pass), then lowest cost."""
    if not designs:
        return None
    return max(designs, key=lambda d: (d["verification"]["score"], -d["bom"]["total_cost_sar"]))


# ---- LangGraph edge functions -------------------------------------------------------------


def route_after_architect(state: dict) -> list[str] | str:
    """Fan out to the four research branches in parallel (or stop if planning failed)."""
    if state.get("final_status") == "FAILED":
        return "reporter"
    return list(RESEARCH_NODES.values())


def route_after_guard(state: dict) -> str:
    return state["route"]


def route_after_replan(state: dict) -> list[str] | str:
    """Targeted re-research (only the requested domains, in parallel) or straight back to design."""
    requests = state.get("research_requests") or {}
    nodes = [RESEARCH_NODES[d] for d in requests if d in RESEARCH_NODES]
    return nodes or "designer"


def route_after_critic(state: dict) -> str:
    return state["route"]
