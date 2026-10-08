"""Deterministic engineering formulas, checked against hand calculations."""

import math

import pytest

from hermes.config import KGCM_TO_NM, G
from hermes.tools.engineering import battery as bat
from hermes.tools.engineering import dynamics as dyn
from hermes.tools.engineering.motor import MotorModel


def test_forces_match_hand_calculation():
    assert dyn.rolling_resistance_force(4.0, 0.02) == pytest.approx(0.02 * 4.0 * G)
    assert dyn.grade_force(4.0, 5.0) == pytest.approx(4.0 * G * math.sin(math.radians(5.0)))  # 3.419 N
    assert dyn.grade_force(4.0, 5.0) == pytest.approx(3.419, abs=1e-3)
    assert dyn.acceleration_force(4.0, 0.5) == 2.0


def test_torque_per_motor_splits_between_drive_motors():
    assert dyn.torque_per_motor(10.0, 0.045, 2) == pytest.approx(0.225)
    with pytest.raises(ValueError):
        dyn.torque_per_motor(10.0, 0.045, 0)


def test_wheel_speed_round_trip():
    rpm = dyn.wheel_rpm_for_speed(1.5, 0.090)
    assert rpm == pytest.approx(318.3, abs=0.1)  # 1.5 / (pi * 0.09) * 60
    assert dyn.speed_from_wheel_rpm(rpm, 0.090) == pytest.approx(1.5)


@pytest.fixture
def pololu_4752():
    # 30:1 37D 12 V: 330 rpm, 0.2 A no-load, 14 kg-cm / 5.5 A stall (Pololu specs page)
    return MotorModel(rated_voltage_v=12, no_load_rpm=330, no_load_current_a=0.2,
                      stall_torque_nm=14 * KGCM_TO_NM, stall_current_a=5.5)


def test_motor_model_end_points(pololu_4752):
    m = pololu_4752
    assert m.speed_rpm_at_torque(0.0, 12) == pytest.approx(330)
    assert m.speed_rpm_at_torque(m.stall_torque_nm, 12) == pytest.approx(0)
    assert m.current_at_torque(0.0) == pytest.approx(0.2)
    assert m.current_at_torque(m.stall_torque_nm) == pytest.approx(5.5)
    assert m.resistance_ohm == pytest.approx(12 / 5.5)


def test_motor_model_scales_with_supply_voltage(pololu_4752):
    m = pololu_4752
    assert m.no_load_rpm_at(11.1) == pytest.approx(330 * 11.1 / 12)
    assert m.stall_torque_at(6.0) == pytest.approx(m.stall_torque_nm / 2)
    # half stall torque at rated voltage -> half no-load speed
    assert m.speed_rpm_at_torque(m.stall_torque_nm / 2, 12) == pytest.approx(165)


def test_motor_electrical_power_exceeds_mechanical(pololu_4752):
    m = pololu_4752
    t, rpm = 0.2, 200
    assert m.electrical_power_w(t, rpm) > m.mechanical_power_w(t, rpm) > 0


def test_battery_energy_runtime_and_sizing():
    e = bat.pack_energy_wh(11.1, 6000)
    assert e == pytest.approx(66.6)
    usable = bat.usable_energy_wh(e, 0.8)
    assert bat.runtime_hours(usable, 10.0) == pytest.approx(5.328)
    # sizing is the inverse of runtime
    assert bat.required_capacity_mah(5.328, 10.0, 11.1, 0.8) == pytest.approx(6000, rel=1e-6)
    assert bat.max_continuous_current_a(2200, 50) == pytest.approx(110)
    with pytest.raises(ValueError):
        bat.runtime_hours(10, 0)
