"""Streamlit UI: the helpers behind app.py (always tested) and an app smoke test (when streamlit is installed)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hermes.graph import build_graph, run_mission
from hermes.ui_support import (
    CallbackLog,
    bom_rows,
    build_team,
    check_rows,
    event_line,
    evidence_rows,
    iteration_rows,
    metric_values,
)

ROOT = Path(__file__).resolve().parents[2]


def test_offline_ui_mission_streams_events_and_fills_every_view():
    seen = []
    log = CallbackLog(seen.append)
    team = build_team(live=False, log=log)
    final = asyncio.run(run_mission(build_graph(team, log=log), "ui test", mission_id="ui-offline"))

    assert final["final_status"] == "VERIFIED"
    assert [e["seq"] for e in seen] == list(range(1, len(seen) + 1))  # every event reached the live feed
    assert any(e["kind"] == "verify" for e in seen)
    assert "reporter" in event_line(seen[-1])  # the feed ends with the report event
    labels = dict(metric_values(final))
    assert {"BOM cost", "Top speed", "Runtime"} <= set(labels)
    assert bom_rows(final) and all(r["Total SAR"] > 0 for r in bom_rows(final))
    assert {r["Status"] for r in check_rows(final)} <= {"PASS", "WARN", "UNVERIFIED"}
    assert [r["Verification"] for r in iteration_rows(final)] == ["FAIL", "FAIL", "PASS", "PASS"]
    assert evidence_rows(final) and all(r["Source"] for r in evidence_rows(final))


def test_callback_errors_never_break_the_mission_log():
    def broken(_record):
        raise RuntimeError("display failed")

    log = CallbackLog(broken)
    assert log.event("designer", "design", "still recorded")["seq"] == 1


def test_streamlit_app_renders_offline():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not at.exception
    at.radio[0].set_value("Offline replay").run()  # never spend credits in tests
    assert not at.exception and at.title[0].value.endswith("HERMES")

    at.button[0].click().run(timeout=300)  # "Run mission": full offline mission through the UI
    assert not at.exception
    assert any("VERIFIED" in s.value for s in at.success)
    assert len(at.tabs) == 6 and len(at.dataframe) >= 4  # BOM, checks, iterations, evidence
    final = at.session_state["final"]
    assert final["ui_mode"] == "offline replay" and final["ui_events"]
