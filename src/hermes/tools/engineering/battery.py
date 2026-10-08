"""Battery energy, runtime and sizing calculations."""

from __future__ import annotations


def pack_energy_wh(voltage_v: float, capacity_mah: float) -> float:
    """E = V * C  [Wh]."""
    return voltage_v * capacity_mah / 1000.0


def usable_energy_wh(energy_wh: float, usable_fraction: float) -> float:
    return energy_wh * usable_fraction


def runtime_hours(usable_wh: float, average_power_w: float) -> float:
    """t = E_usable / P_avg  [h]."""
    if average_power_w <= 0:
        raise ValueError("average power must be positive")
    return usable_wh / average_power_w


def required_capacity_mah(runtime_h: float, average_power_w: float, voltage_v: float,
                          usable_fraction: float) -> float:
    """Capacity needed for a target runtime: C = t * P / (V * usable)  [mAh]."""
    return runtime_h * average_power_w / (voltage_v * usable_fraction) * 1000.0


def max_continuous_current_a(capacity_mah: float, c_rating: float) -> float:
    """I_max = C-rating * capacity  [A]."""
    return c_rating * capacity_mah / 1000.0
