"""Calculation and verification results. Produced only by deterministic code."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Provenance = Literal["SOURCED", "CALCULATED", "ASSUMED", "UNVERIFIED"]
Status = Literal["PASS", "FAIL", "WARN", "UNVERIFIED"]


class Calculation(BaseModel):
    name: str
    value: float | None
    unit: str
    formula: str
    provenance: Provenance = "CALCULATED"
    note: str = ""


class ConstraintResult(BaseModel):
    name: str
    kind: Literal["hard", "soft"]
    required: str
    actual: str
    status: Status
    margin_pct: float | None = Field(default=None, description="Positive = headroom, negative = shortfall.")
    detail: str = ""


class VerificationReport(BaseModel):
    status: Literal["PASS", "FAIL"]
    constraints: list[ConstraintResult]
    score: float = Field(description="0 when every hard constraint passes; otherwise the (negative) sum of normalised shortfalls.")

    @property
    def failed(self) -> list[ConstraintResult]:
        return [c for c in self.constraints if c.kind == "hard" and c.status == "FAIL"]

    @property
    def warnings(self) -> list[ConstraintResult]:
        return [c for c in self.constraints if c.status in ("WARN", "UNVERIFIED")]

    def summary(self) -> str:
        if self.status == "PASS":
            return f"PASS ({len(self.constraints)} checks, {len(self.warnings)} warnings)"
        return "FAIL: " + "; ".join(f"{c.name} (required {c.required}, actual {c.actual})" for c in self.failed)
