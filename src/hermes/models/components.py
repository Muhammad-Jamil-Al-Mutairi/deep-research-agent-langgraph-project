"""Component records from the structured component database."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from hermes.config import KGCM_TO_NM

DataQuality = Literal["sourced", "partial", "assumed"]

# Domain -> component categories that a research stage is responsible for.
DOMAIN_CATEGORIES: dict[str, tuple[str, ...]] = {
    "motor": ("motor",),
    "battery": ("battery",),
    "mechanical": ("wheel", "hub", "bracket", "caster", "chassis", "structure"),
    "electronics": ("motor_driver", "controller", "imu", "range_sensor", "regulator", "wiring"),
}


class Component(BaseModel):
    """One row of the component database. Missing specs are None, never guessed."""

    component_id: str
    category: str
    name: str
    manufacturer: str
    part_number: str
    vendor: str
    price_usd: float
    pack_qty: int = 1
    weight_g: float | None = None
    length_mm: float | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    rated_voltage_v: float | None = None
    voltage_min_v: float | None = None
    voltage_max_v: float | None = None
    gear_ratio: float | None = None
    no_load_rpm: float | None = None
    no_load_current_a: float | None = None
    stall_current_a: float | None = None
    stall_torque_kgcm: float | None = None
    max_power_w: float | None = None
    cont_torque_limit_kgcm: float | None = None
    peak_torque_limit_kgcm: float | None = None
    has_encoder: bool | None = None
    shaft_diameter_mm: float | None = None
    motor_family: str | None = None
    chemistry: str | None = None
    cells: int | None = None
    capacity_mah: float | None = None
    c_rating: float | None = None
    cont_current_a: float | None = None
    peak_current_a: float | None = None
    channels: int | None = None
    logic_v_min: float | None = None
    logic_v_max: float | None = None
    output_v: float | None = None
    supply_current_ma: float | None = None
    supply_voltage_v: float | None = None
    wheel_diameter_mm: float | None = None
    bore_mm: float | None = None
    fits_shaft_mm: float | None = None
    fits_motor_family: str | None = None
    data_quality: DataQuality
    source_url: str
    source_page: str
    retrieved_on: str
    notes: str = ""

    # ---- convenience views in SI units ------------------------------------
    @property
    def stall_torque_nm(self) -> float | None:
        return None if self.stall_torque_kgcm is None else self.stall_torque_kgcm * KGCM_TO_NM

    @property
    def cont_torque_limit_nm(self) -> float | None:
        return None if self.cont_torque_limit_kgcm is None else self.cont_torque_limit_kgcm * KGCM_TO_NM

    @property
    def peak_torque_limit_nm(self) -> float | None:
        return None if self.peak_torque_limit_kgcm is None else self.peak_torque_limit_kgcm * KGCM_TO_NM

    @property
    def energy_wh(self) -> float | None:
        if self.rated_voltage_v is None or self.capacity_mah is None:
            return None
        return self.rated_voltage_v * self.capacity_mah / 1000.0

    @property
    def max_cont_discharge_a(self) -> float | None:
        if self.c_rating is None or self.capacity_mah is None:
            return None
        return self.c_rating * self.capacity_mah / 1000.0

    def citation(self) -> str:
        if self.data_quality == "assumed":
            return "ASSUMED (no external source)"
        page = "" if self.source_page in ("web", "", "N/A") else f", p.{self.source_page}"
        return f"{self.source_url}{page} (retrieved {self.retrieved_on})"

    def key_spec(self) -> str:
        """One-line human summary of the most decision-relevant specs."""
        c = self.category
        if c == "motor":
            enc = "encoder" if self.has_encoder else "no encoder"
            return (f"{self.gear_ratio}:1, {self.no_load_rpm:.0f} rpm no-load, stall {self.stall_torque_kgcm} kg-cm / "
                    f"{self.stall_current_a} A @ {self.rated_voltage_v:.0f} V, {enc}")
        if c == "battery":
            c_txt = f", {self.c_rating:.0f}C" if self.c_rating else ""
            return f"{self.chemistry} {self.rated_voltage_v} V {self.capacity_mah:.0f} mAh ({self.energy_wh:.1f} Wh){c_txt}"
        if c == "motor_driver":
            return f"{self.channels} ch, {self.cont_current_a} A cont/ch, {self.voltage_min_v}-{self.voltage_max_v} V"
        if c == "regulator":
            return f"{self.output_v} V out, {self.cont_current_a} A, {self.voltage_min_v}-{self.voltage_max_v} V in"
        if c == "wheel":
            return (f"{self.wheel_diameter_mm:.0f} mm diameter, {self.bore_mm} mm bore "
                    "(needs one mounting hub per wheel to fit a larger motor shaft)")
        if c == "hub":
            return f"for {self.fits_shaft_mm:.0f} mm shaft, joins one wheel to one motor"
        if c == "bracket":
            return f"for {self.fits_motor_family} gearmotors"
        if c in ("controller", "range_sensor") and self.supply_current_ma:
            return f"{self.supply_current_ma:.0f} mA @ {self.supply_voltage_v} V"
        return self.data_quality
