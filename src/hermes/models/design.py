"""Design proposals (from the Designer agent) and the resolved Bill of Materials."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BOMLineProposal(BaseModel):
    component_id: str = Field(description="Exact component_id from the component database, e.g. POL-4752.")
    quantity: int = Field(ge=1, description="Number of individual units (e.g. 2 wheels, 2 motors).")
    role: str = Field(description="Role in the design, e.g. 'left/right drive motor', 'main battery'.")


class DesignProposal(BaseModel):
    """Structured output of the Designer agent. Contains choices only - no computed numbers."""

    strategy: str = Field(description="Design strategy followed (economy, balanced, performance, ...).")
    lines: list[BOMLineProposal] = Field(description="Every part of the robot, including hubs, brackets, chassis and wiring.")
    rationale: str = Field(description="Why these parts were chosen, in 2-5 sentences.")
    changes_from_previous: str = Field(default="", description="What changed versus the previous design and why (empty for the first design).")


class BOMLine(BaseModel):
    """A resolved BOM line: every number comes from the component database."""

    component_id: str
    category: str
    name: str
    manufacturer: str
    part_number: str
    role: str
    quantity: int
    packs: int
    pack_qty: int
    unit_price_usd: float
    line_cost_usd: float
    line_cost_sar: float
    unit_weight_g: float | None
    line_weight_g: float | None
    key_spec: str
    data_quality: str
    source: str


class BOM(BaseModel):
    lines: list[BOMLine] = Field(default_factory=list)
    unknown_ids: list[str] = Field(default_factory=list)
    total_cost_usd: float = 0.0
    total_cost_sar: float = 0.0
    total_mass_g: float = 0.0
    unverified_mass_items: list[str] = Field(default_factory=list)

    def by_category(self, category: str) -> list[BOMLine]:
        return [line for line in self.lines if line.category == category]

    def fingerprint(self) -> str:
        """Order-independent identity of a design: component ids and quantities."""
        return ";".join(sorted(f"{line.component_id}x{line.quantity}" for line in self.lines))
