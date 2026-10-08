"""The planner cannot silently change engineering assumptions."""

from hermes.models import MissionDraft, MissionProfile, ProfileOverride


def draft(*overrides):
    return MissionDraft(title="t", requirements={"payload_kg": 2, "runtime_h_min": 2, "max_speed_mps": 1.5},
                        profile_overrides=list(overrides))


def test_no_overrides_keeps_documented_defaults():
    spec, rejected = draft().to_spec()
    assert spec.profile == MissionProfile() and not rejected


def test_justified_override_is_applied_and_recorded_as_assumption():
    spec, rejected = draft(ProfileOverride(field="design_grade_deg", value=1.0,
                                           justification="'flat office floors'")).to_spec()
    assert spec.profile.design_grade_deg == 1.0 and not rejected
    assert any(a.id == "P1" and "flat office floors" in a.rationale for a in spec.assumptions)


def test_implausible_overrides_are_rejected_and_defaults_kept():
    # values a live model actually produced in a smoke test
    spec, rejected = draft(ProfileOverride(field="rolling_resistance_coeff", value=0.2, justification="-"),
                           ProfileOverride(field="acceleration_mps2", value=0.0, justification="-"),
                           ProfileOverride(field="unverified_device_power_w", value=0.0, justification="-")).to_spec()
    assert len(rejected) == 3
    assert spec.profile == MissionProfile()


INDOOR = ("Design an indoor robot cart that carries 1 kg for at least 4 hours at up to 0.8 m/s on flat office floors. "
          "It must weigh under 5 kg including the load and cost less than 1200 SAR.")


def test_zeroed_requirement_is_repaired_from_the_request_text():
    """Seen live: the model returned 0 for '0.8 m/s'. Code repairs it from the request and records why."""
    d = MissionDraft(title="t", requirements={"payload_kg": 1, "runtime_h_min": 4, "max_speed_mps": 0})
    spec, _ = d.to_spec(INDOOR)
    assert spec.requirements.max_speed_mps == 0.8
    fix = [a for a in spec.assumptions if a.id.startswith("R")]
    assert fix and "max_speed_mps" in fix[0].statement and "returned 0" in fix[0].rationale


def test_contradicted_requirement_becomes_an_open_question():
    d = MissionDraft(title="t", requirements={"payload_kg": 1, "runtime_h_min": 2, "max_speed_mps": 0.8})
    spec, _ = d.to_spec(INDOOR)
    assert spec.requirements.runtime_h_min == 2  # never silently overridden
    assert any(u.startswith("Check: runtime_h_min") for u in spec.unknowns)


def test_unrepairable_zero_fails_loudly():
    import pytest

    d = MissionDraft(title="t", requirements={"payload_kg": 1, "runtime_h_min": 4, "max_speed_mps": 0})
    with pytest.raises(ValueError, match="max_speed_mps"):
        d.to_spec("Design a robot that carries 1 kg for 4 hours.")  # no speed stated anywhere
