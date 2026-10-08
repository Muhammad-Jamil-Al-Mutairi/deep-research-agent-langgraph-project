# HERMES Engineering Report - Small Autonomous Delivery Robot

**AI-generated engineering proposal - not a certified engineering design.**

**Final status: VERIFIED.** The final design satisfies the specified computational constraints.

## Executive Summary

**Executive Summary – Final Engineering Proposal**

The final design (Iteration #2, “balanced”) satisfies the specified computational constraints (PASS, score 0.0). Two design iterations were required: the first (“economy”) failed due to an incompatible motor driver (POL-713) that could not meet the continuous current requirement. The second iteration replaced the driver with POL-2507 (2 ch, 12 A cont/ch), resolving the current constraint and achieving verification.

The system uses two POL-4843 drive motors with 90 mm wheels, an ESP32 controller, a 66.6 Wh LiPo battery, and a plywood chassis with payload bin. Key computed performance: total mass 3.44 kg, achievable speed 2.13 m/s, peak motor current 1.47 A, average system power 6.82 W, and runtime 7.82 hours. Total BOM cost is 1,387 SAR.

Two specifications remain unverified: the driver logic-level range (POL-2507) and the mass/supply current of the IMU sensor (ADA-4646). Additionally, three items (chassis, payload bin, wiring) are engineering allowances, not sourced parts. Physical validation and qualified engineering review are required before real-world deployment.

## Requirements

| Requirement | Value | Type |
|---|---|---|
| Payload | 2.0 kg | explicit |
| Runtime | >= 2.0 h | explicit |
| Top speed | >= 1.5 m/s | explicit |
| Total mass | <= 8.0 kg (incl. payload) | explicit (payload interpretation: see assumptions) |
| Budget | <= 1,500 SAR | explicit |
| Feature | wheel_encoders | derived |
| Feature | imu | derived |
| Feature | range_sensor | derived |

## Assumptions

| ID | Assumption | Value | Rationale / origin |
|---|---|---|---|
| A1 | Total mass limit of 8 kg includes the 2 kg payload. | true | Conservative interpretation; the user did not specify whether the mass limit includes payload. |
| A2 | Budget of 1500 SAR is for BOM (components) only, not including assembly, shipping, or taxes. |  | Typical for component-level design; user did not specify scope of budget. |
| A3 | The robot operates on relatively flat indoor/outdoor paved surfaces (design_grade_deg = 0). |  | No mention of slopes, stairs, or rough terrain. |
| P-cruise_speed_mps | Average driving speed used for the energy estimate, m/s. | 1.0 | mission profile (ASSUMED) |
| P-design_grade_deg | Steepest ramp the robot must climb, degrees. | 5.0 | mission profile (ASSUMED) |
| P-fraction_time_on_grade | Fraction of drive time spent climbing the design grade. | 0.1 | mission profile (ASSUMED) |
| P-acceleration_mps2 | Peak acceleration requirement, m/s^2. | 0.5 | mission profile (ASSUMED) |
| P-rolling_resistance_coeff | Rolling resistance coefficient of small hard wheels. | 0.02 | mission profile (ASSUMED) |
| P-torque_safety_factor | Safety factor applied to torque requirements. | 1.5 | mission profile (ASSUMED) |
| P-battery_usable_fraction | Fraction of nameplate battery energy that is usable. | 0.8 | mission profile (ASSUMED) |
| P-regulator_efficiency | Efficiency of the logic step-down regulator. | 0.85 | mission profile (ASSUMED) |
| P-driver_efficiency | Motor driver efficiency. | 0.95 | mission profile (ASSUMED) |
| P-unverified_device_power_w | Power allowance for an electronic device whose supply current is not verified, W. | 0.25 | mission profile (ASSUMED) |

### Derived requirements

- Autonomous navigation and delivery implies the need for odometry (wheel_encoders), heading (IMU), and obstacle detection (range_sensor).
- Payload of 2 kg and total mass ≤ 8 kg leaves ≤ 6 kg for the robot chassis, drivetrain, battery, electronics, and all other components.
- Runtime ≥ 2 hours at typical cruise speed (assumed ~1.0 m/s) requires sufficient battery capacity; peak power for 1.5 m/s top speed must also be supported.
- Budget ≤ 1500 SAR (approx. 400 USD) constrains component selection to low-cost, commercially available hobby/educational robotics parts.

### Open questions for a human engineer

- Should the robot operate indoors, outdoors, or both? (Impacts wheel type, motor protection, sensor range.)
- What is the typical operating terrain? (Flat floors, carpet, pavement, gravel?)
- Is the 1500 SAR budget inclusive of all components (motors, battery, controller, sensors, chassis) or just the electronics?
- What is the acceptable recharge time? (Impacts battery chemistry choice.)
- Are there any size constraints (footprint, height) for the robot?
- Is the robot expected to carry the payload in a container/tote, or is the payload integrated?

## Selected Architecture - Final design #2

Differential-drive platform: two direct-drive gearmotors with wheels on universal hubs, a ball caster, one battery pack feeding the motor driver directly and the controller through a step-down regulator.

- **motor**: 2 x 20.4:1 Metal Gearmotor 25Dx65L mm HP 12V with 48 CPR Encoder (POL-4843)
- **motor_driver**: 1 x Dual VNH5019 Motor Driver Shield for Arduino (POL-2507)
- **battery**: 1 x OVONIC 3S 6000mAh 80C 11.1V LiPo Battery (Deans T) (OVO-3S-6000-80C)
- **regulator**: 1 x 5V 2.5A Step-Down Voltage Regulator D24V22F5 (POL-2858)
- **controller**: 1 x ESP32 Feather V2 - 8MB Flash + 2 MB PSRAM (ADA-5400)
- **imu**: 1 x 9-DOF Absolute Orientation IMU Fusion Breakout - BNO055 (STEMMA QT) (ADA-4646)
- **range_sensor**: 1 x VL53L1X Time-of-Flight Distance Sensor Carrier, 400 cm max (POL-3415)
- **wheel**: 2 x Wheel 90x10mm Pair - Black (POL-1435)
- **hub**: 2 x Universal Aluminum Mounting Hub for 4mm Shaft, #4-40 Holes (2-Pack) (POL-1081)
- **bracket**: 2 x 25D mm Metal Gearmotor Bracket Pair (POL-2676)
- **caster**: 1 x Ball Caster with 1in Plastic Ball and Plastic Rollers (POL-2691)
- **chassis**: 1 x Custom plywood base plate 300x250x6 mm (HRM-CHASSIS-PLY6)
- **structure**: 1 x Payload bin / enclosure (2 kg class) (HRM-PAYLOAD-BIN)
- **wiring**: 1 x Wiring, connectors, fuse, switch and fasteners allowance (HRM-WIRING-KIT)

## Component Selection

The previous design failed because POL-713 (1 A cont/ch) was under-rated for the motor peak current of 1.46 A and stall current of 5.0 A. Replacing it with POL-2507 (12 A cont/ch, 150 SAR, 18 g) provides ample margin (12 A >> 1.46 A peak and 5.0 A stall). All other parts from the closest design are retained because they passed their individual constraints. The IMU (ADA-4646) is the only IMU in the database and is kept despite unverified mass/current because no alternative exists. The three HRM-* assumed items are kept as they are the only chassis/structure/wiring options in the database. Total cost increases by ~131 SAR (POL-2507 at 150 SAR replaces POL-713 at 19 SAR), staying within the 1500 SAR budget. The balanced strategy selects POL-2507 as it provides 8x margin on continuous current at moderate cost, avoiding both the under-rated POL-713 and the overkill single-channel POL-2991.

## Engineering Calculations

| Quantity | Value | Unit | Provenance | Formula / inputs | Note |
|---|---|---|---|---|---|
| component_mass | 1.4401 | kg | CALCULATED | sum of BOM line masses = 1440.1 g | 1 item(s) without a verified mass |
| total_mass | 3.4401 | kg | CALCULATED | components 1.440 kg + payload 2.000 kg |  |
| bom_cost_sar | 1387.43 | SAR | CALCULATED | 369.98 USD x 3.75 SAR/USD (BOM) |  |
| n_drive_motors | 2.0 | - | CALCULATED | count of drive motors in BOM |  |
| supply_voltage | 11.1 | V | SOURCED | nominal voltage of OVO-3S-6000-80C |  |
| rolling_force | 0.6747 | N | CALCULATED | Crr*m*g = 0.02 x 3.440 x 9.807 |  |
| grade_force | 2.9403 | N | CALCULATED | m*g*sin(5.0 deg) = 3.440 x 9.807 x sin(5.0) |  |
| accel_force | 1.7201 | N | CALCULATED | m*a = 3.440 x 0.5 |  |
| torque_level | 0.0152 | N-m | CALCULATED | F_rr*r/n = 0.675 x 0.0450 / 2 |  |
| torque_continuous | 0.0813 | N-m | CALCULATED | (F_rr+F_grade)*r/n = (0.675+2.940) x 0.0450 / 2 |  |
| torque_peak | 0.12 | N-m | CALCULATED | (F_rr+F_grade+F_acc)*r/n = (0.675+2.940+1.720) x 0.0450 / 2 |  |
| torque_continuous_design | 0.122 | N-m | CALCULATED | T_cont x SF = 0.0813 x 1.5 |  |
| torque_peak_design | 0.1801 | N-m | CALCULATED | T_peak x SF = 0.1200 x 1.5 |  |
| motor_stall_torque_at_supply | 0.6713 | N-m | CALCULATED | Ts*V/Vr = 0.7257 x 11.1/12.0 |  |
| motor_stall_current_at_supply | 4.625 | A | CALCULATED | Is*V/Vr = 5.0 x 11.1/12.0 |  |
| required_wheel_rpm | 318.3099 | rpm | CALCULATED | v/(pi*d)*60 = 1.5/(pi x 0.09) x 60 |  |
| loaded_wheel_rpm | 452.0402 | rpm | CALCULATED | n0'*(1-T_level/Ts') at 11.1 V |  |
| achievable_speed | 2.1302 | m/s | CALCULATED | rpm*pi*d/60 = 452.0 x pi x 0.09/60 |  |
| motor_current_continuous | 0.8268 | A | CALCULATED | I0 + T_cont/Kt = 0.3 + 0.0813/0.1544 |  |
| motor_current_peak | 1.4662 | A | CALCULATED | I0 + T_peak_design/Kt = 0.3 + 0.1801/0.1544 |  |
| motor_thermal_current_limit | 1.1562 | A | CALCULATED | 25% of stall current at supply voltage (Pololu guidance) |  |
| motor_power_level | 2.2877 | W | CALCULATED | per motor, T=0.0152 N-m at 212 rpm (cruise 1.0 m/s) |  |
| motor_power_grade | 5.5987 | W | CALCULATED | per motor, T=0.0813 N-m at 212 rpm |  |
| mechanical_power_level | 0.6747 | W | CALCULATED | n x T_level x w_cruise |  |
| drive_power_avg | 5.5133 | W | CALCULATED | n x ((1-0.1) x P_level + 0.1 x P_grade) / eta_driver(0.95) |  |
| logic_power | 1.108 | W | CALCULATED | sum of device supply current x voltage (allowance for unverified devices) |  |
| electronics_power_battery | 1.3035 | W | CALCULATED | logic power / eta_regulator(0.85) |  |
| regulator_output_current | 0.2216 | A | CALCULATED | logic power / 5.0 V |  |
| system_power_avg | 6.8168 | W | CALCULATED | P_drive 5.51 + P_electronics 1.30 |  |
| battery_energy | 66.6 | Wh | CALCULATED | V x C = 11.1 x 6000.0 mAh |  |
| battery_usable_energy | 53.28 | Wh | CALCULATED | E x usable fraction = 66.60 x 0.8 |  |
| runtime | 7.816 | h | CALCULATED | E_usable / P_avg = 53.28 / 6.82 |  |
| capacity_needed_for_runtime | 1535.3161 | mAh | CALCULATED | t x P / (V x usable) = 2.0 x 6.82 / (11.1 x 0.8) |  |
| battery_peak_current | 3.0497 | A | CALCULATED | n x I_peak + P_elec/V = 2 x 1.466 + 1.30/11.1 |  |
| battery_max_current | 480.0 | A | CALCULATED | C-rating x capacity = 80.0 x 6.00 Ah |  |

## Verification Results

| Status | Kind | Check | Required | Actual | Margin | Detail |
|---|---|---|---|---|---|---|
| PASS | hard | known_components | all component ids exist in the database | all known |  |  |
| PASS | hard | completeness | drivetrain, power, control and structure present | complete |  |  |
| PASS | hard | feature_wheel_encoders | design includes drive motors with encoders | present |  |  |
| PASS | hard | feature_imu | design includes an IMU | present |  |  |
| PASS | hard | feature_range_sensor | design includes a range sensor | present |  |  |
| PASS | hard | drive_wheels | >= 2 wheels | 2 wheels | +0.0% | one wheel per drive motor |
| PASS | hard | hub_shaft_match | >= 2 hubs | 2 hubs | +0.0% | hubs must fit the 4 mm motor shaft |
| PASS | hard | bracket_match | >= 2 brackets | 2 brackets | +0.0% | brackets must fit 25D gearmotors |
| PASS | hard | driver_channels | >= 2 channels | 2 channels | +0.0% |  |
| PASS | hard | driver_voltage[POL-2507] | 5.5-24.0 V | 11.1 V battery |  |  |
| PASS | hard | driver_current[POL-2507] | >= 1.47 A | 12 A | +718.4% | driver continuous rating vs motor current at design peak torque |
| PASS | soft | driver_stall_rating[POL-2507] | >= 4.62 A | 12 A | +159.5% | Pololu recommends drivers rated above motor stall current |
| UNVERIFIED | soft | logic_level[POL-2507] | controller logic within driver logic range | Specification not verified. |  | driver logic-level range not stated in the source |
| PASS | soft | motor_voltage | <= 13.2 V | 11.1 V | +15.9% | battery nominal voltage vs motor rated voltage (+10%) |
| PASS | hard | logic_supply | regulator required (battery 11.1 V > 3.3 V) | regulator present |  |  |
| PASS | hard | regulator_input[POL-2858] | 5.3-36.0 V | 11.1 V battery |  |  |
| PASS | hard | regulator_current[POL-2858] | <= 2.2 A | 0.222 A | +89.9% |  |
| PASS | hard | speed | >= 1.5 m/s | 2.13 m/s | +42.0% | full-throttle speed on level ground with payload |
| PASS | hard | torque_continuous | <= 0.392 N-m | 0.122 N-m | +68.9% | climb torque x safety factor vs manufacturer continuous-load limit |
| PASS | hard | torque_peak | <= 0.671 N-m | 0.18 N-m | +73.2% | accelerating up the design grade x safety factor vs instantaneous limit / stall torque |
| PASS | soft | motor_thermal | <= 1.16 A | 0.827 A | +28.5% | continuous current vs 25% of stall current |
| PASS | hard | runtime | >= 2 h | 7.82 h | +290.8% |  |
| PASS | hard | battery_current | <= 480 A | 3.05 A | +99.4% |  |
| PASS | hard | mass | <= 8 kg | 3.44 kg | +57.0% | includes payload |
| PASS | hard | budget | <= 1,500 SAR | 1,387 SAR | +7.5% |  |
| UNVERIFIED | soft | evidence_coverage | all specs verified | 2 unverified |  | mass of ADA-4646; supply current of ADA-4646 (allowance 0.25 W used) |
| WARN | soft | assumed_items | sourced parts | HRM-CHASSIS-PLY6, HRM-PAYLOAD-BIN, HRM-WIRING-KIT |  | mass/cost of these items are engineering allowances |

## Iteration History

| Design | Strategy | Verification | Score | Cost (SAR) | Runtime (h) | Failed hard checks | Changes / rationale |
|---|---|---|---|---|---|---|---|
| #1 | economy | FAIL | -0.315 | 1,256 | 7.8282 | driver_current[POL-713] | First design — no previous. |
| #2 | balanced | PASS | 0.0 | 1,387 | 7.816 | - | Replaced POL-713 (dual motor driver, 1 A cont/ch) with POL-2507 (Dual VNH5019, 12 A cont/ch, 150 SAR, 18 g) to fix the driver_current failure (required >= 1.46  |

## Critic Findings

**Design #2 - verdict PASS:** The design passes verification but has two fixable issues: (1) the IMU ADA-4646 has unverified mass and supply current, and (2) the rear ball caster POL-2691 has no stated load rating — for a 3.44 kg robot with 2 kg payload (5.44 kg total on 3 contact points), the caster must support ~1.8 kg. A replacement caster with a known load rating exists in the database.

## Final Design

The final design satisfies the specified computational constraints.

## Bill of Materials

| Component | Manufacturer | Part number | Qty | Packs | Unit price (USD) | Total (SAR) | Weight (g) | Key specification | Data |
|---|---|---|---|---|---|---|---|---|---|
| 20.4:1 Metal Gearmotor 25Dx65L mm HP 12V with 48 CPR Encoder | Pololu | 4843 | 2 |  | 56.95 | 427.12 | 196.0 | 20.4:1, 500 rpm no-load, stall 7.4 kg-cm / 5.0 A @ 12 V, encoder | sourced |
| Wheel 90x10mm Pair - Black | Pololu | 1435 | 2 | 1 | 9.49 | 35.59 | 45.4 | 90 mm diameter, 3.0 mm bore | sourced |
| Universal Aluminum Mounting Hub for 4mm Shaft, #4-40 Holes (2-Pack) | Pololu | 1081 | 2 | 1 | 10.95 | 41.06 | 6.4 | for 4 mm shaft | sourced |
| 25D mm Metal Gearmotor Bracket Pair | Pololu | 2676 | 2 | 1 | 10.95 | 41.06 | 17.0 | for 25D gearmotors | sourced |
| Ball Caster with 1in Plastic Ball and Plastic Rollers | Pololu | 2691 | 1 |  | 5.95 | 22.31 | 16.5 | sourced | sourced |
| Dual VNH5019 Motor Driver Shield for Arduino | Pololu | 2507 | 1 |  | 39.95 | 149.81 | 18.0 | 2 ch, 12.0 A cont/ch, 5.5-24.0 V | sourced |
| OVONIC 3S 6000mAh 80C 11.1V LiPo Battery (Deans T) | Ovonic | 3S-6000-80C | 1 |  | 34.99 | 131.21 | 362.0 | LiPo 11.1 V 6000 mAh (66.6 Wh), 80C | sourced |
| ESP32 Feather V2 - 8MB Flash + 2 MB PSRAM | Adafruit | 5400 | 1 |  | 19.95 | 74.81 | 6.0 | 240 mA @ 3.3 V | sourced |
| Custom plywood base plate 300x250x6 mm | Local fabrication | N/A | 1 |  | 12.00 | 45.00 | 270.0 | assumed | assumed |
| Payload bin / enclosure (2 kg class) | Local fabrication | N/A | 1 |  | 20.00 | 75.00 | 350.0 | assumed | assumed |
| Wiring, connectors, fuse, switch and fasteners allowance | Various | N/A | 1 |  | 20.00 | 75.00 | 150.0 | assumed | assumed |
| 9-DOF Absolute Orientation IMU Fusion Breakout - BNO055 (STEMMA QT) | Adafruit | 4646 | 1 |  | 29.95 | 112.31 | not verified | partial | partial |
| VL53L1X Time-of-Flight Distance Sensor Carrier, 400 cm max | Pololu | 3415 | 1 |  | 22.95 | 86.06 | 0.5 | 20 mA @ 3.3 V | sourced |
| 5V 2.5A Step-Down Voltage Regulator D24V22F5 | Pololu | 2858 | 1 |  | 18.95 | 71.06 | 2.3 | 5.0 V out, 2.2 A, 5.3-36.0 V in | sourced |
| **TOTAL** |  |  |  |  |  | **1,387.43** | **1440.1** |  |  |

Prices: single-unit list prices (USD) converted at the fixed 3.75 SAR/USD peg; shipping, customs and VAT excluded.

## Sources / Evidence

**Component specifications (structured database):**
- POL-4843: https://www.pololu.com/product/4843/specs (retrieved 2026-10-07)
- POL-1435: https://www.pololu.com/product/1435/specs (retrieved 2026-10-07)
- POL-1081: https://www.pololu.com/product/1081/specs (retrieved 2026-10-07)
- POL-2676: https://www.pololu.com/product/2676/specs (retrieved 2026-10-07)
- POL-2691: https://www.pololu.com/product/2691/specs (retrieved 2026-10-07)
- POL-2507: https://www.pololu.com/product/2507/specs (retrieved 2026-10-07)
- OVO-3S-6000-80C: https://us.ovonicshop.com/products/ovonic-3s-lipo-battery-6000mah-3s1p-80c-11-1v-rc-lipo-battery-with-deans-t-plug-for-rc-1-8-1-10-scale-vehicles-car-trucks-boats (retrieved 2026-10-07)
- ADA-5400: https://www.adafruit.com/product/5400 (retrieved 2026-10-07)
- HRM-CHASSIS-PLY6: ASSUMED (no external source)
- HRM-PAYLOAD-BIN: ASSUMED (no external source)
- HRM-WIRING-KIT: ASSUMED (no external source)
- ADA-4646: https://www.adafruit.com/product/4646 (retrieved 2026-10-07)
- POL-3415: https://www.pololu.com/product/3415/specs (retrieved 2026-10-07)
- POL-2858: https://www.pololu.com/product/2858/specs (retrieved 2026-10-07)

**Datasheet evidence retrieved by the research agents (RAG):**
- [battery] [Ovonic 3S 6000 mAh 80C 11.1 V LiPo (Deans T plug)] Source: https://us.ovonicshop.com/products/ovonic-3s-lipo-battery-6000mah-3s1p-80c-11-1v-rc-lipo-battery-with-deans-t-plug-for-rc-1-8-1-10-scale-vehicles-car-trucks-boats. Li-polymer, 6000 mAh, 11.1 V (3S). Continuous discharge rate 80C, maximum burst discharge rate 160C. Charge plug JST-XHR-4P, discharge plug Deans T, soft case. Net weight 362 g (+/-20 g). Size 134 x 42 x 29 mm (+/-5 mm). Price 3 - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://us.ovonicshop.com/products/ovonic-3s-lipo-battery-6000mah-3s1p-80c-11-1v-rc-lipo-battery-with-deans-t-plug-for-rc-1-8-1-10-scale-vehicles-car-trucks-boats>
- [battery] [Ovonic 3S 11.1 V 1400 mAh 50C LiPo (XT60 and Trx plug)] Source: https://us.ovonicshop.com/products/ovonic-11-1v-1400mah-3s-50c-lipo-battery-with-xt60-trx-plug. Net weight 116 g (deviation 20 g). Price 21.99 USD. Dimensions are not stated in the parsed listing. Nameplate energy 11.1 V x 1.4 Ah = 15.5 Wh. - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://us.ovonicshop.com/products/ovonic-11-1v-1400mah-3s-50c-lipo-battery-with-xt60-trx-plug>
- [battery] [Pololu Rechargeable NiMH Battery Pack: 8.4 V, 2200 mAh, 4+3 AA cells (item 2226)] Source: https://www.pololu.com/product/2226/specs. Size 58 x 27 x 51 mm. Weight 6.9 oz (195.6 g). 7 AA NiMH cells. Connector JR 3-pin female. Price 33.07 USD. Maximum discharge current is not stated. Nameplate energy 18.5 Wh. - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://www.pololu.com/product/2226/specs>
- [battery] [Ovonic charging and handling notes] Ovonic listings state: use Ovonic official RC LiPo battery chargers for optimal charging performance; ensure compatibility with both voltage and plug specifications; cease charging immediately upon reaching 4.2 V per cell (normal voltage range 3.7 V to 4.2 V per cell); inspect battery condition before each use. - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://us.ovonicshop.com/>
- [battery] [Voltage compatibility note] A 3S LiPo pack is 11.1 V nominal and 12.6 V at 4.2 V per cell, close to the 12 V rating of the 12 V gearmotors. The NiMH packs (7.2 V and 8.4 V) run 12 V gearmotors at reduced speed, because brushed-motor no-load speed scales approximately with supply voltage. - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://us.ovonicshop.com/>
- [battery] [Ovonic 7200 mAh 3S 11.1 V 80C LiPo hardcase (Deans plug)] Source: https://us.ovonicshop.com/products/ovonic-80c-11-1v-7200mah-3s1p-hardcase-t-lipo-battery. Net weight 458 g (deviation 20 g). Hardcase. Price 71.99 USD. Nameplate energy 79.9 Wh. - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://us.ovonicshop.com/products/ovonic-80c-11-1v-7200mah-3s1p-hardcase-t-lipo-battery>
- [electronics] [Adafruit ESP32 Feather V2 - 8MB Flash + 2 MB PSRAM (Adafruit product 5400)] Source: https://www.adafruit.com/product/5400. Product dimensions 52.3 x 22.8 x 7.2 mm. Product weight 6.0 g. Price 19.95 USD. 240 MHz dual-core Tensilica LX6 microcontroller, 520 KB SRAM, integrated 802.11b/g/n Wi-Fi and dual-mode Bluetooth. As of June 30, 2022 the board may come with a different regulator than the AP2112K due to parts shortages; the regulator can provide at least 500 mA. The ESP - *controllers_esp32_pico_w_bno055.md*, page web <https://www.adafruit.com/product/5400>
- [electronics] [Raspberry Pi Pico W (Adafruit product 5526)] Sources: https://www.adafruit.com/product/5526 and https://datasheets.raspberrypi.com/picow/pico-w-datasheet.pdf. Price 6.00 USD. Dimensions (unassembled) 51 x 21 x 1 mm. RP2040 (dual-core Cortex M0) with 2 MB QSPI flash and on-board wireless. VSYS is the main system input voltage, allowed range 1.8 V to 5.5 V, used by the on-board SMPS to generate 3.3 V. VBUS is 5 V +/-10%. The datasheet states t - *controllers_esp32_pico_w_bno055.md*, page 13 <https://www.adafruit.com/product/5526>
- [electronics] [TB6612FNG Dual Motor Driver Carrier (item 713)] Source: https://www.pololu.com/product/713/specs

- Motor channels: 2. Size 0.60 x 0.80 inch, weight 1.5 g.
- Operating voltage: 4.5 V minimum (can operate down to 2.5 V with reduced current capabilities), 13.5 V maximum.
- Continuous output current per channel: 1 A. Peak output current per channel: 3 A. Continuous paralleled output current: 2 A.
- Maximum PWM frequency: 100 kHz. Logic voltage 2.7 - *pololu_motor_drivers.md*, page web <https://www.pololu.com/product/713/specs>
- [electronics] [Adafruit 9-DOF Absolute Orientation IMU Fusion Breakout - BNO055, STEMMA QT (Adafruit product 4646)] Source: https://www.adafruit.com/product/4646. Price 29.95 USD. The Bosch BNO055 combines a MEMS accelerometer, magnetometer and gyroscope on a single die with an ARM Cortex-M0 based processor that performs sensor fusion and outputs quaternions, Euler angles or vectors. Uses I2C address 0x28 (default) or 0x29. The product page does not state weight or supply current; these specifications are not v - *controllers_esp32_pico_w_bno055.md*, page web <https://www.adafruit.com/product/4646>
- [electronics] [VL53L1X Time-of-Flight Distance Sensor Carrier with Voltage Regulator, 400 cm max (item 3415)] Source: https://www.pololu.com/product/3415/specs

- Size 0.5 x 0.7 x 0.085 inch; weight 0.5 g without optional headers.
- Resolution 1 mm. Maximum range 400 cm; effective range depends on configuration, target, and environment. Minimum range 4 cm; the sensor still detects closer targets but the measurement will not be accurate.
- Interface: I2C. Operating voltage 2.6 V to 5.5 V.
- Supply current: - *pololu_regulator_and_tof_sensor.md*, page web <https://www.pololu.com/product/3415/specs>
- [electronics] [5V, 2.5A Step-Down Voltage Regulator D24V22F5 (item 2858)] Source: https://www.pololu.com/product/2858/specs

- Size 0.7 x 0.7 x 0.31 inch; weight 2.3 g without optional headers.
- Input voltage: 5.3 V minimum (for small loads; this voltage rises approximately linearly up to around 5.8 V at 2.5 A output), 36 V maximum.
- Output voltage: 5 V. Continuous output current: 2.2 A typical maximum at 24 V input. Actual achievable continuous output current is a fu - *pololu_regulator_and_tof_sensor.md*, page web <https://www.pololu.com/product/2858/specs>
- [electronics] [Default mission-profile assumptions] - Cruise speed 1.0 m/s for the energy estimate (the top-speed requirement is checked separately).
- Design grade 5 degrees (ramps and kerb cuts); 10% of drive time spent climbing it.
- Peak acceleration 0.5 m/s2.
- Rolling resistance coefficient 0.02 for small hard wheels on paved or indoor surfaces. Rough outdoor surfaces can be several times higher.
- Torque safety factor 1.5 applied to continuo - *hermes_assumption_register.md*, page N/A <N/A (internal assumption register, not an external source)>
- [mechanical] [Wheel 90x10mm Pair - Black (item 1435)] Source: https://www.pololu.com/product/1435/specs. Size 90 x 10 mm. Weight 0.8 oz per wheel including tire (22.7 g). Shaft (bore) diameter 3 mm, D-shaped hole for press fit onto Pololu micro metal gearmotors and mini plastic gearmotors. Price 9.49 USD per pair. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/1435/specs>
- [mechanical] [Wheel 80x10mm Pair - Black (item 1430)] Source: https://www.pololu.com/product/1430/specs. Size 80 x 10 mm. Weight 0.7 oz per wheel including tire (19.8 g). Bore 3 mm. Price 8.75 USD per pair.

Neither wheel specs page states a load rating. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/1430/specs>
- [mechanical] [Assumed structural items] - HRM-CHASSIS-AL3: custom aluminium base plate 300 x 250 x 3 mm. Mass 607.5 g is calculated from the assumed dimensions and the density of aluminium (2.70 g/cm3). Price 40 USD is an assumed fabrication estimate, not a quote.
- HRM-CHASSIS-PLY6: custom plywood base plate 300 x 250 x 6 mm. Mass 270 g is calculated with an assumed plywood density of 0.60 g/cm3. Price 12 USD is assumed.
- HRM-PAYLOAD- - *hermes_assumption_register.md*, page N/A <N/A (internal assumption register, not an external source)>
- [mechanical] [Ball Caster with 1 inch Plastic Ball and Plastic Rollers (item 2691)] Source: https://www.pololu.com/product/2691/specs. Ball diameter 1 inch, plastic ball. Weight 16.5 g. Price 5.95 USD. No load rating is stated. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/2691/specs>
- [mechanical] [Ball Caster with 1 inch Plastic Ball and Ball Bearings (item 2692)] Source: https://www.pololu.com/product/2692/specs. Ball diameter 1 inch, plastic ball, ball-bearing rollers. Weight 18.5 g. Price 9.95 USD. No load rating is stated. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/2692/specs>
- [mechanical] [Universal Aluminum Mounting Hub for 4mm Shaft, #4-40 Holes, 2-Pack (item 1081)] Source: https://www.pololu.com/product/1081/specs. 19 mm diameter x 5 mm thick. Weight 3.2 g for a single hub without set screw. Shaft diameter 4 mm. Price 10.95 USD per 2-pack. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/1081/specs>
- [mechanical] [Universal Aluminum Mounting Hub for 6mm Shaft, #4-40 Holes, 2-Pack (item 1083)] Source: https://www.pololu.com/product/1083/specs. 25.4 mm diameter x 9.2 mm thick. Weight 6.8 g for a single hub without set screws. Shaft diameter 6 mm. Mounting hole size #4-40 (also the size of the set screws). Price 12.95 USD per 2-pack. The 37D gearmotor page lists this hub for attaching Pololu 80 mm and 90 mm wheels to the 6 mm output shaft. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/1083/specs>
- [motor] [Load limits and thermal guidance] The listed stall torques and currents are theoretical extrapolations; units will typically stall well before these points as the motors heat up. Stalling or overloading gearmotors can greatly decrease their lifetimes and even result in immediate damage. The recommended upper limit for continuously applied loads is 10 kg-cm (150 oz-in), and the recommended upper limit for instantaneous torque is 25 - *pololu_37d_metal_gearmotors.md*, page web <https://www.pololu.com/product/4752>
- [motor] [Load limits and thermal guidance] The listed stall torques and currents are theoretical extrapolations; units will typically stall well before these points as the motors heat up. Stalling or overloading gearmotors can greatly decrease their lifetimes and even result in immediate damage. The recommended upper limit for continuously applied loads is 4 kg-cm (55 oz-in), and the recommended upper limit for intermittently permissible t - *pololu_25d_hp_metal_gearmotors.md*, page web <https://www.pololu.com/product/4843>
- [motor] [Motor driver recommendation] Pololu's high-power motor drivers and Motoron controllers are available in various power levels, several of which can handle the 37D mm metal gearmotors. Pololu generally recommends a motor controller that can handle continuous currents above the stall current of your motor. - *pololu_37d_metal_gearmotors.md*, page web <https://www.pololu.com/product/4752>
- [motor] [Family overview] Measuring 37 mm in diameter, these brushed DC gearmotors are the largest and most powerful Pololu carries. They are available in gear ratios from 6.3:1 to 150:1 and with 12 V or 24 V motors, and all versions are available with integrated 64 CPR quadrature encoders on the motor shafts. The 12 V and 24 V motors offer approximately the same performance at their respective nominal voltages, with the 2 - *pololu_37d_metal_gearmotors.md*, page web <https://www.pololu.com/product/4752>
- [motor] [Mounting] The 25D gearmotors have a 4 mm D-shaped output shaft. HERMES inference (from the related-products listing on the Pololu wheel pages, not an explicit statement): the Pololu universal aluminum mounting hub for 4 mm shafts can attach the 3 mm-bore 80 mm and 90 mm wheels. The Pololu 25D mm metal gearmotor bracket pair mounts these motors (two M3 screws per bracket included). - *pololu_25d_hp_metal_gearmotors.md*, page web <https://www.pololu.com/product/4843>
- [motor] [Specifications per item (specs pages)] - 3203 (20.4:1, no encoder): 25D x 50L mm, 85 g, 4 mm D shaft. Max efficiency 46% at 420 rpm, 1.1 kg-cm, 0.88 A, 4.8 W output (12 V). At 6 V: 250 rpm no-load, 2.5 A stall, 3.7 kg-cm stall. Price 32.95 USD.
- 3204 (34:1, no encoder): 25D x 52L mm, 88 g, 4 mm D shaft. Max efficiency 44% at 260 rpm, 1.6 kg-cm, 0.82 A, 4.3 W output (12 V). Price 32.95 USD.
- 4843 (20.4:1, 48 CPR encoder): 25D x 65L mm - *pololu_25d_hp_metal_gearmotors.md*, page web <https://www.pololu.com/product/4843>
- [motor] [Performance table at 12 V (HP 12V comparison table)] HP 12 V motors: stall current 5.0 A; no-load current 250 mA without encoder, 300 mA with encoder.

| Gear ratio | No-load speed | Stall torque | Max power | Without encoder | With encoder |
|---|---|---|---|---|---|
| 20.4:1 | 500 rpm | 7.4 kg-cm | 9.4 W | item 3203 | item 4843 |
| 34:1 (34.014:1) | 300 rpm | 11 kg-cm | 8.9 W | item 3204 | item 4844 | - *pololu_25d_hp_metal_gearmotors.md*, page web <https://www.pololu.com/product/4843>
- [electronics] [Dual VNH5019 Motor Driver Shield for Arduino (item 2507)] Source: https://www.pololu.com/product/2507/specs

- Motor channels: 2. Size 2.56 x 2.02 x 0.38 inch, weight 18 g without included hardware.
- Operating voltage: 5.5 V minimum, 24 V maximum; not recommended for use with 24 V batteries.
- Continuous output current per channel: 12 A. Peak output current per channel: 30 A.
- Current sense: 0.14 V/A. Maximum PWM frequency: 20 kHz.
- Reverse voltage pr - *pololu_motor_drivers.md*, page web <https://www.pololu.com/product/2507/specs>
- [electronics] [Selection guidance] Pololu generally recommends a motor controller that can handle continuous currents above the stall current of the motor (stated on the 37D and 25D gearmotor pages). The 12 V 37D gearmotors stall at 5.5 A and the HP 12 V 25D gearmotors at 5.0 A (extrapolated), so a 1 A-per-channel driver such as the TB6612FNG is below that recommendation, while the VNH5019 (12 A) and G2 18v17 (17 A) exceed it. - *pololu_motor_drivers.md*, page web <https://www.pololu.com/product/713/specs>
- [mechanical] [Stamped Aluminum L-Bracket Pair for 37D mm Metal Gearmotors (item 1084)] Source: https://www.pololu.com/product/1084/specs. Weight 11 g for a single bracket (no screws or nuts). Each bracket includes six M3 screws for securing the motor and features fourteen mounting holes. Price 11.95 USD per pair. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/1084/specs>

## Limitations

- Specifications are taken from vendor pages and datasheets on the retrieval date; prices and availability change.
- Motor performance uses a linear brushed-DC model built from extrapolated stall values; real motors stall earlier when hot.
- Energy use depends on the assumed mission profile (cruise speed, grade, rolling resistance); see Assumptions.
- Wheel and caster load ratings are not stated by the manufacturer and were not verified.
- logic_level[POL-2507]: Specification not verified. (driver logic-level range not stated in the source)
- evidence_coverage: 2 unverified (mass of ADA-4646; supply current of ADA-4646 (allowance 0.25 W used))
- assumed_items: HRM-CHASSIS-PLY6, HRM-PAYLOAD-BIN, HRM-WIRING-KIT (mass/cost of these items are engineering allowances)

## Recommended Physical Validation

1. Bench-test each gearmotor at the design operating point and log current and case temperature for 30 minutes.
2. Measure the actual rolling resistance on the target floor/pavement and re-run the energy calculation.
3. Drain-test the battery on the assembled robot carrying the payload; confirm runtime against the 2 h target with margin.
4. Climb the design grade with full payload and measure the peak motor current against the driver rating.
5. Load-test wheels, hubs and the caster at 1.5x the static wheel load.
6. Verify logic-level and connector compatibility between the controller, motor driver and sensors.
7. Have a qualified engineer review battery protection (fusing, BMS/low-voltage cutoff) and wiring gauge.

---

**AI-generated engineering proposal - not a certified engineering design.**

Physical validation and qualified engineering review are required before real-world deployment.