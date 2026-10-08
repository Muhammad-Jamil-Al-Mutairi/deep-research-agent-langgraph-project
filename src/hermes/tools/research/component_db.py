"""Structured component database (SQLite) built from ``knowledge/components.csv``.

Vector search is good at finding prose evidence but bad at numeric filtering such
as ``capacity_mah >= 4000 AND weight_g <= 400``. Engineering specs therefore live
in a relational table, and agents query it with whitelisted filter expressions.
"""

from __future__ import annotations

import csv
import re
import sqlite3
import threading
from pathlib import Path

from hermes.config import COMPONENTS_CSV, DATA_DIR
from hermes.models.components import Component

_NUMERIC = {
    "price_usd", "weight_g", "length_mm", "width_mm", "height_mm", "rated_voltage_v", "voltage_min_v",
    "voltage_max_v", "gear_ratio", "no_load_rpm", "no_load_current_a", "stall_current_a", "stall_torque_kgcm",
    "max_power_w", "cont_torque_limit_kgcm", "peak_torque_limit_kgcm", "shaft_diameter_mm", "capacity_mah",
    "c_rating", "cont_current_a", "peak_current_a", "logic_v_min", "logic_v_max", "output_v",
    "supply_current_ma", "supply_voltage_v", "wheel_diameter_mm", "bore_mm", "fits_shaft_mm",
}
_INTEGER = {"pack_qty", "has_encoder", "cells", "channels"}
_TEXT = {
    "component_id", "category", "name", "manufacturer", "part_number", "vendor", "motor_family", "chemistry",
    "fits_motor_family", "data_quality", "source_url", "source_page", "retrieved_on", "notes",
}
FILTERABLE = _NUMERIC | _INTEGER | {"motor_family", "chemistry", "fits_motor_family", "data_quality", "manufacturer"}
_FILTER_RE = re.compile(r"^\s*([a-z_]+)\s*(>=|<=|==|=|>|<|!=)\s*(.+?)\s*$")


class FilterError(ValueError):
    """Raised for a malformed or non-whitelisted filter expression."""


def _sql_type(column: str) -> str:
    if column in _NUMERIC:
        return "REAL"
    if column in _INTEGER:
        return "INTEGER"
    return "TEXT"


def build_database(db_path: Path | None = None, csv_path: Path = COMPONENTS_CSV) -> Path:
    """(Re)build the SQLite database from the CSV. Idempotent."""
    db_path = db_path or DATA_DIR / "components.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = list(reader.fieldnames or [])
        rows = list(reader)
    con = sqlite3.connect(db_path)
    try:
        con.execute("DROP TABLE IF EXISTS components")
        cols_sql = ", ".join(f"{c} {_sql_type(c)}" + (" PRIMARY KEY" if c == "component_id" else "") for c in columns)
        con.execute(f"CREATE TABLE components ({cols_sql})")
        placeholders = ", ".join("?" for _ in columns)
        con.executemany(
            f"INSERT INTO components ({', '.join(columns)}) VALUES ({placeholders})",
            [[_coerce(c, row[c]) for c in columns] for row in rows],
        )
        con.commit()
    finally:
        con.close()
    return db_path


def _coerce(column: str, raw: str):
    raw = raw.strip()
    if raw == "":
        return None
    if column in _NUMERIC:
        return float(raw)
    if column in _INTEGER:
        return int(float(raw))
    return raw


def parse_filter(expr: str) -> tuple[str, str, object]:
    """Parse ``'capacity_mah >= 4000'`` into a safe (column, operator, value) triple."""
    m = _FILTER_RE.match(expr)
    if not m:
        raise FilterError(f"Cannot parse filter '{expr}'. Use the form 'column >= value'.")
    column, op, value = m.group(1), m.group(2), m.group(3).strip().strip("'\"")
    if column not in FILTERABLE:
        raise FilterError(f"Column '{column}' is not filterable. Allowed: {', '.join(sorted(FILTERABLE))}.")
    op = "=" if op == "==" else op
    if column in _NUMERIC or column in _INTEGER:
        try:
            return column, op, float(value)
        except ValueError as exc:
            raise FilterError(f"Value for '{column}' must be numeric, got '{value}'.") from exc
    if op not in ("=", "!="):
        raise FilterError(f"Text column '{column}' supports only = and !=.")
    return column, op, value


class ComponentDB:
    """Read-only access to the component table."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DATA_DIR / "components.db"
        if not self.db_path.exists() or self.db_path.stat().st_mtime < COMPONENTS_CSV.stat().st_mtime:
            build_database(self.db_path)

    def _query(self, sql: str, params: list) -> list[Component]:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(sql, params).fetchall()
        finally:
            con.close()
        return [Component(**{k: row[k] for k in row.keys() if row[k] is not None}) for row in rows]

    def get(self, component_id: str) -> Component | None:
        found = self._query("SELECT * FROM components WHERE component_id = ?", [component_id.strip()])
        return found[0] if found else None

    def all(self) -> list[Component]:
        return self._query("SELECT * FROM components ORDER BY category, price_usd", [])

    def categories(self) -> list[str]:
        return sorted({c.category for c in self.all()})

    def search(self, category: str, filters: list[str] | None = None, sort_by: str = "price_usd",
               limit: int = 10) -> list[Component]:
        """Filter one category with whitelisted expressions. Raises FilterError on bad input."""
        where, params = ["category = ?"], [category]
        for expr in filters or []:
            column, op, value = parse_filter(expr)
            where.append(f"{column} {op} ?")
            params.append(value)
        if sort_by.lstrip("-") not in FILTERABLE:
            raise FilterError(f"Cannot sort by '{sort_by}'.")
        direction = "DESC" if sort_by.startswith("-") else "ASC"
        sql = (f"SELECT * FROM components WHERE {' AND '.join(where)} "
               f"ORDER BY {sort_by.lstrip('-')} {direction} LIMIT ?")
        return self._query(sql, [*params, max(1, min(int(limit), 50))])


_DB: ComponentDB | None = None
_DB_LOCK = threading.Lock()


def get_db() -> ComponentDB:
    """Process-wide database handle (thread-safe first build)."""
    global _DB
    with _DB_LOCK:
        if _DB is None:
            _DB = ComponentDB()
        return _DB
