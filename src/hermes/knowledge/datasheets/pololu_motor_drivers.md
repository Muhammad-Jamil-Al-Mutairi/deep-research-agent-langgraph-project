---
title: Pololu brushed DC motor drivers - TB6612FNG carrier, Dual VNH5019 shield, G2 18v17
manufacturer: Pololu
source_url: https://www.pololu.com/product/713/specs
page: web
component_ids: POL-713, POL-2507, POL-2991
part_numbers: 713, 2507, 2991
retrieved_on: 2026-10-07
---

# Pololu brushed DC motor drivers

## TB6612FNG Dual Motor Driver Carrier (item 713)

Components: POL-713

Source: https://www.pololu.com/product/713/specs

- Motor channels: 2. Size 0.60 x 0.80 inch, weight 1.5 g.
- Operating voltage: 4.5 V minimum (can operate down to 2.5 V with reduced current capabilities), 13.5 V maximum.
- Continuous output current per channel: 1 A. Peak output current per channel: 3 A. Continuous paralleled output current: 2 A.
- Maximum PWM frequency: 100 kHz. Logic voltage 2.7 V to 5.5 V. Reverse voltage protection: yes.
- Price 4.95 USD (qty 1).

## Dual VNH5019 Motor Driver Shield for Arduino (item 2507)

Components: POL-2507

Source: https://www.pololu.com/product/2507/specs

- Motor channels: 2. Size 2.56 x 2.02 x 0.38 inch, weight 18 g without included hardware.
- Operating voltage: 5.5 V minimum, 24 V maximum; not recommended for use with 24 V batteries.
- Continuous output current per channel: 12 A. Peak output current per channel: 30 A.
- Current sense: 0.14 V/A. Maximum PWM frequency: 20 kHz.
- Reverse voltage protection to -16 V; connecting supplies over 16 V in reverse can damage the driver.
- The specs page does not state a logic-voltage range. Arduino shield form factor.
- Price 39.95 USD (qty 1).

## G2 High-Power Motor Driver 18v17 (item 2991)

Components: POL-2991

Source: https://www.pololu.com/product/2991/specs

- Motor channels: 1 (two units are needed for a differential-drive robot). Size 1.3 x 0.8 inch, weight 3.3 g without connectors.
- Operating voltage: 6.5 V minimum, 30 V absolute maximum; higher voltages can permanently destroy the driver. Recommended maximum is approximately 24 V, which leaves a safety margin for ripple voltage on the supply line. Not recommended for use with 24 V batteries.
- Continuous output current: 17 A (typical results with 100% duty cycle at room temperature).
- Current sense: 0.02 V/A. Maximum PWM frequency: 100 kHz. Logic voltage 1.8 V to 5.5 V. Reverse voltage protection: yes.
- Price 44.95 USD (qty 1).

## Selection guidance

Components: POL-713, POL-2507, POL-2991

Pololu generally recommends a motor controller that can handle continuous currents above the stall current of the motor (stated on the 37D and 25D gearmotor pages). The 12 V 37D gearmotors stall at 5.5 A and the HP 12 V 25D gearmotors at 5.0 A (extrapolated), so a 1 A-per-channel driver such as the TB6612FNG is below that recommendation, while the VNH5019 (12 A) and G2 18v17 (17 A) exceed it.
