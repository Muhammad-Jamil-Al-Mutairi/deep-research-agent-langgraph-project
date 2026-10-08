"""Central configuration: physical constants, unit conversions, budgets and paths."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# --- Physical constants and unit conversions -------------------------------
G = 9.80665  # standard gravity, m/s^2
KGCM_TO_NM = G / 100.0  # 1 kg-cm = 0.0980665 N-m
OZ_TO_G = 28.349523125
# The Saudi riyal is pegged to the US dollar at 3.75 SAR/USD (Saudi Central Bank).
SAR_PER_USD = 3.75

# --- Paths -----------------------------------------------------------------
PACKAGE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = PACKAGE_DIR / "knowledge"
COMPONENTS_CSV = KNOWLEDGE_DIR / "components.csv"
DATASHEETS_DIR = KNOWLEDGE_DIR / "datasheets"
# Build artefacts (SQLite DB, Chroma index) live outside the package, git-ignored.
DATA_DIR = Path(os.environ.get("HERMES_DATA_DIR", Path.cwd() / ".hermes"))

# --- Model -----------------------------------------------------------------
DEFAULT_MODEL = os.environ.get("MODEL_NAME", "deepseek/deepseek-v4-flash")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass(frozen=True)
class Budgets:
    """Hard execution budgets. When one is reached HERMES stops gracefully."""

    max_design_iterations: int = 5
    max_critic_revisions: int = 2
    max_research_calls: int = 12  # research-agent runs across the whole mission
    max_total_steps: int = 45  # graph node executions
    tool_calls_per_tool: int = 4  # ToolCallLimitMiddleware per data tool, per agent run
    web_tool_calls: int = 1  # search_web / read_webpage per research run (unverified source)
    model_calls_per_run: int = 12  # ModelCallLimitMiddleware per agent run
    stagnation_window: int = 3
    stagnation_epsilon: float = 0.02
    recursion_limit: int = 150  # LangGraph last-resort guard, above our own budgets


DEFAULT_BUDGETS = Budgets()

# Design strategies the designer escalates through when the loop stagnates.
STRATEGY_LADDER = ["economy", "balanced", "performance", "relax_soft_preferences"]

STRATEGY_DESCRIPTIONS = {
    "economy": "Minimise BOM cost: pick the cheapest candidate for each role that plausibly meets the requirements.",
    "balanced": "Balance cost against margin: prefer parts that pass every hard constraint with modest (10-40%) margins.",
    "performance": "Maximise margins on the failing constraints first, accepting higher cost and mass within the limits.",
    "relax_soft_preferences": "Ignore soft preferences (e.g. preferred vendors, aesthetics); satisfy only the hard constraints.",
}
