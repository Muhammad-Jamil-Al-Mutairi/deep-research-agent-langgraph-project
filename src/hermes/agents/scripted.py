"""Deterministic scripted agents with the same interface as ``LLMTeam`` (no LLM, no cost).

Used by the offline integration tests and by the notebook's reliability demos, where a
specific behaviour (a repeated design, a stagnating loop, an infeasible mission) must be
reproduced exactly. Everything else in the graph - calculation, verification, routing,
loop detection, budgets, checkpointing - is the real production code.
"""

from __future__ import annotations

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel

from hermes.models import (
    DOMAIN_CATEGORIES,
    CandidateNote,
    Critique,
    DesignProposal,
    MissionSpec,
    ReplanDecision,
    ResearchFindings,
)
from hermes.tools.research.component_db import get_db

_ZERO = {"llm_runs": 0, "tokens": 0, "cost_usd": 0.0}


class ScriptedChatModel(FakeMessagesListChatModel):
    """A scripted chat model that accepts ``bind_tools``, so real ``create_agent`` agents can run offline."""

    def bind_tools(self, tools, **kwargs):
        return self


class ScriptedTeam:
    def __init__(self, spec: MissionSpec, designs: list[DesignProposal], critiques: list[Critique] | None = None,
                 replans: list[ReplanDecision] | None = None, fail_research: set[str] | None = None):
        self.spec = spec
        self.designs = list(designs)
        self.critiques = list(critiques or [Critique(verdict="PASS", summary="scripted critic: no issues")])
        self.replans = list(replans or [])
        self.fail_research = fail_research or set()
        self.calls: list[str] = []

    @staticmethod
    def _next(items: list, index: int):
        return items[min(index, len(items) - 1)]  # repeat the last item when the script runs out

    async def plan(self, request: str):
        self.calls.append("plan")
        return self.spec, dict(_ZERO)

    async def research(self, domain: str, objective: str, mission: str):
        self.calls.append(f"research:{domain}")
        if domain in self.fail_research:
            raise RuntimeError(f"scripted research failure for {domain}")
        db = get_db()
        cands = [CandidateNote(component_id=c.component_id, suitability="scripted: database candidate")
                 for cat in DOMAIN_CATEGORIES[domain] for c in db.search(cat, limit=6)]
        return ResearchFindings(domain=domain, candidates=cands, summary=f"scripted {domain} shortlist"), dict(_ZERO)

    async def design(self, brief: str):
        n = sum(1 for c in self.calls if c == "design")
        self.calls.append("design")
        return self._next(self.designs, n), dict(_ZERO)

    async def replan(self, brief: str):
        n = sum(1 for c in self.calls if c == "replan")
        self.calls.append("replan")
        if self.replans:
            return self._next(self.replans, n), dict(_ZERO)
        return ReplanDecision(diagnosis="scripted replanner", root_causes=["see verification"],
                              change_plan=["follow the next scripted design"]), dict(_ZERO)

    async def critique(self, brief: str):
        n = sum(1 for c in self.calls if c == "critique")
        self.calls.append("critique")
        return self._next(self.critiques, n), dict(_ZERO)

    async def summarize(self, brief: str):
        self.calls.append("summarize")
        return "Scripted executive summary (offline run, no LLM).", dict(_ZERO)
