"""Linear brushed-DC gearmotor model built only from datasheet parameters.

Inputs (all from the manufacturer's spec table, referred to the gearbox output):
no-load speed n0, no-load current I0, stall torque Ts and stall current Is at the
rated voltage Vr. Standard linear-motor relations:

    R      = Vr / Is                       (terminal resistance)
    Kt     = Ts / (Is - I0)                (output torque per amp above no-load)
    Ke     = (Vr - I0 * R) / w0            (back-EMF constant at the output shaft)
    I(T)   = I0 + T / Kt
    V(w,T) = I(T) * R + Ke * w             (terminal voltage needed for speed w at torque T)

At a supply voltage V the speed-torque line scales as n0' = n0 * V/Vr and
Ts' = Ts * V/Vr (and Is' = Is * V/Vr), the usual first-order approximation.
"""

from __future__ import annotations

from dataclasses import dataclass

from hermes.tools.engineering.dynamics import rpm_to_rad_s


@dataclass(frozen=True)
class MotorModel:
    rated_voltage_v: float
    no_load_rpm: float
    no_load_current_a: float
    stall_torque_nm: float
    stall_current_a: float

    @property
    def resistance_ohm(self) -> float:
        return self.rated_voltage_v / self.stall_current_a

    @property
    def kt_nm_per_a(self) -> float:
        return self.stall_torque_nm / (self.stall_current_a - self.no_load_current_a)

    @property
    def ke_v_s_per_rad(self) -> float:
        w0 = rpm_to_rad_s(self.no_load_rpm)
        return (self.rated_voltage_v - self.no_load_current_a * self.resistance_ohm) / w0

    # --- operating at supply voltage V --------------------------------------
    def no_load_rpm_at(self, supply_v: float) -> float:
        return self.no_load_rpm * supply_v / self.rated_voltage_v

    def stall_torque_at(self, supply_v: float) -> float:
        return self.stall_torque_nm * supply_v / self.rated_voltage_v

    def stall_current_at(self, supply_v: float) -> float:
        return self.stall_current_a * supply_v / self.rated_voltage_v

    def speed_rpm_at_torque(self, torque_nm: float, supply_v: float) -> float:
        """Full-throttle speed under load: n = n0' * (1 - T / Ts')."""
        return max(0.0, self.no_load_rpm_at(supply_v) * (1.0 - torque_nm / self.stall_torque_at(supply_v)))

    def current_at_torque(self, torque_nm: float) -> float:
        """I = I0 + T / Kt (independent of speed in the linear model)."""
        return self.no_load_current_a + torque_nm / self.kt_nm_per_a

    def electrical_power_w(self, torque_nm: float, speed_rpm: float) -> float:
        """Power drawn at the motor terminals to hold `speed_rpm` against `torque_nm` (PWM-controlled)."""
        current = self.current_at_torque(torque_nm)
        voltage = current * self.resistance_ohm + self.ke_v_s_per_rad * rpm_to_rad_s(speed_rpm)
        return voltage * current

    def mechanical_power_w(self, torque_nm: float, speed_rpm: float) -> float:
        return torque_nm * rpm_to_rad_s(speed_rpm)
