"""Deterministic Markdown engineering report.

Every number in the report comes from the graph state (database specs, calculations,
verification results). The LLM contributes only the executive-summary prose.
"""

from __future__ import annotations

from hermes.models import MissionSpec

DISCLAIMER = "**AI-generated engineering proposal - not a certified engineering design.**"
REVIEW_NOTE = ("Physical validation and qualified engineering review are required before "
               "real-world deployment.")

STATUS_TEXT = {
    "VERIFIED": "The final design satisfies the specified computational constraints.",
    "BUDGET_EXHAUSTED": "DESIGN BUDGET EXHAUSTED - no candidate satisfied every hard constraint. "
                        "The best candidate is reported below. Human review required.",
    "STAGNATED": "LOOP / STAGNATION - the design loop stopped improving and all strategies were tried. "
                 "The best candidate is reported below. Human review required.",
    "UNRESOLVED": "The design does not satisfy every specified computational constraint. Human review required.",
    "FAILED": "The mission could not be planned. No design was produced.",
    "PROVIDER_ERROR": "LLM PROVIDER UNAVAILABLE (e.g. out of credits or invalid key) - the design loop stopped early. "
                      "The best candidate so far is reported below. Human review required.",
}


def _table(headers: list[str], rows: list[list]) -> str:
    def cell(v) -> str:
        return "" if v is None else str(v).replace("|", "/").replace("\n", " ")
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]
    return "\n".join(lines)


def _requirements(spec: MissionSpec) -> str:
    r = spec.requirements
    rows = [["Payload", f"{r.payload_kg} kg", "explicit"], ["Runtime", f">= {r.runtime_h_min} h", "explicit"],
            ["Top speed", f">= {r.max_speed_mps} m/s", "explicit"]]
    if r.mass_kg_max is not None:
        rows.append(["Total mass", f"<= {r.mass_kg_max} kg ({'incl.' if r.mass_includes_payload else 'excl.'} payload)",
                     "explicit (payload interpretation: see assumptions)"])
    if r.budget_sar_max is not None:
        rows.append(["Budget", f"<= {r.budget_sar_max:,.0f} SAR", "explicit"])
    for f in r.required_features:
        rows.append(["Feature", f, "derived"])
    return _table(["Requirement", "Value", "Type"], rows)


def _assumptions(spec: MissionSpec) -> str:
    rows = [[a.id, a.statement, a.value or "", a.rationale or ""] for a in spec.assumptions]
    for name, field in type(spec.profile).model_fields.items():
        rows.append([f"P-{name}", field.description, getattr(spec.profile, name), "mission profile (ASSUMED)"])
    return _table(["ID", "Assumption", "Value", "Rationale / origin"], rows)


def _architecture(final: dict) -> str:
    by_cat: dict[str, list[str]] = {}
    for line in final["bom"]["lines"]:
        by_cat.setdefault(line["category"], []).append(f"{line['quantity']} x {line['name']} ({line['component_id']})")
    order = ["motor", "motor_driver", "battery", "regulator", "controller", "imu", "range_sensor", "wheel", "hub",
             "bracket", "caster", "chassis", "structure", "wiring"]
    items = [f"- **{cat}**: " + "; ".join(by_cat[cat]) for cat in order if cat in by_cat]
    return ("Differential-drive platform: two direct-drive gearmotors with wheels on universal hubs, a ball caster, "
            "one battery pack feeding the motor driver directly and the controller through a step-down regulator.\n\n"
            + "\n".join(items))


def _calculations(final: dict) -> str:
    rows = [[c["name"], c["value"], c["unit"], c["provenance"], c["formula"], c.get("note", "")]
            for c in final["analysis"]["calcs"].values()]
    return _table(["Quantity", "Value", "Unit", "Provenance", "Formula / inputs", "Note"], rows)


def _verification(final: dict) -> str:
    rows = [[c["status"], c["kind"], c["name"], c["required"], c["actual"],
             "" if c["margin_pct"] is None else f"{c['margin_pct']:+.1f}%", c["detail"]]
            for c in final["verification"]["constraints"]]
    return _table(["Status", "Kind", "Check", "Required", "Actual", "Margin", "Detail"], rows)


def _history(designs: list[dict]) -> str:
    rows = []
    for d in designs:
        failed = [c["name"] for c in d["verification"]["constraints"] if c["kind"] == "hard" and c["status"] == "FAIL"]
        runtime = d["analysis"]["calcs"].get("runtime", {}).get("value")
        rows.append([f"#{d['iteration']}", d["strategy"], d["verification"]["status"], d["verification"]["score"],
                     f"{d['bom']['total_cost_sar']:,.0f}", runtime, ", ".join(failed) or "-",
                     (d["proposal"].get("changes_from_previous") or d["proposal"].get("rationale", ""))[:160]])
    return _table(["Design", "Strategy", "Verification", "Score", "Cost (SAR)", "Runtime (h)", "Failed hard checks",
                   "Changes / rationale"], rows)


def _critic(feedback: list[dict]) -> str:
    if not feedback:
        return "The critic did not run (no design passed verification)."
    out = []
    for fb in feedback:
        out.append(f"**Design #{fb.get('iteration')} - verdict {fb['verdict']}:** {fb['summary']}")
        out += [f"- [{i['severity']}] *{i['category']}*: {i['finding']} -> {i['recommendation']}" for i in fb["issues"]]
    return "\n".join(out)


def _bom(final: dict) -> str:
    rows = [[line["name"], line["manufacturer"], line["part_number"], line["quantity"],
             line["packs"] if line["pack_qty"] > 1 else "", f"{line['unit_price_usd']:.2f}",
             f"{line['line_cost_sar']:.2f}",
             "not verified" if line["line_weight_g"] is None else line["line_weight_g"], line["key_spec"],
             line["data_quality"]]
            for line in final["bom"]["lines"]]
    b = final["bom"]
    rows.append(["**TOTAL**", "", "", "", "", "", f"**{b['total_cost_sar']:,.2f}**", f"**{b['total_mass_g']}**", "", ""])
    return (_table(["Component", "Manufacturer", "Part number", "Qty", "Packs", "Unit price (USD)", "Total (SAR)",
                    "Weight (g)", "Key specification", "Data"], rows)
            + "\n\nPrices: single-unit list prices (USD) converted at the fixed 3.75 SAR/USD peg; shipping, customs and "
              "VAT excluded.")


def _sources(final: dict, evidence: list[dict]) -> str:
    out = ["**Component specifications (structured database):**"]
    for line in final["bom"]["lines"]:
        out.append(f"- {line['component_id']}: {line['source']}")
    if evidence:
        out.append("\n**Datasheet evidence retrieved by the research agents (RAG):**")
        seen = set()
        for e in evidence:
            key = (e.get("claim"), e.get("source"))
            if key in seen:
                continue
            seen.add(key)
            url = f" <{e['url']}>" if e.get("url") else ""
            out.append(f"- [{e.get('domain')}] {e.get('claim')} - *{e.get('source')}*, page {e.get('page', 'web')}{url}")
    return "\n".join(out)


def _limitations(final: dict, feedback: list[dict]) -> str:
    items = [
        "Specifications are taken from vendor pages and datasheets on the retrieval date; prices and availability change.",
        "Motor performance uses a linear brushed-DC model built from extrapolated stall values; real motors stall earlier when hot.",
        "Energy use depends on the assumed mission profile (cruise speed, grade, rolling resistance); see Assumptions.",
        "Wheel and caster load ratings are not stated by the manufacturer and were not verified.",
    ]
    for c in final["verification"]["constraints"]:
        if c["status"] in ("WARN", "UNVERIFIED"):
            items.append(f"{c['name']}: {c['actual']} ({c['detail']})")
    for fb in feedback[-1:]:
        items += [f"Critic ({i['severity']}, {i['category']}): {i['finding']}" for i in fb["issues"]]
    return "\n".join(f"- {i}" for i in items)


VALIDATION = """\
1. Bench-test each gearmotor at the design operating point and log current and case temperature for 30 minutes.
2. Measure the actual rolling resistance on the target floor/pavement and re-run the energy calculation.
3. Drain-test the battery on the assembled robot carrying the payload; confirm runtime against the 2 h target with margin.
4. Climb the design grade with full payload and measure the peak motor current against the driver rating.
5. Load-test wheels, hubs and the caster at 1.5x the static wheel load.
6. Verify logic-level and connector compatibility between the controller, motor driver and sensors.
7. Have a qualified engineer review battery protection (fusing, BMS/low-voltage cutoff) and wiring gauge."""


def render_report(state: dict, final: dict | None, summary: str) -> str:
    status = state.get("final_status", "UNRESOLVED")
    spec = MissionSpec.model_validate(state["spec"]) if state.get("spec") else None
    designs = state.get("designs") or []
    feedback = state.get("critic_feedback") or []
    title = spec.title if spec else "Engineering mission"
    parts = [f"# HERMES Engineering Report - {title}", DISCLAIMER,
             f"**Final status: {status}.** {STATUS_TEXT.get(status, '')}",
             "## Executive Summary", summary]
    if spec:
        parts += ["## Requirements", _requirements(spec), "## Assumptions", _assumptions(spec)]
        if spec.derived_requirements or spec.unknowns:
            parts += ["### Derived requirements", "\n".join(f"- {d}" for d in spec.derived_requirements) or "-",
                      "### Open questions for a human engineer", "\n".join(f"- {u}" for u in spec.unknowns) or "-"]
    if final:
        label = "Final design" if status == "VERIFIED" else "Best candidate (not fully compliant)"
        parts += [f"## Selected Architecture - {label} #{final['iteration']}", _architecture(final),
                  "## Component Selection", final["proposal"].get("rationale", ""),
                  "## Engineering Calculations", _calculations(final),
                  "## Verification Results", _verification(final)]
    parts += ["## Iteration History", _history(designs) if designs else "No designs were produced.",
              "## Critic Findings", _critic(feedback)]
    if final:
        parts += ["## Final Design", STATUS_TEXT.get(status, ""), "## Bill of Materials", _bom(final),
                  "## Sources / Evidence", _sources(final, state.get("evidence") or []),
                  "## Limitations", _limitations(final, feedback)]
    parts += ["## Recommended Physical Validation", VALIDATION, "---", DISCLAIMER, REVIEW_NOTE]
    return "\n\n".join(parts)
