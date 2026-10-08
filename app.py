"""HERMES web UI (Streamlit).

    uv sync --extra ui
    uv run --extra ui streamlit run app.py

The notebook stays the graded artifact; this app is a demo front end over the same graph:
the LLM agents propose, the deterministic calculation engine and verifier decide.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import replace
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from hermes.config import DEFAULT_BUDGETS, DEFAULT_MODEL
from hermes.graph import build_graph, run_mission
from hermes.report import DISCLAIMER, REVIEW_NOTE
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

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

st.set_page_config(page_title="HERMES", page_icon="🛠️", layout="wide")

STATUS_STYLE = {"VERIFIED": st.success, "BUDGET_EXHAUSTED": st.warning, "STAGNATED": st.warning,
                "UNRESOLVED": st.warning, "PROVIDER_ERROR": st.error, "FAILED": st.error}


@st.cache_data
def presets() -> dict[str, str]:
    missions = json.loads((ROOT / "evaluation" / "missions.json").read_text(encoding="utf-8"))
    return {m["id"]: m["request"] for m in missions}


# ---- sidebar: mode, model, budgets ----------------------------------------------------------
with st.sidebar:
    st.header("Run settings")
    env_key = os.environ.get("OPENROUTER_API_KEY", "")
    typed_key = "" if env_key else st.text_input("OpenRouter API key", type="password",
                                                 help="Or put OPENROUTER_API_KEY in .env")
    api_key = env_key or typed_key
    mode = st.radio("Mode", ["Live LLM agents", "Offline replay"], index=0 if api_key else 1,
                    help="Offline replay uses scripted agents (no API calls) for the delivery-robot demo. "
                         "The graph, tools, calculations, verifier and loop detection are the real code.")
    live = mode == "Live LLM agents"
    if live and not api_key:
        st.error("Live mode needs an OpenRouter API key.")
    if live:
        st.caption("Key loaded from .env" if env_key else "Key from this session only (not saved)")
    model = st.text_input("Model", DEFAULT_MODEL, disabled=not live)
    use_web = st.checkbox("Allow web search (DuckDuckGo)", value=True, disabled=not live)
    st.subheader("Budgets")
    max_designs = st.slider("Max design iterations", 2, 8, DEFAULT_BUDGETS.max_design_iterations)
    max_revisions = st.slider("Max critic revisions", 0, 3, DEFAULT_BUDGETS.max_critic_revisions)
    st.caption("A live mission costs about $0.015-0.025 and takes 5-10 minutes with the default model.")

# ---- request -------------------------------------------------------------------------------
st.title("🛠️ HERMES")
st.caption("Hierarchical Engineering Reasoning, Modeling & Evaluation System - autonomous engineering design "
           "& verification agent")
st.info(f"{DISCLAIMER.replace('**', '')} {REVIEW_NOTE}", icon="⚠️")

options = presets()
if live:
    choice = st.selectbox("Example request", [*options, "custom"], format_func=lambda k: k.replace("-", " "))
    request = st.text_area("Engineering request", "" if choice == "custom" else options[choice], height=110)
else:
    request = st.text_area("Engineering request (offline replay is scripted for this request)",
                           options["delivery-robot"], height=110, disabled=True)

run_clicked = st.button("Run mission", type="primary", disabled=(live and not api_key) or not request.strip())

# ---- run -------------------------------------------------------------------------------------
if run_clicked:
    budgets = replace(DEFAULT_BUDGETS, max_design_iterations=max_designs, max_critic_revisions=max_revisions)
    events: list[dict] = []
    status = st.status("Running mission...", expanded=True)
    feed = status.empty()

    def show(record: dict) -> None:
        events.append(record)
        status.update(label=f"Running - [{record['seq']}] {record['node']}: {record['message'][:90]}")
        feed.code("\n".join(event_line(e) for e in events[-40:]), language=None)

    log = CallbackLog(show)
    try:
        team = build_team(live, log, budgets=budgets, api_key=api_key, model_name=model, use_web=use_web)
        graph = build_graph(team, budgets=budgets, log=log)
        final = asyncio.run(run_mission(graph, request.strip(), mission_id=f"ui-{uuid.uuid4().hex[:8]}",
                                        budgets=budgets))
    except Exception as exc:
        status.update(label="Mission crashed", state="error")
        st.exception(exc)
        st.stop()
    final["ui_events"] = events
    final["ui_mode"] = "live" if live else "offline replay"
    st.session_state["final"] = final
    status.update(label=f"Mission finished: {final['final_status']}",
                  state="complete" if final["final_status"] == "VERIFIED" else "error", expanded=False)

# ---- results -------------------------------------------------------------------------------
final = st.session_state.get("final")
if final:
    status_text = final["final_status"]
    STATUS_STYLE.get(status_text, st.info)(
        f"**{status_text}** - {len(final.get('designs') or [])} design iteration(s), "
        f"reported design #{(final.get('final_design') or {}).get('iteration', '-')} ({final['ui_mode']})")

    totals = final.get("trace_totals") or {}
    cols = st.columns(len(metric_values(final)) + 2 or 2)
    for col, (label, value) in zip(cols, metric_values(final), strict=False):
        col.metric(label, value)
    cols[-2].metric("Tokens", f"{totals.get('total_tokens', 0):,}")
    cols[-1].metric("LLM cost", f"${totals.get('cost_usd', 0.0):.4f}")

    tabs = st.tabs(["Bill of materials", "Verification", "Iterations", "Evidence (RAG)", "Event log", "Report"])
    with tabs[0]:
        rows = bom_rows(final)
        if rows:
            st.dataframe(rows, width="stretch", hide_index=True)
        else:
            st.write("No design produced.")
        if final.get("final_design"):
            st.caption(f"Total {final['final_design']['bom']['total_cost_sar']:,.2f} SAR. Single-unit list prices "
                       "converted at 3.75 SAR/USD; shipping, customs and VAT excluded.")
    with tabs[1]:
        rows = check_rows(final)
        if rows:
            st.dataframe(rows, width="stretch", hide_index=True)
        else:
            st.write("No design produced.")
    with tabs[2]:
        st.dataframe(iteration_rows(final), width="stretch", hide_index=True)
        for fb in final.get("critic_feedback") or []:
            st.markdown(f"**Critic on design #{fb.get('iteration')}: {fb['verdict']}** - {fb['summary']}")
    with tabs[3]:
        rows = evidence_rows(final)
        st.caption(f"{len(rows)} cited datasheet passages (local embeddings, Chroma vector store).")
        st.dataframe(rows, width="stretch", hide_index=True,
                     column_config={"URL": st.column_config.LinkColumn("URL")})
    with tabs[4]:
        st.code("\n".join(event_line(e) for e in final["ui_events"]), language=None)
    with tabs[5]:
        st.download_button("Download report (.md)", final["report_md"], file_name=f"{final['mission_id']}.md",
                           mime="text/markdown")
        st.markdown(final["report_md"])
