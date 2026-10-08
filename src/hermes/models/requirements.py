"""Mission requirements produced by the Mission Architect agent.

Explicit requirements (stated by the user), derived requirements and assumptions
are kept apart so the report never presents an assumption as a fact.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

Domain = Literal["motor", "battery", "mechanical", "electronics"]
DOMAINS: tuple[Domain, ...] = ("motor", "battery", "mechanical", "electronics")
Feature = Literal["wheel_encoders", "imu", "range_sensor"]


class Requirements(BaseModel):
    """Numeric requirements. Hard constraints are checked by the verifier."""

    payload_kg: float = Field(gt=0, description="Payload mass the robot must carry, kg.")
    runtime_h_min: float = Field(gt=0, description="Minimum continuous operating time, hours.")
    max_speed_mps: float = Field(
        gt=0,
        description="Top speed the design must be able to reach on level ground, m/s (always > 0). 'maximum speed of "
                    "1.5 m/s', 'up to 0.8 m/s' and 'at least 0.8 m/s' all mean the robot must reach that speed, so "
                    "use that number. If no speed is given, use 1.0 and record it as an assumption.",
    )
    mass_kg_max: float | None = Field(default=None, gt=0, description="Maximum total mass, kg (null if not stated).")
    mass_includes_payload: bool = Field(
        default=True,
        description="Whether mass_kg_max includes the payload. If the user did not say, choose true (conservative) and record it as an assumption.",
    )
    budget_sar_max: float | None = Field(default=None, gt=0, description="Maximum BOM cost in SAR (null if not stated).")
    required_features: list[Feature] = Field(
        default_factory=list,
        description="Functional features the application needs, e.g. wheel_encoders for odometry, imu for heading, range_sensor for obstacles.",
    )


class MissionProfile(BaseModel):
    """Operating assumptions used by the deterministic calculations.

    Every field is an ASSUMPTION unless the user stated it. Defaults are
    conservative values for a small indoor/outdoor delivery robot.
    """

    cruise_speed_mps: float = Field(default=1.0, ge=0.1, le=5, description="Average driving speed used for the energy estimate, m/s.")
    design_grade_deg: float = Field(default=5.0, ge=0, le=20, description="Steepest ramp the robot must climb, degrees.")
    fraction_time_on_grade: float = Field(default=0.10, ge=0, le=0.5, description="Fraction of drive time spent climbing the design grade.")
    acceleration_mps2: float = Field(default=0.5, ge=0.1, le=3, description="Peak acceleration requirement, m/s^2.")
    rolling_resistance_coeff: float = Field(default=0.02, ge=0.005, le=0.1, description="Rolling resistance coefficient of small hard wheels.")
    torque_safety_factor: float = Field(default=1.5, ge=1.2, le=4, description="Safety factor applied to torque requirements.")
    battery_usable_fraction: float = Field(default=0.80, ge=0.5, le=0.9, description="Fraction of nameplate battery energy that is usable.")
    regulator_efficiency: float = Field(default=0.85, ge=0.5, le=0.98, description="Efficiency of the logic step-down regulator.")
    driver_efficiency: float = Field(default=0.95, ge=0.5, le=0.99, description="Motor driver efficiency.")
    unverified_device_power_w: float = Field(
        default=0.25, ge=0.05, le=3, description="Power allowance for an electronic device whose supply current is not verified, W."
    )


ProfileField = Literal[
    "cruise_speed_mps", "design_grade_deg", "fraction_time_on_grade", "acceleration_mps2",
    "rolling_resistance_coeff", "torque_safety_factor", "battery_usable_fraction", "regulator_efficiency",
    "driver_efficiency", "unverified_device_power_w",
]


class ProfileOverride(BaseModel):
    """A justified change to one mission-profile default (the LLM may not set profile numbers freely)."""

    field: ProfileField
    value: float
    justification: str = Field(description="Quote the part of the user request that justifies changing the default.")


class RequirementsDraft(Requirements):
    """LLM-facing variant of Requirements: the three core numbers may come back as 0.

    Seen live: the model returned 0 for every value below 1 ("0.8 m/s" -> 0) and re-sent the same
    rejected answer until its call budget ran out. Accepting 0 here lets code repair the value from
    the request text (`reconcile_with_text`) before the strict Requirements validation.
    """

    payload_kg: float = Field(ge=0, description=Requirements.model_fields["payload_kg"].description)
    runtime_h_min: float = Field(ge=0, description=Requirements.model_fields["runtime_h_min"].description)
    max_speed_mps: float = Field(ge=0, description=Requirements.model_fields["max_speed_mps"].description)


# ---- deterministic cross-check of the LLM's numbers against the request text ----------------

_NUM = r"(\d+(?:\.\d+)?)"
_TEXT_PATTERNS: dict[str, list[tuple[str, float]]] = {
    "max_speed_mps": [(_NUM + r"\s*(?:m/s|met(?:er|re)s? per second)", 1.0), (_NUM + r"\s*km/h", 1 / 3.6)],
    "runtime_h_min": [(_NUM + r"\s*(?:h|hrs?|hours?)\b", 1.0)],
    "payload_kg": [(r"(?:payload|carr(?:y|ies|ying))\D{0,25}?" + _NUM + r"\s*kg", 1.0),
                   (_NUM + r"\s*kg\s+payload", 1.0)],
}


def values_in_text(field: str, text: str) -> list[float]:
    """Numbers the request states for a requirement field, converted to the field's unit."""
    found = {round(float(m) * scale, 4) for pattern, scale in _TEXT_PATTERNS.get(field, [])
             for m in re.findall(pattern, text, flags=re.IGNORECASE)}
    return sorted(found)


def reconcile_with_text(values: dict, text: str) -> tuple[dict, list[str], list[str]]:
    """Fill zeroed fields from an unambiguous number in the request; flag values the request contradicts.

    Returns (values, corrections, mismatches).
    """
    values, corrections, mismatches = dict(values), [], []
    for field in _TEXT_PATTERNS:
        stated, value = values_in_text(field, text), values.get(field)
        if not value and len(stated) == 1:
            values[field] = stated[0]
            corrections.append((field, value, stated[0]))
        elif value and stated and not any(abs(value - x) <= 0.01 * x for x in stated):
            mismatches.append(f"{field} = {value} does not match the value(s) stated in the request {stated}")
    return values, corrections, mismatches


class Assumption(BaseModel):
    id: str = Field(description="Short id such as A1.")
    statement: str
    value: str | None = None
    rationale: str | None = None


class ResearchTask(BaseModel):
    domain: Domain
    objective: str = Field(description="What this research stage must find, including numeric targets where known.")


class MissionDraft(BaseModel):
    """Structured output of the Mission Architect agent, validated into a MissionSpec by code."""

    title: str = Field(description="Short mission title.")
    requirements: RequirementsDraft
    profile_overrides: list[ProfileOverride] = Field(
        default_factory=list,
        description="Usually EMPTY. Override a default operating assumption only when the request explicitly "
                    "implies it (e.g. 'flat indoor floors' -> design_grade_deg 1).")
    assumptions: list[Assumption] = Field(default_factory=list, description="Assumptions you made that the user did not state.")
    derived_requirements: list[str] = Field(default_factory=list, description="Requirements derived from the explicit ones, with reasoning.")
    unknowns: list[str] = Field(default_factory=list, description="Open questions a human engineer should confirm.")
    research_plan: list[ResearchTask] = Field(default_factory=list, description="One task per domain: motor, battery, mechanical, electronics.")

    def to_spec(self, request_text: str | None = None) -> tuple[MissionSpec, list[str]]:
        """Validate the draft into a MissionSpec.

        Numeric requirements are cross-checked against the request text (zeroed values repaired, contradictions
        flagged as open questions). Profile overrides go through MissionProfile validation; out-of-range ones
        are rejected and the default is kept.
        """
        profile, rejected, assumptions = MissionProfile(), [], list(self.assumptions)
        values, unknowns = self.requirements.model_dump(), list(self.unknowns)
        if request_text:
            values, corrections, mismatches = reconcile_with_text(values, request_text)
            for i, (field, got, fixed) in enumerate(corrections, 1):
                assumptions.append(Assumption(
                    id=f"R{i}", statement=f"Requirement {field} taken from the request text", value=str(fixed),
                    rationale=f"the planner returned {got}; deterministic cross-check against the request"))
            unknowns += [f"Check: {m}" for m in mismatches]
        try:
            requirements = Requirements.model_validate(values)
        except ValidationError as exc:
            raise ValueError(f"requirements are invalid even after the cross-check with the request: "
                             f"{[e['loc'][-1] for e in exc.errors()]}") from exc
        for i, ov in enumerate(self.profile_overrides, 1):
            try:
                profile = MissionProfile.model_validate({**profile.model_dump(), ov.field: ov.value})
            except ValueError:
                rejected.append(f"{ov.field}={ov.value} (outside the plausible range; default kept)")
                continue
            assumptions.append(Assumption(id=f"P{i}", statement=f"Profile override: {ov.field} = {ov.value}",
                                          value=str(ov.value), rationale=ov.justification))
        spec = MissionSpec(title=self.title, requirements=requirements, profile=profile, assumptions=assumptions,
                           derived_requirements=self.derived_requirements, unknowns=unknowns,
                           research_plan=self.research_plan)
        return spec, rejected


class MissionSpec(BaseModel):
    """Validated mission specification used by the rest of the graph."""

    title: str
    requirements: Requirements
    profile: MissionProfile = Field(default_factory=MissionProfile)
    assumptions: list[Assumption] = Field(default_factory=list)
    derived_requirements: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    research_plan: list[ResearchTask] = Field(default_factory=list)
