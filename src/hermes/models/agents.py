"""Structured outputs of the research, replanning and critic agents."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from hermes.models.requirements import Domain


class CandidateNote(BaseModel):
    component_id: str = Field(description="Exact component_id from the database.")
    suitability: str = Field(description="Why it fits (or might fit) the mission, citing numbers.")
    concerns: str = Field(default="", description="Risks, missing specs or doubts.")


class EvidenceNote(BaseModel):
    claim: str = Field(description="A specific technical fact, e.g. 'continuous load limit is 10 kg-cm'.")
    source: str = Field(description="Source document file name or URL exactly as returned by the tool.")
    page: str = Field(default="web", description="Page or section reference as returned by the tool.")
    url: str | None = Field(default=None, description="Source URL as returned by the tool.")
    component_id: str | None = None


class ResearchFindings(BaseModel):
    domain: Domain
    candidates: list[CandidateNote] = Field(description="Shortlist of 2-6 suitable components, best first.")
    evidence: list[EvidenceNote] = Field(default_factory=list, description="Facts retrieved from datasheets with citations.")
    summary: str = Field(description="2-4 sentence summary of the findings for the designer.")


class ResearchRequest(BaseModel):
    domain: Domain
    objective: str = Field(description="What to look for, with numeric targets, e.g. 'battery >= 40 Wh under 250 g'.")


class ReplanDecision(BaseModel):
    diagnosis: str = Field(description="Root-cause diagnosis of the failure, quoting the failing numbers.")
    root_causes: list[str] = Field(description="Each root cause in one line.")
    change_plan: list[str] = Field(description="Concrete changes for the next design, e.g. 'replace POL-713 with a driver rated >= 2 A continuous'.")
    research_requests: list[ResearchRequest] = Field(
        default_factory=list, description="Only if the current shortlist cannot fix the problem: targeted new research."
    )
    next_strategy: Literal["economy", "balanced", "performance", "relax_soft_preferences"] | None = Field(
        default=None, description="Escalate the design strategy if the current one cannot meet the constraints."
    )


class CriticIssue(BaseModel):
    severity: Literal["low", "medium", "high"]
    category: str = Field(description="e.g. thermal, evidence, compatibility, assumption, functional, safety")
    finding: str
    recommendation: str


class Critique(BaseModel):
    verdict: Literal["PASS", "REVISE"] = Field(description="REVISE only for issues the next design iteration can actually fix.")
    issues: list[CriticIssue] = Field(default_factory=list)
    summary: str
