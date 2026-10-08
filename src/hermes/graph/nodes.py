"""LangGraph node functions for the HERMES mission graph.

LLM nodes:           mission_architect, research_<domain> (x4, parallel), designer, replanner, critic, reporter
Deterministic nodes: calculate, verify, guard

Each node returns a partial state update and appends numbered events. Agent failures
never crash the graph: each LLM node has a deterministic fallback.
"""

from __future__ import annotations

import asyncio

from hermes.agents import briefs
from hermes.agents.common import ProviderError
from hermes.agents.team import AgentTeam
from hermes.config import DEFAULT_BUDGETS, STRATEGY_LADDER, Budgets
from hermes.graph.routing import best_design, decide_after_verify
from hermes.graph.state import add_usage
from hermes.models import (
    DOMAIN_CATEGORIES,
    DOMAINS,
    CandidateNote,
    Critique,
    DesignProposal,
    EvidenceNote,
    MissionSpec,
    ReplanDecision,
    ResearchFindings,
    VerificationReport,
)
from hermes.models.design import BOM
from hermes.observability.events import MissionLog
from hermes.observability.tracing import observe
from hermes.report import render_report
from hermes.tools.engineering.bom import build_bom
from hermes.tools.engineering.calculator import DesignAnalysis, analyse_design
from hermes.tools.research.component_db import ComponentDB, get_db
from hermes.tools.verification.verifier import verify_design


PROVIDER_DOWN = "PROVIDER:"


def _step(extra: dict | None = None) -> dict:
    return {"steps": 1, **(extra or {})}


class HermesNodes:
    def __init__(self, team: AgentTeam, log: MissionLog | None = None, budgets: Budgets = DEFAULT_BUDGETS,
                 db: ComponentDB | None = None, retrieve_evidence: bool = True):
        self.team = team
        self.log = log or MissionLog()
        self.budgets = budgets
        self.db = db or get_db()
        self.retrieve_evidence = retrieve_evidence

    # ---- helpers ---------------------------------------------------------------------
    def ev(self, node: str, kind: str, message: str, **data) -> dict:
        return self.log.event(node, kind, message, **data)

    @staticmethod
    def _spec(state) -> MissionSpec:
        return MissionSpec.model_validate(state["spec"])

    def _fallback_findings(self, domain: str, reason: str) -> ResearchFindings:
        cands = [CandidateNote(component_id=c.component_id, suitability="database fallback candidate",
                               concerns=reason)
                 for cat in DOMAIN_CATEGORIES[domain] for c in self.db.search(cat, limit=6)]
        return ResearchFindings(domain=domain, candidates=cands,
                                summary=f"Fallback shortlist from the structured database ({reason}).")

    @staticmethod
    def _provider_down(state) -> str | None:
        """The recorded fatal provider error, if any: once set, no node calls the LLM again."""
        return next((e for e in (state.get("errors") or []) if e.startswith(PROVIDER_DOWN)), None)

    def _provider_errors(self, node: str, exc: Exception, events: list) -> list[str]:
        if not isinstance(exc, ProviderError):
            return []
        events.append(self.ev(node, "error", f"{exc} - no further LLM calls; the mission will stop with the best "
                                             "candidate so far"))
        return [f"{PROVIDER_DOWN} {exc}"]

    def _actionable(self, critique: Critique, design: dict) -> bool:
        """True if any recommendation names a database component that the design does not already use."""
        used = {line["component_id"] for line in design["bom"]["lines"]}
        text = " ".join(f"{i.recommendation} {i.finding}" for i in critique.issues).upper()
        return any(c.component_id.upper() in text for c in self.db.all() if c.component_id not in used)

    def _datasheet_evidence(self, candidates: list[CandidateNote], per_domain: int = 8) -> list[dict]:
        """Retrieve the best datasheet passage for each shortlisted component (metadata-filtered RAG)."""
        if not self.retrieve_evidence:
            return []
        from hermes.tools.research.rag import evidence_for_component

        out, seen = [], set()
        for cand in candidates[:per_domain]:
            comp = self.db.get(cand.component_id)
            for e in evidence_for_component(comp.component_id, f"{comp.name} ratings, limits and specifications"):
                if (e["source"], e["claim"]) not in seen:
                    seen.add((e["source"], e["claim"]))
                    out.append(e)
        return out

    # ---- 1. Mission Architect (planner) ------------------------------------------------
    @observe(name="node:mission_architect")
    async def mission_architect(self, state):
        try:
            spec, usage = await self.team.plan(state["user_request"])
        except Exception as exc:
            return {"final_status": "FAILED", "errors": [f"mission_architect: {exc}"], "usage": _step(),
                    "events": [self.ev("mission_architect", "error", f"Could not parse requirements: {exc}")]}
        rejected = usage.pop("rejected_overrides", [])
        plan = {t.domain: t.objective for t in spec.research_plan}
        for d in DOMAINS:  # the plan must cover every domain
            plan.setdefault(d, f"Shortlist {d} components that meet: {briefs.mission_brief(spec).splitlines()[1]}")
        r = spec.requirements
        events = [
            self.ev("mission_architect", "plan",
                    f"Requirements parsed: payload {r.payload_kg} kg, runtime >= {r.runtime_h_min} h, "
                    f"speed >= {r.max_speed_mps} m/s, mass <= {r.mass_kg_max} kg, budget <= {r.budget_sar_max} SAR, "
                    f"features {r.required_features}"),
            self.ev("mission_architect", "plan",
                    f"{len(spec.assumptions)} assumption(s), {len(spec.derived_requirements)} derived requirement(s), "
                    f"{len(spec.unknowns)} open question(s)"),
            self.ev("mission_architect", "plan", f"Research plan: {len(plan)} parallel tasks -> {', '.join(plan)}"),
        ]
        overrides = [a for a in spec.assumptions if a.id.startswith("P")]
        if overrides:
            events.append(self.ev("mission_architect", "plan", "Profile overrides accepted: "
                                  + "; ".join(f"{a.statement} ({a.rationale})" for a in overrides)[:300]))
        for a in (a for a in spec.assumptions if a.id.startswith("R")):
            events.append(self.ev("mission_architect", "plan", f"{a.statement}: {a.value} ({a.rationale})"))
        for u in (u for u in spec.unknowns if u.startswith("Check:")):
            events.append(self.ev("mission_architect", "error", f"Requirement cross-check: {u[7:]}"))
        if rejected:
            events.append(self.ev("mission_architect", "error",
                                  "Profile overrides REJECTED by validation: " + "; ".join(rejected)))
        return {"spec": spec.model_dump(), "research_plan": plan, "strategy": "economy",
                "events": events, "usage": _step(usage)}

    # ---- 2. Research (one node per domain, run in parallel) ------------------------
    def research_node(self, domain: str):
        @observe(name=f"node:research_{domain}")
        async def research(state):
            node = f"research_{domain}"
            usage_so_far = (state.get("usage") or {}).get("research_calls", 0)
            if usage_so_far >= self.budgets.max_research_calls:
                return {"usage": _step(), "events": [self.ev(node, "budget",
                        f"Research budget exhausted ({usage_so_far}/{self.budgets.max_research_calls}); "
                        "reusing existing findings")]}
            objective = (state.get("research_requests") or {}).get(domain) or state["research_plan"][domain]
            events = [self.ev(node, "research", f"Searching DB + datasheets: {objective[:110]}")]
            usage, errors = {"research_calls": 1}, []
            if self._provider_down(state):
                findings = self._fallback_findings(domain, "LLM provider unavailable")
            else:
                try:
                    findings, agent_usage = await self.team.research(
                        domain, objective, briefs.mission_brief(self._spec(state)))
                    usage.update(agent_usage)
                except Exception as exc:
                    events.append(self.ev(node, "error",
                                          f"Research agent failed ({exc}); falling back to structured DB query"))
                    errors = self._provider_errors(node, exc, events)
                    findings = self._fallback_findings(domain, "research agent failed")

            valid, dropped = [], []
            for cand in findings.candidates:
                comp = self.db.get(cand.component_id)
                (valid if comp and comp.category in DOMAIN_CATEGORIES[domain] else dropped).append(cand)
            if dropped:
                events.append(self.ev(node, "error", "Discarded candidates not in this domain's database categories: "
                                                     + ", ".join(c.component_id for c in dropped)))
            covered = {self.db.get(c.component_id).category for c in valid}
            missing = [cat for cat in DOMAIN_CATEGORIES[domain] if cat not in covered]
            if missing:
                extra = self._fallback_findings(domain, "category not covered by the agent").candidates
                valid += [c for c in extra if self.db.get(c.component_id).category in missing]
                events.append(self.ev(node, "info", f"Added database candidates for uncovered categories: {missing}"))
            # Guaranteed RAG evidence: one cited datasheet passage per shortlisted part (deterministic).
            known = {(e.source, e.claim) for e in findings.evidence}
            try:
                retrieved = await asyncio.to_thread(self._datasheet_evidence, valid)
            except Exception as exc:
                retrieved = []
                events.append(self.ev(node, "error", f"Datasheet retrieval unavailable ({exc}); DB specs only"))
            new = [EvidenceNote(**e) for e in retrieved if (e["source"], e["claim"]) not in known]
            if new:
                events.append(self.ev(node, "research", f"RAG: {len(new)} cited passages retrieved for shortlisted parts "
                                      + ", ".join(sorted({e.component_id for e in new}))[:120]))
            findings = findings.model_copy(update={"candidates": valid, "domain": domain,
                                                   "evidence": [*findings.evidence, *new]})
            evidence = [{**e.model_dump(), "domain": domain} for e in findings.evidence]
            events.append(self.ev(node, "research",
                                  f"{len(valid)} candidates, {len(evidence)} cited datasheet facts: "
                                  + ", ".join(c.component_id for c in valid[:6])))
            return {"research_results": {domain: findings.model_dump()}, "evidence": evidence,
                    "usage": _step(usage), "events": events, "errors": errors}
        return research

    # ---- 3. Designer -----------------------------------------------------------------
    @observe(name="node:designer")
    async def designer(self, state):
        spec = self._spec(state)
        designs = state.get("designs") or []
        k = len(designs) + 1
        parts = [briefs.mission_brief(spec), briefs.strategy_brief(state["strategy"]),
                 briefs.shortlist_brief(state.get("research_results") or {}), briefs.history_brief(designs)]
        if designs:
            last = designs[-1]
            parts.append("LATEST " + briefs.verification_brief(VerificationReport.model_validate(last["verification"]),
                                                               DesignAnalysis.model_validate(last["analysis"])))
            best = best_design(designs)
            failed = [c["name"] for c in best["verification"]["constraints"]
                      if c["kind"] == "hard" and c["status"] == "FAIL"]
            # Anchor refinement on the closest candidate so fixes accumulate instead of drifting back.
            parts.append(f"CLOSEST DESIGN SO FAR: #{best['iteration']} (score {best['verification']['score']}, "
                         f"failed {failed or '-'}). Start from this parts list and change only what is needed "
                         "to fix its failures:\n" + briefs.bom_brief(BOM.model_validate(best["bom"])))
        if state.get("replan"):
            r = state["replan"]
            parts.append("REPLANNING DECISION:\n  diagnosis: " + r["diagnosis"] + "\n  changes: "
                         + "; ".join(r["change_plan"]))
        flags = state.get("loop_flags") or {}
        if flags.get("repeated") or flags.get("stagnated"):
            parts.append("WARNING: the loop detector flagged repetition/stagnation. Propose a materially "
                         "different design consistent with the new strategy.")
        events, errors = [], []
        try:
            if self._provider_down(state):
                raise ProviderError("LLM provider unavailable earlier in this mission")
            proposal, usage = await self.team.design("\n\n".join(parts))
            # Pre-check: a parts list identical to an earlier design gets one corrective re-prompt before
            # it costs a calculate/verify iteration. A second repeat goes through and the guard handles it.
            previous = {d["fingerprint"]: d["iteration"] for d in designs}
            dup = previous.get(build_bom(proposal, self.db).fingerprint())
            if dup:
                events.append(self.ev("designer", "loop", f"Proposal repeats design #{dup} exactly - "
                                      "rejected before calculation, asking the designer for a different design"))
                parts.append(f"REJECTED: your proposal is identical to design #{dup}, which already FAILED. "
                             "Propose a different parts list that fixes the CLOSEST DESIGN SO FAR.")
                proposal, retry_usage = await self.team.design("\n\n".join(parts))
                usage = add_usage(usage, retry_usage)
            proposal = proposal.model_copy(update={"strategy": state["strategy"]})
            events.append(self.ev("designer", "design", f"Design #{k} proposed [{state['strategy']}]: "
                                  f"{len(proposal.lines)} lines. {proposal.rationale[:140]}"))
        except Exception as exc:
            proposal, usage = DesignProposal(strategy=state["strategy"], lines=[], rationale=f"designer failed: {exc}"), {}
            events.append(self.ev("designer", "error", f"Designer failed ({exc}); empty design will fail verification"))
            if not self._provider_down(state):
                errors = self._provider_errors("designer", exc, events)
        return {"pending_proposal": proposal.model_dump(), "research_requests": {}, "usage": _step(usage),
                "events": events, "errors": errors}

    # ---- 4. Calculation engine (deterministic) -----------------------------------------
    @observe(name="node:calculate")
    async def calculate(self, state):
        proposal = DesignProposal.model_validate(state["pending_proposal"])
        spec = self._spec(state)
        bom = build_bom(proposal, self.db)
        analysis = analyse_design(bom, spec.requirements, spec.profile, self.db)
        k = len(state.get("designs") or []) + 1
        v = analysis.value
        if analysis.issues:
            msg = f"Design #{k}: cannot complete analysis - {'; '.join(analysis.issues)}"
        else:
            msg = (f"Design #{k}: BOM {bom.total_cost_sar:,.0f} SAR, mass {v('total_mass'):.2f} kg, "
                   f"peak torque {v('torque_peak_design'):.3f} N-m/motor, speed {v('achievable_speed'):.2f} m/s, "
                   f"avg power {v('system_power_avg'):.1f} W, runtime {v('runtime'):.2f} h")
        events = [self.ev("calculate", "calc", msg)]
        if bom.unknown_ids:
            events.append(self.ev("calculate", "error", f"Unknown component ids rejected: {bom.unknown_ids}"))
        return {"pending_analysis": {"bom": bom.model_dump(), "analysis": analysis.model_dump()},
                "usage": _step(), "events": events}

    # ---- 5. Verification engine (deterministic, decides PASS/FAIL) ----------------------
    @observe(name="node:verify")
    async def verify(self, state):
        spec = self._spec(state)
        bom = BOM.model_validate(state["pending_analysis"]["bom"])
        analysis = DesignAnalysis.model_validate(state["pending_analysis"]["analysis"])
        report = verify_design(bom, analysis, spec.requirements, self.db)
        k = len(state.get("designs") or []) + 1
        record = {"iteration": k, "strategy": state["strategy"], "proposal": state["pending_proposal"],
                  "bom": bom.model_dump(), "analysis": analysis.model_dump(), "verification": report.model_dump(),
                  "fingerprint": bom.fingerprint()}
        label = "PASSED" if report.status == "PASS" else "FAILED"
        detail = f"{len(report.warnings)} warning(s)" if report.status == "PASS" else report.summary()[6:]
        event = self.ev("verify", "verify", f"Design #{k} verification {label}: {detail}")
        return {"designs": [record], "current": record, "usage": _step(), "events": [event]}

    # ---- 6. Reliability guard (loop detection + budgets + routing) ----------------------
    @observe(name="node:guard")
    async def guard(self, state):
        designs = state["designs"]
        steps = (state.get("usage") or {}).get("steps", 0) + 1
        verdict = decide_after_verify(designs, state["strategy"], steps, self.budgets)
        if self._provider_down(state) and verdict.route != "reporter":
            verdict.route, verdict.final_status = "reporter", "PROVIDER_ERROR"
            verdict.messages.append(("budget", "LLM PROVIDER UNAVAILABLE - stopping the design loop. "
                                               "Human review required."))
        events = [self.ev("guard", kind, msg) for kind, msg in verdict.messages]
        events.append(self.ev("guard", "info", f"Route -> {verdict.route}"))
        update = {"route": verdict.route, "strategy": verdict.strategy, "usage": _step(), "events": events,
                  "loop_flags": {"repeated": verdict.repeated, "stagnated": verdict.stagnated}}
        if verdict.final_status:
            update["final_status"] = verdict.final_status
        return update

    # ---- 7. Replanner -----------------------------------------------------------------
    @observe(name="node:replanner")
    async def replanner(self, state):
        spec = self._spec(state)
        cur = state["current"]
        report = VerificationReport.model_validate(cur["verification"])
        analysis = DesignAnalysis.model_validate(cur["analysis"])
        parts = [briefs.mission_brief(spec), briefs.strategy_brief(state["strategy"]),
                 briefs.bom_brief(BOM.model_validate(cur["bom"])), briefs.verification_brief(report, analysis),
                 briefs.history_brief(state["designs"])]
        critic = (state.get("critic_feedback") or [])
        from_critic = report.status == "PASS" and critic and critic[-1]["verdict"] == "REVISE"
        if from_critic:
            parts.append("CRITIC REQUESTED REVISION:\n" + "\n".join(
                f"  [{i['severity']}] {i['category']}: {i['finding']} -> {i['recommendation']}"
                for i in critic[-1]["issues"]))
        if (state.get("loop_flags") or {}).get("repeated") or (state.get("loop_flags") or {}).get("stagnated"):
            parts.append(f"CHANGE STRATEGY: the loop detector fired; the new strategy is '{state['strategy']}'.")
        errors, pre = [], []
        try:
            if self._provider_down(state):
                raise ProviderError("LLM provider unavailable earlier in this mission")
            decision, usage = await self.team.replan("\n\n".join(parts))
        except Exception as exc:
            if not self._provider_down(state):
                errors = self._provider_errors("replanner", exc, pre)
            failed = report.failed
            decision = ReplanDecision(
                diagnosis=f"Replanner unavailable ({exc}); deterministic diagnosis from the verifier.",
                root_causes=[f"{c.name}: required {c.required}, actual {c.actual}" for c in failed],
                change_plan=[f"Fix {c.name} ({c.detail})" for c in failed] or ["Address the critic's issues"])
            usage = {}
        events = [*pre, self.ev("replanner", "replan", f"Diagnosis: {decision.diagnosis[:200]}"),
                  self.ev("replanner", "replan", "Plan: " + " | ".join(decision.change_plan)[:220])]
        requests = {}
        budget_left = self.budgets.max_research_calls - (state.get("usage") or {}).get("research_calls", 0)
        for req in decision.research_requests:
            if req.domain in DOMAINS and len(requests) < budget_left:
                requests[req.domain] = req.objective
        if decision.research_requests and len(requests) < len(decision.research_requests):
            events.append(self.ev("replanner", "budget", "Research budget limits targeted re-research to "
                                                         f"{list(requests) or 'none'}"))
        if requests:
            events.append(self.ev("replanner", "replan", f"Targeted re-research: {list(requests)}"))
        update = {"replan": decision.model_dump(), "research_requests": requests, "usage": _step(usage),
                  "events": events, "errors": errors}
        ladder = STRATEGY_LADDER
        new = decision.next_strategy
        if new in ladder and ladder.index(new) > ladder.index(state["strategy"]):  # escalate only
            update["strategy"] = new
            events.append(self.ev("replanner", "replan", f"Strategy escalated: {state['strategy']} -> {new}"))
        return update

    # ---- 8. Critic ------------------------------------------------------------------------
    @observe(name="node:critic")
    async def critic(self, state):
        spec = self._spec(state)
        cur = state["current"]
        report = VerificationReport.model_validate(cur["verification"])
        analysis = DesignAnalysis.model_validate(cur["analysis"])
        evidence = state.get("evidence") or []
        brief = "\n\n".join([
            briefs.mission_brief(spec), briefs.bom_brief(BOM.model_validate(cur["bom"])),
            "ALL CHECKS:\n" + "\n".join(f"  [{c.status}] {c.name}: {c.required} | {c.actual}"
                                        + (f" ({c.margin_pct:+.0f}%)" if c.margin_pct is not None else "")
                                        for c in report.constraints),
            briefs.verification_brief(report, analysis),
            f"EVIDENCE: {len(evidence)} cited datasheet facts collected by research.",
            briefs.shortlist_brief(state.get("research_results") or {}),
            (f"BUDGET HEADROOM: {spec.requirements.budget_sar_max - cur['bom']['total_cost_sar']:,.0f} SAR"
             if spec.requirements.budget_sar_max else "BUDGET HEADROOM: no budget limit"),
            briefs.history_brief(state["designs"]),
        ])
        errors, pre = [], []
        try:
            if self._provider_down(state):
                raise ProviderError("LLM provider unavailable earlier in this mission")
            critique, usage = await self.team.critique(brief)
        except Exception as exc:
            critique, usage = Critique(verdict="PASS", summary=f"Critic unavailable ({exc}); no review performed."), {}
            if not self._provider_down(state):
                errors = self._provider_errors("critic", exc, pre)
        revisions = sum(1 for c in (state.get("critic_feedback") or []) if c["verdict"] == "REVISE")
        route = "reporter"
        events = [*pre, self.ev("critic", "critic", f"Critic verdict {critique.verdict}: {critique.summary[:180]}")]
        if critique.verdict == "REVISE" and not self._actionable(critique, cur):
            # Deterministic gate: a revision must name a catalogue part that is not already in the design.
            critique = critique.model_copy(update={"verdict": "PASS"})
            events.append(self.ev("critic", "info", "REVISE not actionable (no catalogue replacement named) - "
                                  "issues recorded as limitations instead of another iteration"))
        for issue in critique.issues[:4]:
            events.append(self.ev("critic", "critic", f"[{issue.severity}] {issue.category}: {issue.finding[:150]}"))
        if critique.verdict == "REVISE":
            if revisions < self.budgets.max_critic_revisions:
                route = "replanner"
            else:
                events.append(self.ev("critic", "budget", f"Critic revision budget exhausted ({revisions}/"
                                      f"{self.budgets.max_critic_revisions}); remaining issues become limitations"))
        events.append(self.ev("critic", "info", f"Route -> {route}"))
        return {"critic_feedback": [{**critique.model_dump(), "iteration": cur["iteration"]}], "route": route,
                "usage": _step(usage), "events": events, "errors": errors}

    # ---- 9. Reporter ------------------------------------------------------------------------
    @observe(name="node:reporter")
    async def reporter(self, state):
        designs = state.get("designs") or []
        status = state.get("final_status")
        cur = state.get("current")
        if status is None:
            status = "VERIFIED" if cur and cur["verification"]["status"] == "PASS" else "UNRESOLVED"
        final = cur if status == "VERIFIED" else best_design(designs)
        fallback_events = []
        passing = [d for d in designs if d["verification"]["status"] == "PASS"]
        if status != "VERIFIED" and passing:
            # A critic-requested revision failed and the loop stopped: keep the last verified design.
            final, status = passing[-1], "VERIFIED"
            fallback_events.append(self.ev("reporter", "info", f"Latest design did not pass ({state.get('final_status')}); "
                                           f"reporting the last verified design #{final['iteration']}"))
        facts = (f"Status: {status}. Iterations: {len(designs)}. "
                 + (briefs.bom_brief(BOM.model_validate(final["bom"])) + "\n"
                    + briefs.verification_brief(VerificationReport.model_validate(final["verification"]),
                                                DesignAnalysis.model_validate(final["analysis"]))
                    if final else "No design was produced.")
                 + "\n" + briefs.history_brief(designs))
        try:
            if self._provider_down(state):
                raise ProviderError("LLM provider unavailable")
            summary, usage = await self.team.summarize(facts)
        except Exception as exc:
            summary, usage = (f"Executive summary unavailable ({exc}). Final status: {status} after "
                              f"{len(designs)} design iteration(s)."), {}
        report_md = render_report({**state, "final_status": status}, final, summary)
        event = self.ev("reporter", "report", f"Engineering report generated - final status {status}"
                        + (f", design #{final['iteration']}" if final else ""))
        return {"report_md": report_md, "final_design": final, "final_status": status, "usage": _step(usage),
                "events": [*fallback_events, event]}
