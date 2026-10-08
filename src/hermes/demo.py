"""Demonstration missions and scripted fixtures for offline runs (tests and reliability demos)."""

from __future__ import annotations

from hermes.models import (
    Assumption,
    BOMLineProposal,
    CriticIssue,
    Critique,
    DesignProposal,
    MissionSpec,
    ReplanDecision,
    Requirements,
    ResearchTask,
)

DELIVERY_ROBOT_REQUEST = (
    "Design a small autonomous delivery robot with a 2 kg payload, at least 2 hours runtime, "
    "maximum speed of 1.5 m/s, total mass below 8 kg, and budget below 1500 SAR. "
    "Use commercially available components."
)

INFEASIBLE_REQUEST = (
    "Design a small autonomous delivery robot with a 2 kg payload, at least 12 hours runtime, "
    "maximum speed of 2.5 m/s, total mass below 3 kg, and budget below 600 SAR."
)


def delivery_robot_spec(**overrides) -> MissionSpec:
    """The MissionSpec a correct Mission Architect produces for DELIVERY_ROBOT_REQUEST."""
    req = Requirements(payload_kg=2.0, runtime_h_min=2.0, max_speed_mps=1.5, mass_kg_max=8.0,
                       mass_includes_payload=True, budget_sar_max=1500.0,
                       required_features=["wheel_encoders", "imu", "range_sensor"])
    req = req.model_copy(update=overrides)
    return MissionSpec(
        title="Small autonomous delivery robot",
        requirements=req,
        assumptions=[Assumption(id="A1", statement="The 8 kg mass limit includes the 2 kg payload.",
                                value="mass_includes_payload=true", rationale="conservative interpretation")],
        derived_requirements=["Wheel encoders for odometry", "IMU for heading", "Range sensor for obstacles"],
        unknowns=["Operating surface (indoor floor vs pavement)", "Maximum ramp angle on the route"],
        research_plan=[ResearchTask(domain=d, objective=f"shortlist {d} parts for a {req.payload_kg} kg payload robot")
                       for d in ("motor", "battery", "mechanical", "electronics")],
    )


def _lines(*pairs: tuple[str, int, str]) -> list[BOMLineProposal]:
    return [BOMLineProposal(component_id=c, quantity=q, role=r) for c, q, r in pairs]


COMMON_PARTS = [("POL-2858", 1, "5 V logic regulator"), ("HRM-PAYLOAD-BIN", 1, "payload bin"),
                ("HRM-WIRING-KIT", 1, "wiring and fasteners")]

ECONOMY_DESIGN = DesignProposal(
    strategy="economy",
    lines=_lines(("POL-3203", 2, "drive motor"), ("POL-1081", 2, "hub"), ("POL-2676", 2, "bracket"),
                 ("POL-1430", 2, "wheel"), ("POL-2691", 1, "caster"), ("POL-713", 1, "motor driver"),
                 ("OVO-3S-1400-50C", 1, "battery"), ("ADA-5526", 1, "controller"), ("ADA-4646", 1, "IMU"),
                 ("POL-3415", 1, "range sensor"), ("HRM-CHASSIS-PLY6", 1, "chassis"), *COMMON_PARTS),
    rationale="Cheapest part in every role: 25D motors without encoders, TB6612FNG driver, 1400 mAh pack, Pico W.",
)

BALANCED_OVER_BUDGET = DesignProposal(
    strategy="balanced",
    lines=_lines(("POL-4751", 2, "drive motor with encoder"), ("POL-1083", 2, "hub"), ("POL-1084", 2, "bracket"),
                 ("POL-1435", 2, "wheel"), ("POL-2692", 1, "caster"), ("POL-2507", 1, "motor driver"),
                 ("OVO-3S-6000-80C", 1, "battery"), ("ADA-5400", 1, "controller"), ("ADA-4646", 1, "IMU"),
                 ("POL-3415", 1, "range sensor"), ("HRM-CHASSIS-AL3", 1, "chassis"), *COMMON_PARTS),
    rationale="37D encoder motors, VNH5019 driver rated above stall current, 6000 mAh pack, ESP32 controller.",
    changes_from_previous="Encoders added, driver upgraded to 12 A, battery upgraded to 66.6 Wh.",
)

PASSING_DESIGN = DesignProposal(
    strategy="balanced",
    lines=_lines(("POL-4843", 2, "drive motor with encoder"), ("POL-1081", 2, "hub"), ("POL-2676", 2, "bracket"),
                 ("POL-1435", 2, "wheel"), ("POL-2692", 1, "caster"), ("POL-2507", 1, "motor driver"),
                 ("OVO-3S-6000-80C", 1, "battery"), ("ADA-5400", 1, "controller"), ("ADA-4646", 1, "IMU"),
                 ("POL-3415", 1, "range sensor"), ("HRM-CHASSIS-PLY6", 1, "chassis"), *COMMON_PARTS),
    rationale="25D encoder motors and a plywood chassis bring the encoder design under budget.",
    changes_from_previous="37D -> 25D encoder gearmotors (4 mm hubs and 25D brackets), aluminium -> plywood chassis.",
)

MARGIN_CRITIQUE = Critique(
    verdict="REVISE",
    summary="Passes verification, but the 66.6 Wh pack gives several times the required runtime.",
    issues=[CriticIssue(severity="medium", category="margin",
                        finding="Runtime margin is excessive; the 6000 mAh pack adds mass and cost the mission does not need.",
                        recommendation="Use the 2200 mAh 3S pack (OVO-3S-2200-50C) if runtime still clears 2 h with margin.")],
)

REFINED_DESIGN = PASSING_DESIGN.model_copy(update={
    "lines": [ln if ln.component_id != "OVO-3S-6000-80C" else BOMLineProposal(component_id="OVO-3S-2200-50C",
                                                                               quantity=1, role="battery")
              for ln in PASSING_DESIGN.lines],
    "rationale": "Right-sized battery: 2200 mAh 3S pack keeps runtime above 2 h with lower mass and cost.",
    "changes_from_previous": "OVO-3S-6000-80C -> OVO-3S-2200-50C after the critic flagged excessive runtime margin.",
})


SCRIPTED_REPLANS = [
    ReplanDecision(diagnosis="TB6612FNG is rated 1 A/channel but the motors draw more at peak; no encoders.",
                   root_causes=["driver under-rated", "missing wheel encoders"],
                   change_plan=["driver rated above motor stall current", "encoder gearmotors"],
                   next_strategy="balanced"),
    ReplanDecision(diagnosis="Budget exceeded by 3.2% with 37D encoder motors and an aluminium chassis.",
                   root_causes=["37D encoder motors and aluminium plate are the costliest items"],
                   change_plan=["25D encoder motors with 4 mm hubs and 25D brackets", "plywood chassis"]),
    ReplanDecision(diagnosis="Critic: runtime margin is excessive.", root_causes=["oversized battery"],
                   change_plan=["2200 mAh 3S pack"]),
]
