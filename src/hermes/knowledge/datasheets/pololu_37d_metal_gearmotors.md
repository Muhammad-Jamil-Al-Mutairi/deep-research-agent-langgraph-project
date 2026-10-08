---
title: Pololu 37D mm Metal Gearmotors, 12 V (helical pinion), with and without 64 CPR encoder
manufacturer: Pololu
source_url: https://www.pololu.com/product/4752
page: web
component_ids: POL-4741, POL-4742, POL-4743, POL-4751, POL-4752, POL-4753
part_numbers: 4741, 4742, 4743, 4751, 4752, 4753
retrieved_on: 2026-10-07
---

# Pololu 37D mm metal gearmotors (12 V)

## Family overview

Measuring 37 mm in diameter, these brushed DC gearmotors are the largest and most powerful Pololu carries. They are available in gear ratios from 6.3:1 to 150:1 and with 12 V or 24 V motors, and all versions are available with integrated 64 CPR quadrature encoders on the motor shafts. The 12 V and 24 V motors offer approximately the same performance at their respective nominal voltages, with the 24 V motor drawing half the current of the 12 V motor. The gearbox is composed mainly of spur gears, with helical gears for the first stage for reduced noise and improved efficiency. The output shaft is 16 mm long, 6 mm diameter, D-shaped.

## Performance table at 12 V (from the family comparison table)

All 12 V versions: stall current 5.5 A, no-load current 0.2 A (extrapolated stall values).

| Gear ratio | No-load speed | Stall torque | Max power | Without encoder | With encoder |
|---|---|---|---|---|---|
| 19:1 (18.75:1) | 530 rpm | 8.5 kg-cm | 12 W | item 4741 | item 4751 |
| 30:1 | 330 rpm | 14 kg-cm | 12 W | item 4742 | item 4752 |
| 50:1 | 200 rpm | 21 kg-cm | 10 W | item 4743 | item 4753 |

## Specifications per item (specs pages)

- 4741 (19:1, no encoder): 37D x 52L mm, 185 g. Max efficiency 55% at 470 rpm, 1.0 kg-cm, 0.76 A, 5.0 W output (12 V). At 6 V: 270 rpm no-load, 3.0 A stall, 5.0 kg-cm stall.
- 4742 (30:1, no encoder): 37D x 52L mm, 185 g. Max efficiency 54% at 280 rpm, 1.8 kg-cm, 0.78 A, 5.1 W output (12 V). At 6 V: 170 rpm, 3.0 A stall, 7.9 kg-cm stall.
- 4743 (50:1, no encoder): 37D x 54L mm, 190 g. Max efficiency 51% at 180 rpm, 2.2 kg-cm, 0.66 A, 4.0 W output (12 V).
- 4751 (19:1, 64 CPR encoder): 37D x 68L mm, 200 g. Price 60.95 USD (qty 1).
- 4752 (30:1, 64 CPR encoder): 37D x 68L mm, 200 g. Encoder gives 1920 counts per revolution of the gearbox output shaft. Price 60.95 USD (qty 1).
- 4753 (50:1, 64 CPR encoder): 37D x 70L mm, 205 g. Price 60.95 USD (qty 1).
- Versions without encoder: 38.95 USD (qty 1).

## Load limits and thermal guidance

The listed stall torques and currents are theoretical extrapolations; units will typically stall well before these points as the motors heat up. Stalling or overloading gearmotors can greatly decrease their lifetimes and even result in immediate damage. The recommended upper limit for continuously applied loads is 10 kg-cm (150 oz-in), and the recommended upper limit for instantaneous torque is 25 kg-cm (350 oz-in). Stalls can also result in rapid (potentially on the order of seconds) thermal damage to the motor windings and brushes; a general recommendation for brushed DC motor operation is 25% or less of the stall current.

Output power for the 70:1 and higher ratios is constrained by gearbox load limits; the spec provided is output power at the maximum recommended load of 10 kg-cm.

## Motor driver recommendation

Pololu's high-power motor drivers and Motoron controllers are available in various power levels, several of which can handle the 37D mm metal gearmotors. Pololu generally recommends a motor controller that can handle continuous currents above the stall current of your motor.

## Encoder

A two-channel Hall effect encoder senses the rotation of a magnetic disk on a rear protrusion of the motor shaft. The quadrature encoder provides a resolution of 64 counts per revolution of the motor shaft when counting both edges of both channels. To compute the counts per revolution of the gearbox output, multiply the gear ratio by 64. The motor/encoder has six colour-coded, 8 inch (20 cm) leads terminated by a 1x6 female header with 0.1 inch pitch.

## Mounting wheels

Components: POL-4741, POL-4742, POL-4743, POL-4751, POL-4752, POL-4753, POL-1083, POL-1084, POL-1435, POL-1430

The 6 mm diameter gearbox output shaft works with the Pololu universal aluminum mounting hub for 6 mm shafts, which can be used to mount Pololu wheels (80 mm and 90 mm diameter) or custom wheels and mechanisms to the gearmotor's output shaft. Pololu's stamped aluminum L-bracket pair is made for mounting 37D mm gearmotors.
