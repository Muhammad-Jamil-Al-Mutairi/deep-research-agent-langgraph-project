"""Numbered, human-readable mission trace ("[7] Design #2 verification FAILED ...").

Complements the span tree: spans answer "what ran and what did it cost", events
answer "what did the agent decide and why". Events are printed live and also
stored in the graph state so they survive checkpointing and appear in the report.
"""

from __future__ import annotations

import time
from typing import Literal

EventKind = Literal["plan", "research", "design", "calc", "verify", "replan", "critic", "loop", "budget",
                    "report", "error", "info"]

_ICONS = {"loop": "!!", "budget": "!!", "error": "xx", "verify": ">>", "critic": "??"}


class MissionLog:
    """Assigns sequence numbers and prints events as they happen."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.seq = 0

    def event(self, node: str, kind: EventKind, message: str, **data) -> dict:
        self.seq += 1
        record = {"seq": self.seq, "t": round(time.time(), 3), "node": node, "kind": kind,
                  "message": message, **data}
        if self.verbose:
            icon = _ICONS.get(kind, "  ")
            print(f"[{self.seq:>2}] {icon} {node:<20} {message}", flush=True)
        return record
