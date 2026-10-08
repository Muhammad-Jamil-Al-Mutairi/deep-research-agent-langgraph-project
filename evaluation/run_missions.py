"""Run the evaluation missions against the live LLM agents and record the outcomes.

Usage:  uv run python evaluation/run_missions.py [mission-id ...]
Writes evaluation/results/<id>.md (engineering report) and evaluation/results/summary.md.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from hermes.agents.common import make_llm
from hermes.agents.team import LLMTeam
from hermes.config import DEFAULT_MODEL
from hermes.graph import build_graph, run_mission
from hermes.models import DOMAINS
from hermes.observability.events import MissionLog

HERE = Path(__file__).resolve().parent


async def run_one(mission: dict) -> dict:
    log = MissionLog()
    team = LLMTeam(make_llm(), model_name=DEFAULT_MODEL,
                   on_tool_loop=lambda d, t, m: log.event(f"research_{d}" if d in DOMAINS else d, "loop", m),
                   on_converge=lambda agent, reason: log.event(agent, "budget",
                                                               f"Stage budget reached ({reason}) -> forcing final answer"))
    graph = build_graph(team, log=log)
    final = await run_mission(graph, mission["request"], mission_id=mission["id"])
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / f"{mission['id']}.md").write_text(final["report_md"], encoding="utf-8")
    totals = final.get("trace_totals", {})
    return {
        "id": mission["id"],
        "final_status": final["final_status"],
        "expected": mission["expect"]["final_status"],
        "met_expectation": final["final_status"] in mission["expect"]["final_status"],
        "design_iterations": len(final["designs"]),
        "verification_trail": " -> ".join(d["verification"]["status"] for d in final["designs"]),
        "loop_events": sum(1 for e in final["events"] if e["kind"] == "loop"),
        "graph_steps": final["usage"].get("steps", 0),
        "agent_runs": totals.get("agent_runs", 0),
        "tokens": totals.get("total_tokens", 0),
        "cost_usd": totals.get("cost_usd", 0.0),
    }


async def main(ids: list[str]) -> None:
    load_dotenv()
    missions = json.loads((HERE / "missions.json").read_text(encoding="utf-8"))
    store = HERE / "results" / "summary.json"
    results = json.loads(store.read_text(encoding="utf-8")) if store.exists() else {}
    for m in missions:
        if not ids or m["id"] in ids:
            results[m["id"]] = {**await run_one(m), "model": DEFAULT_MODEL, "run_on": date.today().isoformat()}
            store.write_text(json.dumps(results, indent=1), encoding="utf-8")  # merge: re-running one keeps the rest
    print(write_summary(missions, results))


def write_summary(missions: list[dict], results: dict) -> str:
    """Render evaluation/results/summary.md from the merged per-mission results."""
    rows = [results[m["id"]] for m in missions if m["id"] in results]
    header = list(rows[0].keys())
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(r[h]) for h in header) + " |" for r in rows]
    pending = [m["id"] for m in missions if m["id"] not in results]
    total = sum(r["cost_usd"] for r in rows)
    text = ("# HERMES evaluation missions (live LLM runs)\n\n" + "\n".join(lines)
            + f"\n\nTotal cost of the runs above: ${total:.4f} USD.\n"
            + (f"\nPending live run:{', '.join(pending)}.\n" if pending else ""))
    (HERE / "results" / "summary.md").write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
