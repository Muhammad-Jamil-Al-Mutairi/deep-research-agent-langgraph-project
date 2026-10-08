"""Verification engine: the only component that decides PASS/FAIL."""

import pytest

from hermes.demo import (
    BALANCED_OVER_BUDGET,
    ECONOMY_DESIGN,
    PASSING_DESIGN,
    REFINED_DESIGN,
    delivery_robot_spec,
)
from hermes.models import BOMLineProposal, DesignProposal
from hermes.tools.engineering.bom import build_bom
from hermes.tools.engineering.calculator import analyse_design
from hermes.tools.verification.verifier import score, verify_design


def run(design, db, spec=None):
    spec = spec or delivery_robot_spec()
    bom = build_bom(design, db)
    analysis = analyse_design(bom, spec.requirements, spec.profile, db)
    return verify_design(bom, analysis, spec.requirements, db), analysis, bom


def by_name(report):
    return {c.name: c for c in report.constraints}


def test_economy_design_fails_on_driver_current_and_encoders(db):
    report, analysis, _ = run(ECONOMY_DESIGN, db)
    checks = by_name(report)
    assert report.status == "FAIL"
    assert checks["driver_current[POL-713]"].status == "FAIL"  # 1 A driver vs ~1.1 A peak motor current
    assert checks["feature_wheel_encoders"].status == "FAIL"
    assert checks["runtime"].status == "PASS"
    assert report.score < 0


def test_balanced_design_fails_only_on_budget(db):
    report, _, bom = run(BALANCED_OVER_BUDGET, db)
    assert [c.name for c in report.failed] == ["budget"]
    assert bom.total_cost_sar > 1500
    assert by_name(report)["budget"].margin_pct == pytest.approx(-3.2, abs=0.1)


@pytest.mark.parametrize("design", [PASSING_DESIGN, REFINED_DESIGN])
def test_compliant_designs_pass_with_warnings_not_failures(db, design):
    report, analysis, _ = run(design, db)
    assert report.status == "PASS" and report.score == 0
    assert report.warnings  # unverified evidence is surfaced, never hidden
    assert analysis.value("runtime") >= 2.0


def test_soft_warnings_never_make_a_design_fail(db):
    report, _, _ = run(PASSING_DESIGN, db)
    soft = [c for c in report.constraints if c.kind == "soft"]
    assert any(c.status in ("WARN", "UNVERIFIED") for c in soft)
    assert report.status == "PASS"


def test_mass_limit_respects_payload_interpretation(db):
    tight = delivery_robot_spec(mass_kg_max=3.0)
    incl, _, _ = run(PASSING_DESIGN, db, tight)
    assert by_name(incl)["mass"].status == "FAIL"  # 3.44 kg incl. payload
    excl, _, _ = run(PASSING_DESIGN, db, delivery_robot_spec(mass_kg_max=3.0, mass_includes_payload=False))
    assert by_name(excl)["mass"].status == "PASS"  # 1.44 kg without payload


def test_mechanical_mismatch_is_caught(db):
    wrong_hubs = DesignProposal(strategy="t", rationale="", lines=[
        ln if ln.component_id != "POL-1081" else BOMLineProposal(component_id="POL-1083", quantity=2, role="hub")
        for ln in PASSING_DESIGN.lines])  # 6 mm hubs on 4 mm shafts
    report, _, _ = run(wrong_hubs, db)
    assert by_name(report)["hub_shaft_match"].status == "FAIL"


def test_unknown_or_missing_parts_fail_cleanly(db):
    report, analysis, _ = run(DesignProposal(strategy="t", rationale="", lines=[
        BOMLineProposal(component_id="MADE-UP-MOTOR", quantity=2, role="motor")]), db)
    checks = by_name(report)
    assert report.status == "FAIL"
    assert checks["known_components"].status == "FAIL"
    assert checks["completeness"].status == "FAIL"
    assert analysis.issues  # analysis refused rather than inventing numbers


def test_score_is_zero_only_when_all_hard_checks_pass(db):
    passing, _, _ = run(PASSING_DESIGN, db)
    failing, _, _ = run(ECONOMY_DESIGN, db)
    assert score(passing.constraints) == 0
    assert score(failing.constraints) < score(run(BALANCED_OVER_BUDGET, db)[0].constraints) < 0
