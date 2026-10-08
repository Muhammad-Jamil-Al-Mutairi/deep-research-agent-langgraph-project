"""Resolve a design proposal into a priced, weighed Bill of Materials."""

from __future__ import annotations

import math

from hermes.config import SAR_PER_USD
from hermes.models.design import BOM, BOMLine, DesignProposal
from hermes.tools.research.component_db import ComponentDB


def usd_to_sar(usd: float) -> float:
    return usd * SAR_PER_USD


def build_bom(proposal: DesignProposal, db: ComponentDB) -> BOM:
    """Look up every proposed component. Unknown ids are reported, never invented."""
    bom = BOM()
    merged: dict[str, tuple[int, list[str]]] = {}
    for line in proposal.lines:
        cid = line.component_id.strip()
        qty, roles = merged.get(cid, (0, []))
        merged[cid] = (qty + line.quantity, roles + [line.role])

    for cid, (qty, roles) in merged.items():
        comp = db.get(cid)
        if comp is None:
            bom.unknown_ids.append(cid)
            continue
        packs = math.ceil(qty / comp.pack_qty)
        line_cost = packs * comp.price_usd
        line_weight = None if comp.weight_g is None else comp.weight_g * qty
        if line_weight is None:
            bom.unverified_mass_items.append(cid)
        bom.lines.append(BOMLine(
            component_id=cid, category=comp.category, name=comp.name, manufacturer=comp.manufacturer,
            part_number=comp.part_number, role=" / ".join(dict.fromkeys(roles)), quantity=qty, packs=packs,
            pack_qty=comp.pack_qty, unit_price_usd=comp.price_usd, line_cost_usd=round(line_cost, 2),
            line_cost_sar=round(usd_to_sar(line_cost), 2), unit_weight_g=comp.weight_g,
            line_weight_g=None if line_weight is None else round(line_weight, 1),
            key_spec=comp.key_spec(), data_quality=comp.data_quality, source=comp.citation(),
        ))
    bom.total_cost_usd = round(sum(line.line_cost_usd for line in bom.lines), 2)
    bom.total_cost_sar = round(usd_to_sar(bom.total_cost_usd), 2)
    bom.total_mass_g = round(sum(line.line_weight_g or 0.0 for line in bom.lines), 1)
    return bom
