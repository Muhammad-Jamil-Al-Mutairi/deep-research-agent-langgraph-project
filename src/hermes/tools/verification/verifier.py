"""Deterministic verification engine - the only component allowed to decide PASS/FAIL.

Hard constraints gate the design. Soft constraints produce WARN/UNVERIFIED results
that the Critic agent reviews, but they never make a failing design pass.
"""

from __future__ import annotations

from collections.abc import Callable

from hermes.models.components import Component
from hermes.models.design import BOM
from hermes.models.requirements import Requirements
from hermes.models.verification import ConstraintResult, VerificationReport
from hermes.tools.engineering.calculator import DesignAnalysis
from hermes.tools.research.component_db import ComponentDB

_FEATURE_CHECKS: dict[str, tuple[str, Callable[[BOM, dict[str, Component]], bool]]] = {
    "wheel_encoders": ("drive motors with encoders",
                       lambda bom, c: any(c[x.component_id].has_encoder for x in bom.by_category("motor"))),
    "imu": ("an IMU", lambda bom, c: bool(bom.by_category("imu"))),
    "range_sensor": ("a range sensor", lambda bom, c: bool(bom.by_category("range_sensor"))),
}


def fmt(x: float) -> str:
    """Readable number: thousands without exponent, small values to 3 significant figures."""
    return f"{x:,.0f}" if abs(x) >= 100 else f"{x:.3g}"


def _min_check(name: str, actual: float, required: float, unit: str, detail: str = "",
               kind: str = "hard") -> ConstraintResult:
    """actual must be >= required."""
    margin = (actual - required) / required * 100.0 if required else None
    status = "PASS" if actual >= required else ("FAIL" if kind == "hard" else "WARN")
    return ConstraintResult(name=name, kind=kind, required=f">= {fmt(required)} {unit}", actual=f"{fmt(actual)} {unit}",
                            status=status, margin_pct=None if margin is None else round(margin, 1), detail=detail)


def _max_check(name: str, actual: float, limit: float, unit: str, detail: str = "",
               kind: str = "hard") -> ConstraintResult:
    """actual must be <= limit."""
    margin = (limit - actual) / limit * 100.0 if limit else None
    status = "PASS" if actual <= limit else ("FAIL" if kind == "hard" else "WARN")
    return ConstraintResult(name=name, kind=kind, required=f"<= {fmt(limit)} {unit}", actual=f"{fmt(actual)} {unit}",
                            status=status, margin_pct=None if margin is None else round(margin, 1), detail=detail)


def _bool_check(name: str, ok: bool, required: str, actual: str, kind: str = "hard",
                detail: str = "") -> ConstraintResult:
    status = "PASS" if ok else ("FAIL" if kind == "hard" else "WARN")
    return ConstraintResult(name=name, kind=kind, required=required, actual=actual, status=status, detail=detail)


def _unverified(name: str, required: str, detail: str) -> ConstraintResult:
    return ConstraintResult(name=name, kind="soft", required=required, actual="Specification not verified.",
                            status="UNVERIFIED", detail=detail)


def score(constraints: list[ConstraintResult]) -> float:
    """0 if every hard constraint passes, else the negative sum of normalised shortfalls (capped at 1 each)."""
    total = 0.0
    for c in constraints:
        if c.kind == "hard" and c.status == "FAIL":
            shortfall = 1.0 if c.margin_pct is None else min(1.0, abs(c.margin_pct) / 100.0)
            total -= shortfall
    return round(total, 4)


def verify_design(bom: BOM, analysis: DesignAnalysis, req: Requirements, db: ComponentDB) -> VerificationReport:
    out: list[ConstraintResult] = []
    comps = {line.component_id: c for line in bom.lines if (c := db.get(line.component_id))}
    cats = {line.category for line in bom.lines}

    # ---- 1. design validity / completeness ------------------------------------------
    out.append(_bool_check("known_components", not bom.unknown_ids, "all component ids exist in the database",
                           "unknown: " + ", ".join(bom.unknown_ids) if bom.unknown_ids else "all known"))
    required_cats = ["motor", "motor_driver", "battery", "controller", "wheel", "hub", "bracket", "caster", "chassis"]
    missing = [c for c in required_cats if c not in cats]
    out.append(_bool_check("completeness", not missing, "drivetrain, power, control and structure present",
                           "missing: " + ", ".join(missing) if missing else "complete"))
    for feature in req.required_features:
        label, check = _FEATURE_CHECKS[feature]
        out.append(_bool_check(f"feature_{feature}", check(bom, comps), f"design includes {label}",
                               "present" if check(bom, comps) else "absent"))
    if analysis.issues:
        out.append(_bool_check("analysis", False, "design can be analysed", "; ".join(analysis.issues)))
        return VerificationReport(status="FAIL", constraints=out, score=score(out))

    motor_line = bom.by_category("motor")[0]
    motor = comps[motor_line.component_id]
    battery = comps[bom.by_category("battery")[0].component_id]
    n = motor_line.quantity
    v = analysis.value("supply_voltage")

    # ---- 2. mechanical compatibility --------------------------------------------------
    wheels = sum(line.quantity for line in bom.by_category("wheel"))
    out.append(_min_check("drive_wheels", wheels, n, "wheels", "one wheel per drive motor"))
    hubs_ok = sum(line.quantity for line in bom.by_category("hub")
                  if comps[line.component_id].fits_shaft_mm == motor.shaft_diameter_mm)
    out.append(_min_check("hub_shaft_match", hubs_ok, n, "hubs",
                          f"hubs must fit the {motor.shaft_diameter_mm:.0f} mm motor shaft"))
    brackets_ok = sum(line.quantity for line in bom.by_category("bracket")
                      if comps[line.component_id].fits_motor_family == motor.motor_family)
    out.append(_min_check("bracket_match", brackets_ok, n, "brackets", f"brackets must fit {motor.motor_family} gearmotors"))

    # ---- 3. electrical compatibility -------------------------------------------------
    channels = sum((comps[x.component_id].channels or 0) * x.quantity for x in bom.by_category("motor_driver"))
    out.append(_min_check("driver_channels", channels, n, "channels"))
    for line in bom.by_category("motor_driver"):
        d = comps[line.component_id]
        out.append(_bool_check(f"driver_voltage[{d.component_id}]",
                               d.voltage_min_v <= v <= d.voltage_max_v,
                               f"{d.voltage_min_v}-{d.voltage_max_v} V", f"{v} V battery"))
        out.append(_min_check(f"driver_current[{d.component_id}]", d.cont_current_a,
                              analysis.value("motor_current_peak"), "A",
                              "driver continuous rating vs motor current at design peak torque"))
        out.append(_min_check(f"driver_stall_rating[{d.component_id}]", d.cont_current_a,
                              analysis.value("motor_stall_current_at_supply"), "A",
                              "Pololu recommends drivers rated above motor stall current", kind="soft"))
        ctrl = bom.by_category("controller")
        if ctrl and d.logic_v_min is not None:
            lv = comps[ctrl[0].component_id].logic_v_max
            out.append(_bool_check(f"logic_level[{d.component_id}]", d.logic_v_min <= lv <= d.logic_v_max,
                                   f"{d.logic_v_min}-{d.logic_v_max} V logic", f"{lv} V controller", kind="soft"))
        elif ctrl:
            out.append(_unverified(f"logic_level[{d.component_id}]", "controller logic within driver logic range",
                                   "driver logic-level range not stated in the source"))
    if motor.rated_voltage_v:
        out.append(_max_check("motor_voltage", v, motor.rated_voltage_v * 1.10, "V",
                              "battery nominal voltage vs motor rated voltage (+10%)", kind="soft"))
    # Logic power path: the controller needs a regulator if the battery exceeds its input range.
    ctrl = bom.by_category("controller")
    if ctrl:
        c = comps[ctrl[0].component_id]
        max_in = c.voltage_max_v or c.logic_v_max or 5.5
        regs = bom.by_category("regulator")
        if v > max_in:
            out.append(_bool_check("logic_supply", bool(regs), f"regulator required (battery {v} V > {max_in} V)",
                                   "regulator present" if regs else "no regulator"))
        for line in regs:
            r = comps[line.component_id]
            out.append(_bool_check(f"regulator_input[{r.component_id}]", r.voltage_min_v <= v <= r.voltage_max_v,
                                   f"{r.voltage_min_v}-{r.voltage_max_v} V", f"{v} V battery"))
            if (i_out := analysis.value("regulator_output_current")) is not None:
                out.append(_max_check(f"regulator_current[{r.component_id}]", i_out, r.cont_current_a, "A"))

    # ---- 4. performance ---------------------------------------------------------------
    out.append(_min_check("speed", analysis.value("achievable_speed"), req.max_speed_mps, "m/s",
                          "full-throttle speed on level ground with payload"))
    out.append(_max_check("torque_continuous", analysis.value("torque_continuous_design"),
                          motor.cont_torque_limit_nm or analysis.value("motor_stall_torque_at_supply") * 0.25, "N-m",
                          "climb torque x safety factor vs manufacturer continuous-load limit"))
    peak_limit = min(x for x in (motor.peak_torque_limit_nm, analysis.value("motor_stall_torque_at_supply")) if x)
    out.append(_max_check("torque_peak", analysis.value("torque_peak_design"), peak_limit, "N-m",
                          "accelerating up the design grade x safety factor vs instantaneous limit / stall torque"))
    out.append(_max_check("motor_thermal", analysis.value("motor_current_continuous"),
                          analysis.value("motor_thermal_current_limit"), "A",
                          "continuous current vs 25% of stall current", kind="soft"))
    out.append(_min_check("runtime", analysis.value("runtime"), req.runtime_h_min, "h"))
    if (i_max := analysis.value("battery_max_current")) is not None:
        out.append(_max_check("battery_current", analysis.value("battery_peak_current"), i_max, "A"))
    else:
        out.append(_unverified("battery_current", "pack rated for peak current",
                               f"{battery.component_id} maximum discharge current not stated"))

    # ---- 5. mass and budget ---------------------------------------------------------
    if req.mass_kg_max is not None:
        mass = analysis.value("total_mass") if req.mass_includes_payload else analysis.value("component_mass")
        out.append(_max_check("mass", mass, req.mass_kg_max, "kg",
                              "includes payload" if req.mass_includes_payload else "excludes payload"))
    if req.budget_sar_max is not None:
        out.append(_max_check("budget", bom.total_cost_sar, req.budget_sar_max, "SAR"))

    # ---- 6. evidence quality ----------------------------------------------------------
    if analysis.unverified:
        out.append(ConstraintResult(name="evidence_coverage", kind="soft", required="all specs verified",
                                    actual=f"{len(analysis.unverified)} unverified", status="UNVERIFIED",
                                    detail="; ".join(analysis.unverified)))
    assumed = [line.component_id for line in bom.lines if line.data_quality == "assumed"]
    if assumed:
        out.append(ConstraintResult(name="assumed_items", kind="soft", required="sourced parts",
                                    actual=", ".join(assumed), status="WARN",
                                    detail="mass/cost of these items are engineering allowances"))

    hard_fail = any(c.kind == "hard" and c.status == "FAIL" for c in out)
    return VerificationReport(status="FAIL" if hard_fail else "PASS", constraints=out, score=score(out))
