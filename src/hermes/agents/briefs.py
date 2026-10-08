"""Render compact, number-rich text briefs for the agents from structured state.

Agents never receive raw state dumps: they get the facts that matter for their
decision, with every number coming from the database or the calculation engine.
"""

from __future__ import annotations

from hermes.config import STRATEGY_DESCRIPTIONS
from hermes.models import MissionSpec, VerificationReport
from hermes.models.design import BOM
from hermes.tools.engineering.calculator import DesignAnalysis
from hermes.tools.research.component_db import get_db

KEY_CALCS = ["total_mass", "achievable_speed", "torque_continuous_design", "torque_peak_design",
             "motor_current_peak", "system_power_avg", "battery_energy", "runtime", "bom_cost_sar"]


def mission_brief(spec: MissionSpec) -> str:
    r, p = spec.requirements, spec.profile
    lines = [
        f"MISSION: {spec.title}",
        f"- payload {r.payload_kg} kg | runtime >= {r.runtime_h_min} h | top speed >= {r.max_speed_mps} m/s",
        f"- mass <= {r.mass_kg_max} kg ({'incl.' if r.mass_includes_payload else 'excl.'} payload) | "
        f"budget <= {r.budget_sar_max} SAR",
        f"- required features: {', '.join(r.required_features) or 'none'}",
        f"- profile: cruise {p.cruise_speed_mps} m/s, grade {p.design_grade_deg} deg ({p.fraction_time_on_grade:.0%} of time), "
        f"accel {p.acceleration_mps2} m/s2, Crr {p.rolling_resistance_coeff}, torque SF {p.torque_safety_factor}, "
        f"usable battery {p.battery_usable_fraction:.0%}",
    ]
    if spec.assumptions:
        lines.append("- assumptions: " + "; ".join(f"{a.id}: {a.statement}" for a in spec.assumptions))
    return "\n".join(lines)


def shortlist_brief(research_results: dict) -> str:
    db = get_db()
    out = ["SHORTLISTS FROM RESEARCH (numbers from the component database):"]
    for domain, findings in sorted(research_results.items()):
        out.append(f"[{domain}] {findings.get('summary', '')}")
        for cand in findings.get("candidates", []):
            comp = db.get(cand["component_id"])
            if comp is None:
                continue
            weight = "weight n/v" if comp.weight_g is None else f"{comp.weight_g:g} g"
            pack = (f" per {comp.pack_qty}-pack (BOM quantity counts units: 2 per robot -> quantity 2)"
                    if comp.pack_qty > 1 else "")
            out.append(f"  - {comp.component_id} ({comp.category}) {comp.price_usd:.2f} USD{pack}, {weight}, "
                       f"{comp.key_spec()} :: {cand.get('suitability', '')[:160]}"
                       + (f" | concern: {cand['concerns'][:120]}" if cand.get("concerns") else ""))
    return "\n".join(out)


def bom_brief(bom: BOM) -> str:
    rows = [f"  - {line.component_id} x{line.quantity} ({line.role}): {line.line_cost_sar:.0f} SAR, "
            f"{line.line_weight_g if line.line_weight_g is not None else 'n/v'} g, {line.key_spec}"
            for line in bom.lines]
    return "BOM:\n" + "\n".join(rows) + f"\n  TOTAL {bom.total_cost_sar:.0f} SAR, {bom.total_mass_g:.0f} g (excl. payload)"


def verification_brief(report: VerificationReport, analysis: DesignAnalysis) -> str:
    lines = [f"VERIFICATION: {report.status} (score {report.score})"]
    for c in report.constraints:
        if c.status != "PASS":
            margin = "" if c.margin_pct is None else f", margin {c.margin_pct:+.1f}%"
            lines.append(f"  [{c.status}] {c.name}: required {c.required}, actual {c.actual}{margin}. {c.detail}")
    lines.append("KEY CALCULATIONS: " + ", ".join(
        f"{n}={analysis.calcs[n].value:g} {analysis.calcs[n].unit}" for n in KEY_CALCS if n in analysis.calcs))
    return "\n".join(lines)


def history_brief(designs: list[dict]) -> str:
    if not designs:
        return "DESIGN HISTORY: none yet."
    rows = ["DESIGN HISTORY:"]
    for d in designs:
        ver = d["verification"]
        failed = [c["name"] for c in ver["constraints"] if c["kind"] == "hard" and c["status"] == "FAIL"]
        runtime = d["analysis"]["calcs"].get("runtime", {}).get("value")
        rows.append(f"  #{d['iteration']} [{d['strategy']}] {ver['status']} score={ver['score']} "
                    f"cost={d['bom']['total_cost_sar']:.0f} SAR runtime={runtime} h "
                    f"failed={failed or '-'} parts={d['fingerprint']}")
    return "\n".join(rows)


def strategy_brief(strategy: str) -> str:
    return f"STRATEGY: {strategy} - {STRATEGY_DESCRIPTIONS.get(strategy, strategy)}"
