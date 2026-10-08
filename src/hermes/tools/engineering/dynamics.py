"""Vehicle dynamics: forces, wheel torque and wheel speed for a wheeled robot."""

from __future__ import annotations

import math

from hermes.config import G


def rolling_resistance_force(mass_kg: float, crr: float) -> float:
    """F_rr = Crr * m * g  [N]."""
    return crr * mass_kg * G


def grade_force(mass_kg: float, grade_deg: float) -> float:
    """F_grade = m * g * sin(theta)  [N]."""
    return mass_kg * G * math.sin(math.radians(grade_deg))


def acceleration_force(mass_kg: float, accel_mps2: float) -> float:
    """F_acc = m * a  [N]."""
    return mass_kg * accel_mps2


def torque_per_motor(total_force_n: float, wheel_radius_m: float, n_drive_motors: int) -> float:
    """Wheel torque each drive motor must supply: T = F * r / n  [N-m] (direct drive)."""
    if n_drive_motors <= 0:
        raise ValueError("n_drive_motors must be positive")
    return total_force_n * wheel_radius_m / n_drive_motors


def wheel_rpm_for_speed(speed_mps: float, wheel_diameter_m: float) -> float:
    """rpm = v / (pi * d) * 60."""
    return speed_mps / (math.pi * wheel_diameter_m) * 60.0


def speed_from_wheel_rpm(rpm: float, wheel_diameter_m: float) -> float:
    """v = rpm * pi * d / 60  [m/s]."""
    return rpm * math.pi * wheel_diameter_m / 60.0


def rpm_to_rad_s(rpm: float) -> float:
    return rpm * 2.0 * math.pi / 60.0
