"""UI-independent helpers for the Streamlit app (``app.py``).

Kept in the package so they are unit-tested without Streamlit: live event capture, team
selection (live LLM agents or the offline scripted replay) and flat rows for the result tables.
"""

from __future__ import annotations

from collections.abc import Callable

from hermes.config import DEFAULT_BUDGETS, Budgets
from hermes.observability.events import MissionLog

KIND_ICONS = {"plan": "🧭", "research": "🔎", "design": "📐", "calc": "🧮", "verify": "✅", "replan": "🔁",
              "critic": "🧐", "loop": "⚠️", "budget": "⛔", "report": "📄", "error": "❌", "info": "•"}

METRICS = [("bom_cost_sar", "BOM cost", "SAR", "{:,.0f}"), ("total_mass", "Total mass", "kg", "{:.2f}"),
           ("achievable_speed", "Top speed", "m/s", "{:.2f}"), ("runtime", "Runtime", "h", "{:.1f}"),
           ("system_power_avg", "Average power", "W", "{:.1f}")]


class CallbackLog(MissionLog):
    """MissionLog that also forwards every event to a callback (the UI's live event feed).

    It captures everything the console log shows, including tool-loop and stage-budget events
    raised inside the agents, which never reach the graph state.
    """

    def __init__(self, sink: Callable[[dict], None], verbose: bool = False):
        super().__init__(verbose=verbose)
        self.sink = sink

    def event(self, node, kind, message, **data) -> dict:
        record = super().event(node, kind, message, **data)
        try:
            self.sink(record)
        except Exception:  # a display problem must never break the mission
            pass
        return record


def build_team(live: bool, log: MissionLog, budgets: Budgets = DEFAULT_BUDGETS, api_key: str | None = None,
               model_name: str | None = None, use_web: bool = True):
    """Real ``create_agent`` team when live, otherwise the scripted offline replay of the demo mission."""
    if live:
        from hermes.agents.common import make_llm
        from hermes.agents.team import LLMTeam
        from hermes.config import DEFAULT_MODEL
        from hermes.models import DOMAINS

        model = model_name or DEFAULT_MODEL
        return LLMTeam(make_llm(model, api_key), model_name=model, budgets=budgets, use_web=use_web,
                       on_tool_loop=lambda d, t, m: log.event(f"research_{d}" if d in DOMAINS else d, "loop", m),
                       on_converge=lambda agent, reason: log.event(
                           agent, "budget", f"Stage budget reached ({reason}) -> forcing final answer"))
    from hermes.agents.scripted import ScriptedTeam
    from hermes.demo import (
        BALANCED_OVER_BUDGET,
        ECONOMY_DESIGN,
        MARGIN_CRITIQUE,
        PASSING_DESIGN,
        REFINED_DESIGN,
        SCRIPTED_REPLANS,
        delivery_robot_spec,
    )
    from hermes.models import Critique

    return ScriptedTeam(delivery_robot_spec(), [ECONOMY_DESIGN, BALANCED_OVER_BUDGET, PASSING_DESIGN, REFINED_DESIGN],
                        critiques=[MARGIN_CRITIQUE, Critique(verdict="PASS", summary="scripted critic: no further issues")],
                        replans=SCRIPTED_REPLANS)


def event_line(e: dict) -> str:
    return f"{e['seq']:>3}  {KIND_ICONS.get(e['kind'], '•')}  {e['node']:<20} {e['message']}"


def metric_values(final: dict) -> list[tuple[str, str]]:
    """(label, formatted value) for the headline metrics of the reported design."""
    design = final.get("final_design")
    if not design:
        return []
    calcs = design["analysis"]["calcs"]
    out = []
    for key, label, unit, fmt in METRICS:
        if key in calcs and calcs[key].get("value") is not None:
            out.append((label, f"{fmt.format(calcs[key]['value'])} {unit}"))
    return out


def bom_rows(final: dict) -> list[dict]:
    design = final.get("final_design")
    if not design:
        return []
    return [{"Component": ln["name"], "Part": f"{ln['manufacturer']} {ln['part_number']}", "Qty": ln["quantity"],
             "Unit USD": ln["unit_price_usd"], "Total SAR": ln["line_cost_sar"],
             "Weight g": ln["line_weight_g"], "Key spec": ln["key_spec"], "Data": ln["data_quality"]}
            for ln in design["bom"]["lines"]]


def check_rows(final: dict) -> list[dict]:
    design = final.get("final_design")
    if not design:
        return []
    return [{"Status": c["status"], "Kind": c["kind"], "Check": c["name"], "Required": c["required"],
             "Actual": c["actual"], "Margin %": None if c["margin_pct"] is None else round(c["margin_pct"], 1)}
            for c in design["verification"]["constraints"]]


def iteration_rows(final: dict) -> list[dict]:
    rows = []
    for d in final.get("designs") or []:
        failed = [c["name"] for c in d["verification"]["constraints"] if c["kind"] == "hard" and c["status"] == "FAIL"]
        rows.append({"Design": d["iteration"], "Strategy": d["strategy"], "Verification": d["verification"]["status"],
                     "Score": d["verification"]["score"], "Cost SAR": round(d["bom"]["total_cost_sar"]),
                     "Failed hard checks": ", ".join(failed) or "-"})
    return rows


def evidence_rows(final: dict) -> list[dict]:
    seen, rows = set(), []
    for e in final.get("evidence") or []:
        key = (e.get("source"), e.get("claim"))
        if key in seen:
            continue
        seen.add(key)
        rows.append({"Domain": e.get("domain"), "Component": e.get("component_id") or "", "Claim": e.get("claim"),
                     "Source": e.get("source"), "Page": e.get("page"), "URL": e.get("url") or ""})
    return rows
