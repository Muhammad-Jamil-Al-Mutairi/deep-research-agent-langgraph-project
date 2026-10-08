"""Structured component database: build, lookup, safe filtering, provenance."""

import pytest

from hermes.models import BOMLineProposal, DesignProposal
from hermes.tools.engineering.bom import build_bom
from hermes.tools.research.component_db import FilterError, parse_filter


def test_every_component_has_provenance(db):
    for c in db.all():
        assert c.data_quality in ("sourced", "partial", "assumed")
        if c.data_quality != "assumed":
            assert c.source_url.startswith("https://"), c.component_id
        assert c.retrieved_on == "2026-10-07"


def test_get_known_and_unknown(db):
    motor = db.get("POL-4752")
    assert motor.no_load_rpm == 330 and motor.stall_torque_kgcm == 14 and motor.has_encoder is True
    assert db.get("POL-9999") is None


def test_numeric_filters_and_sorting(db):
    big = db.search("battery", ["capacity_mah >= 4000", "chemistry = LiPo"], sort_by="-capacity_mah")
    assert [b.component_id for b in big] == ["OVO-3S-7200-80C", "OVO-3S-6000-80C"]
    enc = db.search("motor", ["has_encoder = 1", "shaft_diameter_mm = 6"])
    assert {m.component_id for m in enc} == {"POL-4751", "POL-4752", "POL-4753"}


@pytest.mark.parametrize("expr", ["price_usd; DROP TABLE components", "notes = x", "1=1 OR price_usd > 0",
                                  "capacity_mah >= lots"])
def test_filter_injection_and_bad_values_are_rejected(expr):
    with pytest.raises(FilterError):
        parse_filter(expr)


def test_bom_packs_prices_and_unknown_ids(db):
    proposal = DesignProposal(strategy="t", rationale="", lines=[
        BOMLineProposal(component_id="POL-1435", quantity=2, role="wheel"),  # sold in pairs -> 1 pack
        BOMLineProposal(component_id="POL-1083", quantity=3, role="hub"),  # 2-packs -> 2 packs
        BOMLineProposal(component_id="NOPE-1", quantity=1, role="ghost"),
    ])
    bom = build_bom(proposal, db)
    wheel, hub = bom.lines
    assert wheel.packs == 1 and wheel.line_cost_usd == 9.49 and wheel.line_weight_g == pytest.approx(45.36, abs=0.05)
    assert hub.packs == 2 and hub.line_cost_usd == pytest.approx(25.90)
    assert bom.unknown_ids == ["NOPE-1"]
    assert bom.total_cost_sar == pytest.approx((9.49 + 25.90) * 3.75, abs=0.01)


def test_unverified_weight_is_reported_not_guessed(db):
    bom = build_bom(DesignProposal(strategy="t", rationale="", lines=[
        BOMLineProposal(component_id="ADA-4646", quantity=1, role="imu")]), db)
    assert bom.lines[0].line_weight_g is None
    assert bom.unverified_mass_items == ["ADA-4646"]
