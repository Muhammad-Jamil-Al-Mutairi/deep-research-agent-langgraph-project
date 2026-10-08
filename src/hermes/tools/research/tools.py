"""LangChain tools exposed to HERMES agents.

Every tool returns a string and never raises: bad input or an empty result becomes
an explanatory message the agent can act on ("handles bad tool results gracefully").
"""

from __future__ import annotations

import json
import logging

from langchain_core.tools import tool

from hermes.config import SAR_PER_USD
from hermes.tools.engineering import battery as bat
from hermes.tools.engineering import dynamics as dyn
from hermes.tools.research.component_db import FILTERABLE, FilterError, get_db

logger = logging.getLogger(__name__)


def _row(c) -> str:
    weight = "weight not verified" if c.weight_g is None else f"{c.weight_g:g} g"
    pack = f" per pack of {c.pack_qty}" if c.pack_qty > 1 else ""
    return (f"- {c.component_id} | {c.name} | {c.price_usd:.2f} USD ({c.price_usd * SAR_PER_USD:.0f} SAR){pack} | "
            f"{weight} | {c.key_spec()} | data: {c.data_quality}")


@tool
def search_components(category: str, filters: list[str] | None = None, sort_by: str = "price_usd",
                      limit: int = 8) -> str:
    """Search the structured component database (authoritative numeric specs).

    category: one of motor, battery, motor_driver, controller, imu, range_sensor, regulator,
              wheel, hub, bracket, caster, chassis, structure, wiring.
    filters: expressions "column op value" using ONLY these columns -
             common: price_usd, weight_g, manufacturer, data_quality;
             motor: gear_ratio, no_load_rpm, stall_torque_kgcm, stall_current_a, cont_torque_limit_kgcm,
                    has_encoder (1/0), shaft_diameter_mm, motor_family (25D/37D);
             battery: chemistry (LiPo/NiMH), cells, capacity_mah, c_rating, rated_voltage_v;
             motor_driver: channels, cont_current_a, voltage_min_v, voltage_max_v, logic_v_min, logic_v_max;
             wheel/hub/bracket: wheel_diameter_mm, bore_mm, fits_shaft_mm, fits_motor_family;
             controller/sensors/regulator: supply_current_ma, output_v, voltage_min_v, voltage_max_v.
             Example: ["capacity_mah >= 4000", "weight_g <= 400", "has_encoder = 1"].
    sort_by: a numeric column, prefix with '-' for descending (e.g. "-capacity_mah").
    """
    db = get_db()
    try:
        rows = db.search(category, filters or [], sort_by=sort_by, limit=limit)
    except FilterError as exc:
        return f"Filter error: {exc}"
    except Exception as exc:  # database problems must not crash the agent
        logger.exception("component search failed")
        return f"Component search failed: {exc}"
    if not rows:
        known = ", ".join(db.categories())
        return (f"No '{category}' components match {filters or 'no filters'}. "
                f"Relax a filter or check the category name (known: {known}).")
    return f"{len(rows)} result(s) for {category} {filters or ''}:\n" + "\n".join(_row(c) for c in rows)


@tool
def get_component(component_id: str) -> str:
    """Return every verified specification of one component plus its source citation (JSON)."""
    comp = get_db().get(component_id)
    if comp is None:
        return f"Unknown component_id '{component_id}'. Use search_components to find valid ids."
    data = {k: v for k, v in comp.model_dump().items() if v not in (None, "")}
    data["citation"] = comp.citation()
    missing = [k for k in ("weight_g", "supply_current_ma") if getattr(comp, k) is None
               and comp.category in ("controller", "imu", "range_sensor")]
    if missing:
        data["not_verified"] = missing
    return json.dumps(data, indent=1)


@tool
def search_datasheets(query: str, component_id: str | None = None, k: int = 4) -> str:
    """Semantic search over datasheet excerpts (RAG). Returns passages with citations.

    Use for qualitative evidence: load limits, thermal guidance, compatibility, handling notes.
    Optionally restrict to one component_id.
    """
    try:
        from hermes.tools.research.rag import get_index

        hits = get_index().search(query, k=max(1, min(k, 8)), component_id=component_id)
    except Exception as exc:
        logger.exception("datasheet search failed")
        return f"Datasheet search unavailable ({exc}). Rely on search_components for specs."
    if not hits:
        return f"No datasheet passages found for '{query}'" + (f" and {component_id}." if component_id else ".")
    blocks = []
    for i, h in enumerate(hits, 1):
        m = h.metadata
        page = m.get("page") or "web"
        blocks.append(f"[{i}] source: {m.get('source')} | section: {m.get('section')} | page: {page} | "
                      f"url: {m.get('source_url')} | relevance: {h.score:.2f}\n{h.text}")
    return "\n\n".join(blocks)


# ---- deterministic engineering calculators exposed as tools ---------------------------


@tool
def size_battery_for_runtime(runtime_h: float, average_power_w: float, voltage_v: float = 11.1,
                             usable_fraction: float = 0.8) -> str:
    """Capacity (mAh) and energy (Wh) a battery needs to run `average_power_w` for `runtime_h` hours."""
    try:
        mah = bat.required_capacity_mah(runtime_h, average_power_w, voltage_v, usable_fraction)
    except (ValueError, ZeroDivisionError) as exc:
        return f"Cannot size battery: {exc}"
    return (f"Required capacity: {mah:.0f} mAh at {voltage_v} V ({mah * voltage_v / 1000:.1f} Wh nameplate), "
            f"formula t*P/(V*usable) = {runtime_h}*{average_power_w}/({voltage_v}*{usable_fraction}).")


@tool
def wheel_rpm_for_speed(speed_mps: float, wheel_diameter_mm: float) -> str:
    """Wheel rpm needed for a linear speed: rpm = v / (pi * d) * 60."""
    if wheel_diameter_mm <= 0:
        return "wheel_diameter_mm must be positive"
    return f"{dyn.wheel_rpm_for_speed(speed_mps, wheel_diameter_mm / 1000):.1f} rpm"


@tool
def usd_to_sar(amount_usd: float) -> str:
    """Convert USD to SAR at the fixed peg of 3.75 SAR/USD."""
    return f"{amount_usd:.2f} USD = {amount_usd * SAR_PER_USD:.2f} SAR"


RESEARCH_DB_TOOLS = [search_components, get_component, search_datasheets]
ENGINEERING_TOOLS = [size_battery_for_runtime, wheel_rpm_for_speed, usd_to_sar]
FILTERABLE_COLUMNS = sorted(FILTERABLE)
