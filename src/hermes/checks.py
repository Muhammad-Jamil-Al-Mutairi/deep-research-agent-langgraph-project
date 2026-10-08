"""Markdown views of a finished mission for the notebook's "Checks" section."""

from __future__ import annotations

from hermes.report import _history, _table, _verification


def status_line(final: dict) -> str:
    trail = " -> ".join(f"#{d['iteration']} {d['verification']['status']}" for d in final.get("designs") or [])
    critic = " -> ".join(c["verdict"] for c in final.get("critic_feedback") or []) or "not run"
    return (f"**Final status: {final.get('final_status')}** | design iterations: {len(final.get('designs') or [])} "
            f"| verification trail: {trail or '-'} | critic: {critic}")


def iteration_table(final: dict) -> str:
    return _history(final.get("designs") or [])


def verification_table(final: dict) -> str:
    design = final.get("final_design")
    return _verification(design) if design else "No design."


def events_table(final: dict, kinds: tuple[str, ...] | None = None) -> str:
    rows = [[e["seq"], e["node"], e["kind"], e["message"]] for e in final.get("events") or []
            if kinds is None or e["kind"] in kinds]
    return _table(["#", "Node", "Kind", "Event"], rows) if rows else "No events of this kind."


def research_timeline(final: dict) -> str:
    """Start/end of each research branch from event timestamps - overlapping intervals = parallel execution."""
    spans: dict[str, list[float]] = {}
    for e in final.get("events") or []:
        if e["node"].startswith("research_"):
            spans.setdefault(e["node"], []).append(e["t"])
    if not spans:
        return "No research events."
    t0 = min(min(v) for v in spans.values())
    rows = [[node, f"{min(v) - t0:.2f}", f"{max(v) - t0:.2f}"] for node, v in sorted(spans.items())]
    return _table(["Research branch", "first event (s)", "last event (s)"], rows)


def usage_table(final: dict) -> str:
    u, t = final.get("usage") or {}, final.get("trace_totals") or {}
    rows = [["graph node executions (steps)", u.get("steps", 0)],
            ["research-agent runs", u.get("research_calls", 0)],
            ["LLM agent runs", t.get("agent_runs", u.get("llm_runs", 0))],
            ["total tokens", t.get("total_tokens", u.get("tokens", 0))],
            ["real OpenRouter cost (USD)", f"{t.get('cost_usd', u.get('cost_usd', 0.0)):.4f}"]]
    return _table(["Budget / usage", "Value"], rows)


async def checkpoint_table(graph, config: dict, limit: int = 60) -> str:
    rows = []
    async for snap in graph.aget_state_history(config):
        v = snap.values
        rows.append([snap.metadata.get("step"), ", ".join(snap.next) or "END", len(v.get("designs") or []),
                     v.get("strategy", ""), v.get("final_status") or ""])
        if len(rows) >= limit:
            break
    rows.reverse()
    return _table(["Checkpoint step", "Next node(s)", "Designs so far", "Strategy", "Final status"], rows)
