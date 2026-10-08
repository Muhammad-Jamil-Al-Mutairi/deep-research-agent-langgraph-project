"""Full deterministic engineering analysis of one design.

Every number the verifier and the report use is computed here from database specs
(SOURCED) and mission-profile values (ASSUMED). The LLM never supplies numbers.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from hermes.models.components import Component
from hermes.models.design import BOM
from hermes.models.requirements import MissionProfile, Requirements
from hermes.models.verification import Calculation
from hermes.tools.engineering import battery as bat
from hermes.tools.engineering import dynamics as dyn
from hermes.tools.engineering.motor import MotorModel
from hermes.tools.research.component_db import ComponentDB

ELECTRONICS = ("controller", "imu", "range_sensor")


class DesignAnalysis(BaseModel):
    calcs: dict[str, Calculation] = Field(default_factory=dict)
    roles: dict[str, list[str]] = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list, description="Structural problems that prevent a calculation.")
    unverified: list[str] = Field(default_factory=list, description="Specs that were missing and replaced by an allowance.")

    def value(self, name: str) -> float | None:
        calc = self.calcs.get(name)
        return None if calc is None else calc.value


class _Recorder:
    def __init__(self, analysis: DesignAnalysis):
        self.a = analysis

    def __call__(self, name: str, value: float | None, unit: str, formula: str,
                 provenance: str = "CALCULATED", note: str = "") -> float | None:
        rounded = None if value is None else round(value, 4)
        self.a.calcs[name] = Calculation(name=name, value=rounded, unit=unit, formula=formula,
                                         provenance=provenance, note=note)
        return value


def _components(bom: BOM, db: ComponentDB) -> dict[str, Component]:
    return {line.component_id: comp for line in bom.lines if (comp := db.get(line.component_id))}


def analyse_design(bom: BOM, req: Requirements, profile: MissionProfile, db: ComponentDB) -> DesignAnalysis:
    """Compute mass, forces, torques, speeds, currents, power, energy, runtime and cost."""
    a = DesignAnalysis()
    rec = _Recorder(a)
    comps = _components(bom, db)
    for line in bom.lines:
        a.roles.setdefault(line.category, []).append(line.component_id)

    # ---- mass and cost ---------------------------------------------------
    components_kg = bom.total_mass_g / 1000.0
    rec("component_mass", components_kg, "kg", f"sum of BOM line masses = {bom.total_mass_g:.1f} g",
        note=f"{len(bom.unverified_mass_items)} item(s) without a verified mass" if bom.unverified_mass_items else "")
    mass_kg = rec("total_mass", components_kg + req.payload_kg, "kg",
                  f"components {components_kg:.3f} kg + payload {req.payload_kg:.3f} kg")
    rec("bom_cost_sar", bom.total_cost_sar, "SAR", f"{bom.total_cost_usd:.2f} USD x 3.75 SAR/USD (BOM)")
    a.unverified.extend(f"mass of {cid}" for cid in bom.unverified_mass_items)

    motor_lines = bom.by_category("motor")
    wheel_lines = bom.by_category("wheel")
    battery_lines = bom.by_category("battery")
    if len(motor_lines) != 1:
        a.issues.append(f"expected exactly one drive-motor part type, found {len(motor_lines)}")
    if not wheel_lines:
        a.issues.append("no drive wheels in the BOM")
    if len(battery_lines) != 1 or battery_lines[0].quantity != 1:
        a.issues.append("expected exactly one battery pack (parallel packs are not modelled)")
    if a.issues:
        return a

    motor = comps[motor_lines[0].component_id]
    n_motors = motor_lines[0].quantity
    wheel = comps[wheel_lines[0].component_id]
    battery = comps[battery_lines[0].component_id]
    needed = {"motor stall torque": motor.stall_torque_kgcm, "motor stall current": motor.stall_current_a,
              "motor no-load speed": motor.no_load_rpm, "wheel diameter": wheel.wheel_diameter_mm,
              "battery voltage": battery.rated_voltage_v, "battery capacity": battery.capacity_mah}
    missing = [k for k, v in needed.items() if v is None]
    if missing:
        a.issues.append("missing specs: " + ", ".join(missing))
        return a

    p = profile
    rec("n_drive_motors", n_motors, "-", "count of drive motors in BOM")
    d_m = wheel.wheel_diameter_mm / 1000.0
    r_m = d_m / 2.0
    v_batt = rec("supply_voltage", battery.rated_voltage_v, "V", f"nominal voltage of {battery.component_id}", "SOURCED")

    # ---- forces and torque -------------------------------------------------
    f_rr = rec("rolling_force", dyn.rolling_resistance_force(mass_kg, p.rolling_resistance_coeff), "N",
               f"Crr*m*g = {p.rolling_resistance_coeff} x {mass_kg:.3f} x 9.807")
    f_gr = rec("grade_force", dyn.grade_force(mass_kg, p.design_grade_deg), "N",
               f"m*g*sin({p.design_grade_deg} deg) = {mass_kg:.3f} x 9.807 x sin({p.design_grade_deg})")
    f_ac = rec("accel_force", dyn.acceleration_force(mass_kg, p.acceleration_mps2), "N",
               f"m*a = {mass_kg:.3f} x {p.acceleration_mps2}")
    t_level = rec("torque_level", dyn.torque_per_motor(f_rr, r_m, n_motors), "N-m",
                  f"F_rr*r/n = {f_rr:.3f} x {r_m:.4f} / {n_motors}")
    t_cont = rec("torque_continuous", dyn.torque_per_motor(f_rr + f_gr, r_m, n_motors), "N-m",
                 f"(F_rr+F_grade)*r/n = ({f_rr:.3f}+{f_gr:.3f}) x {r_m:.4f} / {n_motors}")
    t_peak = rec("torque_peak", dyn.torque_per_motor(f_rr + f_gr + f_ac, r_m, n_motors), "N-m",
                 f"(F_rr+F_grade+F_acc)*r/n = ({f_rr:.3f}+{f_gr:.3f}+{f_ac:.3f}) x {r_m:.4f} / {n_motors}")
    sf = p.torque_safety_factor
    rec("torque_continuous_design", t_cont * sf, "N-m", f"T_cont x SF = {t_cont:.4f} x {sf}")
    t_peak_d = rec("torque_peak_design", t_peak * sf, "N-m", f"T_peak x SF = {t_peak:.4f} x {sf}")

    model = MotorModel(rated_voltage_v=motor.rated_voltage_v or 12.0, no_load_rpm=motor.no_load_rpm,
                       no_load_current_a=motor.no_load_current_a or 0.0, stall_torque_nm=motor.stall_torque_nm,
                       stall_current_a=motor.stall_current_a)
    rec("motor_stall_torque_at_supply", model.stall_torque_at(v_batt), "N-m",
        f"Ts*V/Vr = {motor.stall_torque_nm:.4f} x {v_batt}/{model.rated_voltage_v}")
    stall_i = rec("motor_stall_current_at_supply", model.stall_current_at(v_batt), "A",
                  f"Is*V/Vr = {motor.stall_current_a} x {v_batt}/{model.rated_voltage_v}")

    # ---- speed -----------------------------------------------------------------
    rec("required_wheel_rpm", dyn.wheel_rpm_for_speed(req.max_speed_mps, d_m), "rpm",
        f"v/(pi*d)*60 = {req.max_speed_mps}/(pi x {d_m}) x 60")
    rpm_loaded = rec("loaded_wheel_rpm", model.speed_rpm_at_torque(t_level, v_batt), "rpm",
                     f"n0'*(1-T_level/Ts') at {v_batt} V")
    rec("achievable_speed", dyn.speed_from_wheel_rpm(rpm_loaded, d_m), "m/s", f"rpm*pi*d/60 = {rpm_loaded:.1f} x pi x {d_m}/60")

    # ---- current -----------------------------------------------------------
    rec("motor_current_continuous", model.current_at_torque(t_cont), "A",
                 f"I0 + T_cont/Kt = {model.no_load_current_a} + {t_cont:.4f}/{model.kt_nm_per_a:.4f}")
    i_peak = rec("motor_current_peak", model.current_at_torque(t_peak_d), "A",
                 f"I0 + T_peak_design/Kt = {model.no_load_current_a} + {t_peak_d:.4f}/{model.kt_nm_per_a:.4f}")
    rec("motor_thermal_current_limit", 0.25 * stall_i, "A", "25% of stall current at supply voltage (Pololu guidance)")

    # ---- power -------------------------------------------------------------
    cruise_rpm = dyn.wheel_rpm_for_speed(p.cruise_speed_mps, d_m)
    p_level = model.electrical_power_w(t_level, cruise_rpm)
    p_grade = model.electrical_power_w(t_cont, cruise_rpm)
    rec("motor_power_level", p_level, "W", f"per motor, T={t_level:.4f} N-m at {cruise_rpm:.0f} rpm (cruise {p.cruise_speed_mps} m/s)")
    rec("motor_power_grade", p_grade, "W", f"per motor, T={t_cont:.4f} N-m at {cruise_rpm:.0f} rpm")
    rec("mechanical_power_level", n_motors * model.mechanical_power_w(t_level, cruise_rpm), "W", "n x T_level x w_cruise")
    f = p.fraction_time_on_grade
    p_drive = rec("drive_power_avg", n_motors * ((1 - f) * p_level + f * p_grade) / p.driver_efficiency, "W",
                  f"n x ((1-{f}) x P_level + {f} x P_grade) / eta_driver({p.driver_efficiency})")

    p_logic = 0.0
    for cat in ELECTRONICS:
        for line in bom.by_category(cat):
            comp = comps[line.component_id]
            if comp.supply_current_ma is not None and comp.supply_voltage_v is not None:
                p_logic += line.quantity * comp.supply_current_ma / 1000.0 * comp.supply_voltage_v
            else:
                p_logic += line.quantity * p.unverified_device_power_w
                a.unverified.append(f"supply current of {line.component_id} (allowance {p.unverified_device_power_w} W used)")
    rec("logic_power", p_logic, "W", "sum of device supply current x voltage (allowance for unverified devices)")
    p_elec = rec("electronics_power_battery", p_logic / p.regulator_efficiency, "W",
                 f"logic power / eta_regulator({p.regulator_efficiency})")
    regs = bom.by_category("regulator")
    if regs and (out_v := comps[regs[0].component_id].output_v):
        rec("regulator_output_current", p_logic / out_v, "A", f"logic power / {out_v} V")
    p_total = rec("system_power_avg", p_drive + p_elec, "W", f"P_drive {p_drive:.2f} + P_electronics {p_elec:.2f}")

    # ---- battery and runtime -------------------------------------------------
    e_wh = rec("battery_energy", bat.pack_energy_wh(v_batt, battery.capacity_mah), "Wh",
               f"V x C = {v_batt} x {battery.capacity_mah} mAh")
    e_use = rec("battery_usable_energy", bat.usable_energy_wh(e_wh, p.battery_usable_fraction), "Wh",
                f"E x usable fraction = {e_wh:.2f} x {p.battery_usable_fraction}")
    rec("runtime", bat.runtime_hours(e_use, p_total), "h", f"E_usable / P_avg = {e_use:.2f} / {p_total:.2f}")
    rec("capacity_needed_for_runtime",
        bat.required_capacity_mah(req.runtime_h_min, p_total, v_batt, p.battery_usable_fraction), "mAh",
        f"t x P / (V x usable) = {req.runtime_h_min} x {p_total:.2f} / ({v_batt} x {p.battery_usable_fraction})")
    rec("battery_peak_current", n_motors * i_peak + p_elec / v_batt, "A",
        f"n x I_peak + P_elec/V = {n_motors} x {i_peak:.3f} + {p_elec:.2f}/{v_batt}")
    if battery.c_rating is not None:
        rec("battery_max_current", battery.max_cont_discharge_a, "A",
            f"C-rating x capacity = {battery.c_rating} x {battery.capacity_mah / 1000:.2f} Ah")
    else:
        a.unverified.append(f"maximum discharge current of {battery.component_id}")
    return a
