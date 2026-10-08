# HERMES Engineering Report - Indoor Robot Cart - 1 kg payload, 4 h runtime, obstacle detection

**AI-generated engineering proposal - not a certified engineering design.**

**Final status: VERIFIED.** The final design satisfies the specified computational constraints.

## Executive Summary

**Executive Summary – Final Engineering Proposal**

The proposed robot design passes all verification criteria after **two iterations**. The first iteration failed due to an incompatible wheel-to-motor hub shaft match and insufficient battery runtime (1.96 hours). The second iteration corrected these issues by replacing the motor driver (POL-713 with POL-2507), mounting hubs (POL-1083 with POL-1081), battery (OVO-3S-1400-50C with OVO-3S-6000-80C), and controller (ADA-5526 with ADA-5400), achieving a runtime of **7.51 hours**.

Total estimated BOM cost is **1,107 SAR** with a system mass of **2.42 kg** (excluding the 1 kg payload). The design reaches a calculated top speed of **1.15 m/s** and delivers **7.1 W** average system power from a 66.6 Wh LiPo battery. Three items (chassis, payload bin, wiring kit) are engineering allowances with assumed mass and cost.

One specification remains unverified: the controller logic-level voltage range for the VNH5019 driver was not explicitly confirmed against the datasheet.

**Physical validation and qualified engineering review are required before real-world deployment.**

## Requirements

| Requirement | Value | Type |
|---|---|---|
| Payload | 1.0 kg | explicit |
| Runtime | >= 4.0 h | explicit |
| Top speed | >= 0.8 m/s | explicit |
| Total mass | <= 5.0 kg (incl. payload) | explicit (payload interpretation: see assumptions) |
| Budget | <= 1,200 SAR | explicit |
| Feature | range_sensor | derived |

## Assumptions

| ID | Assumption | Value | Rationale / origin |
|---|---|---|---|
| A1 | The stated 0.8 m/s is the maximum top speed the robot must reach on level ground. | 0.8 m/s |  |
| A2 | The 5 kg limit is the total system mass including the robot, battery, electronics and the 1 kg payload; no separate allowance exists. | 5 kg total including payload |  |
| A3 | The 1200 SAR limit applies to the BOM cost of the robot components. |  |  |
| A4 | Only obstacle detection was requested; autonomous navigation/obstacle avoidance logic was not implied and is not required. |  |  |
| P1 | Profile override: design_grade_deg = 1.0 | 1.0 | Request says the robot runs on 'flat office floors', implying level indoor surfaces. |
| P-cruise_speed_mps | Average driving speed used for the energy estimate, m/s. | 1.0 | mission profile (ASSUMED) |
| P-design_grade_deg | Steepest ramp the robot must climb, degrees. | 1.0 | mission profile (ASSUMED) |
| P-fraction_time_on_grade | Fraction of drive time spent climbing the design grade. | 0.1 | mission profile (ASSUMED) |
| P-acceleration_mps2 | Peak acceleration requirement, m/s^2. | 0.5 | mission profile (ASSUMED) |
| P-rolling_resistance_coeff | Rolling resistance coefficient of small hard wheels. | 0.02 | mission profile (ASSUMED) |
| P-torque_safety_factor | Safety factor applied to torque requirements. | 1.5 | mission profile (ASSUMED) |
| P-battery_usable_fraction | Fraction of nameplate battery energy that is usable. | 0.8 | mission profile (ASSUMED) |
| P-regulator_efficiency | Efficiency of the logic step-down regulator. | 0.85 | mission profile (ASSUMED) |
| P-driver_efficiency | Motor driver efficiency. | 0.95 | mission profile (ASSUMED) |
| P-unverified_device_power_w | Power allowance for an electronic device whose supply current is not verified, W. | 0.25 | mission profile (ASSUMED) |

### Derived requirements

- The request states the cart 'needs obstacle detection' -> the robot must carry at least one range sensor (e.g. ultrasonic or ToF) with a forward detection cone covering its path at 0.8 m/s.
- No autonomous navigation/delivery/localisation was requested -> wheel encoders and IMU are NOT required (they would only add cost); the cart may be teleoperated or stop on obstacle detection.
- Carrying 1 kg at 0.8 m/s on flat office floors -> the drivetrain must provide enough continuous torque and wheel speed for that load, with the total system mass under 5 kg and BOM under 1200 SAR.

### Open questions for a human engineer

- Is the cart required to navigate autonomously around obstacles (adding wheel encoders + IMU and cost), or only to detect obstacles and stop/warn?
- Is 0.8 m/s the top speed or the typical cruise speed?
- Is the 1200 SAR budget for BOM only, or must it cover assembly labour and tools?
- Which floor conditions must be handled beyond flat smooth office floors (carpet, door thresholds, ramps)?
- Any preference on wheel size, footprint, or ground clearance?

## Selected Architecture - Final design #2

Differential-drive platform: two direct-drive gearmotors with wheels on universal hubs, a ball caster, one battery pack feeding the motor driver directly and the controller through a step-down regulator.

- **motor**: 2 x 34:1 Metal Gearmotor 25Dx52L mm HP 12V (POL-3204)
- **motor_driver**: 1 x Dual VNH5019 Motor Driver Shield for Arduino (POL-2507)
- **battery**: 1 x OVONIC 3S 6000mAh 80C 11.1V LiPo Battery (Deans T) (OVO-3S-6000-80C)
- **regulator**: 1 x 5V 2.5A Step-Down Voltage Regulator D24V22F5 (POL-2858)
- **controller**: 1 x ESP32 Feather V2 - 8MB Flash + 2 MB PSRAM (ADA-5400)
- **range_sensor**: 1 x VL53L1X Time-of-Flight Distance Sensor Carrier, 400 cm max (POL-3415)
- **wheel**: 2 x Wheel 80x10mm Pair - Black (POL-1430)
- **hub**: 2 x Universal Aluminum Mounting Hub for 4mm Shaft, #4-40 Holes (2-Pack) (POL-1081)
- **bracket**: 2 x 25D mm Metal Gearmotor Bracket Pair (POL-2676)
- **caster**: 1 x Ball Caster with 1in Plastic Ball and Ball Bearings (POL-2692)
- **chassis**: 1 x Custom plywood base plate 300x250x6 mm (HRM-CHASSIS-PLY6)
- **structure**: 1 x Payload bin / enclosure (2 kg class) (HRM-PAYLOAD-BIN)
- **wiring**: 1 x Wiring, connectors, fuse, switch and fasteners allowance (HRM-WIRING-KIT)

## Component Selection

Economy strategy: each part is the cheapest candidate that meets its role. POL-3204 motors (124 SAR each) provide 1.41 m/s wheel speed exceeding 0.8 m/s, with 4.0 kg-cm continuous torque margin. POL-1081 hubs (4mm bore) mate the motor shafts to the POL-1430 wheels. POL-2507 dual driver (150 SAR) handles 12A continuous per channel, well above the 5A motor stall. OVO-3S-6000-80C battery (66.6 Wh, 131 SAR) provides 4+ h runtime at 80% depth-of-discharge. ADA-5400 ESP32 controller (75 SAR) has sourced mass/current data resolving the evidence_coverage failure. Total estimated cost ~1107 SAR under the 1200 SAR budget, mass ~1.38 kg (excl. payload) well under 5 kg.

## Engineering Calculations

| Quantity | Value | Unit | Provenance | Formula / inputs | Note |
|---|---|---|---|---|---|
| component_mass | 1.4164 | kg | CALCULATED | sum of BOM line masses = 1416.4 g |  |
| total_mass | 2.4164 | kg | CALCULATED | components 1.416 kg + payload 1.000 kg |  |
| bom_cost_sar | 1107.34 | SAR | CALCULATED | 295.29 USD x 3.75 SAR/USD (BOM) |  |
| n_drive_motors | 2.0 | - | CALCULATED | count of drive motors in BOM |  |
| supply_voltage | 11.1 | V | SOURCED | nominal voltage of OVO-3S-6000-80C |  |
| rolling_force | 0.4739 | N | CALCULATED | Crr*m*g = 0.02 x 2.416 x 9.807 |  |
| grade_force | 0.4136 | N | CALCULATED | m*g*sin(1.0 deg) = 2.416 x 9.807 x sin(1.0) |  |
| accel_force | 1.2082 | N | CALCULATED | m*a = 2.416 x 0.5 |  |
| torque_level | 0.0095 | N-m | CALCULATED | F_rr*r/n = 0.474 x 0.0400 / 2 |  |
| torque_continuous | 0.0178 | N-m | CALCULATED | (F_rr+F_grade)*r/n = (0.474+0.414) x 0.0400 / 2 |  |
| torque_peak | 0.0419 | N-m | CALCULATED | (F_rr+F_grade+F_acc)*r/n = (0.474+0.414+1.208) x 0.0400 / 2 |  |
| torque_continuous_design | 0.0266 | N-m | CALCULATED | T_cont x SF = 0.0178 x 1.5 |  |
| torque_peak_design | 0.0629 | N-m | CALCULATED | T_peak x SF = 0.0419 x 1.5 |  |
| motor_stall_torque_at_supply | 0.9978 | N-m | CALCULATED | Ts*V/Vr = 1.0787 x 11.1/12.0 |  |
| motor_stall_current_at_supply | 4.625 | A | CALCULATED | Is*V/Vr = 5.0 x 11.1/12.0 |  |
| required_wheel_rpm | 190.9859 | rpm | CALCULATED | v/(pi*d)*60 = 0.8/(pi x 0.08) x 60 |  |
| loaded_wheel_rpm | 274.8639 | rpm | CALCULATED | n0'*(1-T_level/Ts') at 11.1 V |  |
| achievable_speed | 1.1513 | m/s | CALCULATED | rpm*pi*d/60 = 274.9 x pi x 0.08/60 |  |
| motor_current_continuous | 0.3282 | A | CALCULATED | I0 + T_cont/Kt = 0.25 + 0.0178/0.2271 |  |
| motor_current_peak | 0.5268 | A | CALCULATED | I0 + T_peak_design/Kt = 0.25 + 0.0629/0.2271 |  |
| motor_thermal_current_limit | 1.1562 | A | CALCULATED | 25% of stall current at supply voltage (Pololu guidance) |  |
| motor_power_level | 2.8509 | W | CALCULATED | per motor, T=0.0095 N-m at 239 rpm (cruise 1.0 m/s) |  |
| motor_power_grade | 3.2355 | W | CALCULATED | per motor, T=0.0178 N-m at 239 rpm |  |
| mechanical_power_level | 0.4739 | W | CALCULATED | n x T_level x w_cruise |  |
| drive_power_avg | 6.0828 | W | CALCULATED | n x ((1-0.1) x P_level + 0.1 x P_grade) / eta_driver(0.95) |  |
| logic_power | 0.858 | W | CALCULATED | sum of device supply current x voltage (allowance for unverified devices) |  |
| electronics_power_battery | 1.0094 | W | CALCULATED | logic power / eta_regulator(0.85) |  |
| regulator_output_current | 0.1716 | A | CALCULATED | logic power / 5.0 V |  |
| system_power_avg | 7.0922 | W | CALCULATED | P_drive 6.08 + P_electronics 1.01 |  |
| battery_energy | 66.6 | Wh | CALCULATED | V x C = 11.1 x 6000.0 mAh |  |
| battery_usable_energy | 53.28 | Wh | CALCULATED | E x usable fraction = 66.60 x 0.8 |  |
| runtime | 7.5125 | h | CALCULATED | E_usable / P_avg = 53.28 / 7.09 |  |
| capacity_needed_for_runtime | 3194.6824 | mAh | CALCULATED | t x P / (V x usable) = 4.0 x 7.09 / (11.1 x 0.8) |  |
| battery_peak_current | 1.1446 | A | CALCULATED | n x I_peak + P_elec/V = 2 x 0.527 + 1.01/11.1 |  |
| battery_max_current | 480.0 | A | CALCULATED | C-rating x capacity = 80.0 x 6.00 Ah |  |

## Verification Results

| Status | Kind | Check | Required | Actual | Margin | Detail |
|---|---|---|---|---|---|---|
| PASS | hard | known_components | all component ids exist in the database | all known |  |  |
| PASS | hard | completeness | drivetrain, power, control and structure present | complete |  |  |
| PASS | hard | feature_range_sensor | design includes a range sensor | present |  |  |
| PASS | hard | drive_wheels | >= 2 wheels | 2 wheels | +0.0% | one wheel per drive motor |
| PASS | hard | hub_shaft_match | >= 2 hubs | 2 hubs | +0.0% | hubs must fit the 4 mm motor shaft |
| PASS | hard | bracket_match | >= 2 brackets | 2 brackets | +0.0% | brackets must fit 25D gearmotors |
| PASS | hard | driver_channels | >= 2 channels | 2 channels | +0.0% |  |
| PASS | hard | driver_voltage[POL-2507] | 5.5-24.0 V | 11.1 V battery |  |  |
| PASS | hard | driver_current[POL-2507] | >= 0.527 A | 12 A | +2177.9% | driver continuous rating vs motor current at design peak torque |
| PASS | soft | driver_stall_rating[POL-2507] | >= 4.62 A | 12 A | +159.5% | Pololu recommends drivers rated above motor stall current |
| UNVERIFIED | soft | logic_level[POL-2507] | controller logic within driver logic range | Specification not verified. |  | driver logic-level range not stated in the source |
| PASS | soft | motor_voltage | <= 13.2 V | 11.1 V | +15.9% | battery nominal voltage vs motor rated voltage (+10%) |
| PASS | hard | logic_supply | regulator required (battery 11.1 V > 3.3 V) | regulator present |  |  |
| PASS | hard | regulator_input[POL-2858] | 5.3-36.0 V | 11.1 V battery |  |  |
| PASS | hard | regulator_current[POL-2858] | <= 2.2 A | 0.172 A | +92.2% |  |
| PASS | hard | speed | >= 0.8 m/s | 1.15 m/s | +43.9% | full-throttle speed on level ground with payload |
| PASS | hard | torque_continuous | <= 0.392 N-m | 0.0266 N-m | +93.2% | climb torque x safety factor vs manufacturer continuous-load limit |
| PASS | hard | torque_peak | <= 0.785 N-m | 0.0629 N-m | +92.0% | accelerating up the design grade x safety factor vs instantaneous limit / stall torque |
| PASS | soft | motor_thermal | <= 1.16 A | 0.328 A | +71.6% | continuous current vs 25% of stall current |
| PASS | hard | runtime | >= 4 h | 7.51 h | +87.8% |  |
| PASS | hard | battery_current | <= 480 A | 1.14 A | +99.8% |  |
| PASS | hard | mass | <= 5 kg | 2.42 kg | +51.7% | includes payload |
| PASS | hard | budget | <= 1,200 SAR | 1,107 SAR | +7.7% |  |
| WARN | soft | assumed_items | sourced parts | HRM-CHASSIS-PLY6, HRM-PAYLOAD-BIN, HRM-WIRING-KIT |  | mass/cost of these items are engineering allowances |

## Iteration History

| Design | Strategy | Verification | Score | Cost (SAR) | Runtime (h) | Failed hard checks | Changes / rationale |
|---|---|---|---|---|---|---|---|
| #1 | economy | FAIL | -1.51 | 883 | 1.959 | hub_shaft_match, runtime | First design - no previous. |
| #2 | economy | PASS | 0.0 | 1,107 | 7.5125 | - | Four changes from design #1: (1) POL-1083 (6mm shaft hubs) replaced with POL-1081 (4mm shaft hubs) to fix hub_shaft_match — the POL-1081 hub has a 4mm bore that |

## Critic Findings

**Design #2 - verdict PASS:** The design passes all deterministic checks and is functionally sound for the stated mission. Key unverified items (caster load rating, logic-level compatibility) cannot be resolved by alternative database components — the only dual-channel motor driver and the only casters all lack this data. The three assumed items are engineering allowances with no better database alternatives. The VL53L1X range margin at speed is a testing concern, not a design flaw. Within the available component database and 93 SAR headroom, no concrete fixable problem exists that a different selection would solve.
- [medium] *evidence*: Caster POL-2692 has no load rating in the database. With total system mass 2.42 kg and a 3-point support configuration, the caster may bear 0.8-1.2 kg. No load rating data exists for any caster in the database (POL-2691 or POL-2692), so this cannot be verified. -> Physically verify caster load capacity against the actual weight distribution before procurement. No alternative database component resolves this.
- [medium] *evidence*: Logic level compatibility between ESP32 Feather V2 (3.3V I/O) and VNH5019 driver (POL-2507) is UNVERIFIED. The driver's logic input voltage range is not documented in the sourced database evidence, though the VNH5019 is known to accept 3.3V logic. -> Confirm from the VNH5019 full datasheet that VIH(min) ≤ 3.3V. No alternative driver exists in the database (POL-2507 is the only dual-channel ≥5A unit).
- [medium] *assumption*: Three BOM items (HRM-CHASSIS-PLY6, HRM-PAYLOAD-BIN, HRM-WIRING-KIT) are engineering allowances with assumed mass (770 g total) and cost (195 SAR total). If actual components are heavier or costlier, mass or budget constraints could be violated. -> Source actual components and verify mass/cost before build. No alternative database parts exist for payload bin or wiring; HRM-CHASSIS-AL3 is heavier and more expensive.
- [low] *functional*: VL53L1X range sensor (POL-3415) has a maximum range of 400 cm. At 1.0 m/s cruise speed, this provides only 4 seconds of detection time. Detection reliability on low-reflectivity indoor targets (dark surfaces, glass) may be significantly shorter. -> Test obstacle detection performance at speed with representative indoor targets. No alternative range sensor exists in the database.
- [low] *thermal*: Motor driver POL-2507 (VNH5019) is rated for 12 A continuous per channel but the actual peak motor current is only 0.527 A. While this provides ample margin, the driver's thermal derating at 11.1 V input and the shield form factor's heat dissipation in a confined chassis are unverified. -> Verify driver temperature under sustained operation at the design current. No alternative driver exists.
- [low] *compatibility*: POL-2507 is an Arduino shield form factor; the ESP32 Feather V2 does not have Arduino-compatible pin headers. Connecting them requires jumper wires rather than direct stacking, increasing wiring complexity and potential for loose connections. -> Use a breadboard or custom wiring harness. No alternative driver exists in the database.

## Final Design

The final design satisfies the specified computational constraints.

## Bill of Materials

| Component | Manufacturer | Part number | Qty | Packs | Unit price (USD) | Total (SAR) | Weight (g) | Key specification | Data |
|---|---|---|---|---|---|---|---|---|---|
| 34:1 Metal Gearmotor 25Dx52L mm HP 12V | Pololu | 3204 | 2 |  | 32.95 | 247.13 | 176.0 | 34.014:1, 300 rpm no-load, stall 11.0 kg-cm / 5.0 A @ 12 V, no encoder | sourced |
| Wheel 80x10mm Pair - Black | Pololu | 1430 | 2 | 1 | 8.75 | 32.81 | 39.7 | 80 mm diameter, 3.0 mm bore (needs one mounting hub per wheel to fit a larger motor shaft) | sourced |
| Universal Aluminum Mounting Hub for 4mm Shaft, #4-40 Holes (2-Pack) | Pololu | 1081 | 2 | 1 | 10.95 | 41.06 | 6.4 | for 4 mm shaft, joins one wheel to one motor | sourced |
| 25D mm Metal Gearmotor Bracket Pair | Pololu | 2676 | 2 | 1 | 10.95 | 41.06 | 17.0 | for 25D gearmotors | sourced |
| Ball Caster with 1in Plastic Ball and Ball Bearings | Pololu | 2692 | 1 |  | 9.95 | 37.31 | 18.5 | sourced | sourced |
| Dual VNH5019 Motor Driver Shield for Arduino | Pololu | 2507 | 1 |  | 39.95 | 149.81 | 18.0 | 2 ch, 12.0 A cont/ch, 5.5-24.0 V | sourced |
| OVONIC 3S 6000mAh 80C 11.1V LiPo Battery (Deans T) | Ovonic | 3S-6000-80C | 1 |  | 34.99 | 131.21 | 362.0 | LiPo 11.1 V 6000 mAh (66.6 Wh), 80C | sourced |
| ESP32 Feather V2 - 8MB Flash + 2 MB PSRAM | Adafruit | 5400 | 1 |  | 19.95 | 74.81 | 6.0 | 240 mA @ 3.3 V | sourced |
| VL53L1X Time-of-Flight Distance Sensor Carrier, 400 cm max | Pololu | 3415 | 1 |  | 22.95 | 86.06 | 0.5 | 20 mA @ 3.3 V | sourced |
| 5V 2.5A Step-Down Voltage Regulator D24V22F5 | Pololu | 2858 | 1 |  | 18.95 | 71.06 | 2.3 | 5.0 V out, 2.2 A, 5.3-36.0 V in | sourced |
| Custom plywood base plate 300x250x6 mm | Local fabrication | N/A | 1 |  | 12.00 | 45.00 | 270.0 | assumed | assumed |
| Payload bin / enclosure (2 kg class) | Local fabrication | N/A | 1 |  | 20.00 | 75.00 | 350.0 | assumed | assumed |
| Wiring, connectors, fuse, switch and fasteners allowance | Various | N/A | 1 |  | 20.00 | 75.00 | 150.0 | assumed | assumed |
| **TOTAL** |  |  |  |  |  | **1,107.34** | **1416.4** |  |  |

Prices: single-unit list prices (USD) converted at the fixed 3.75 SAR/USD peg; shipping, customs and VAT excluded.

## Sources / Evidence

**Component specifications (structured database):**
- POL-3204: https://www.pololu.com/product/3204/specs (retrieved 2026-10-07)
- POL-1430: https://www.pololu.com/product/1430/specs (retrieved 2026-10-07)
- POL-1081: https://www.pololu.com/product/1081/specs (retrieved 2026-10-07)
- POL-2676: https://www.pololu.com/product/2676/specs (retrieved 2026-10-07)
- POL-2692: https://www.pololu.com/product/2692/specs (retrieved 2026-10-07)
- POL-2507: https://www.pololu.com/product/2507/specs (retrieved 2026-10-07)
- OVO-3S-6000-80C: https://us.ovonicshop.com/products/ovonic-3s-lipo-battery-6000mah-3s1p-80c-11-1v-rc-lipo-battery-with-deans-t-plug-for-rc-1-8-1-10-scale-vehicles-car-trucks-boats (retrieved 2026-10-07)
- ADA-5400: https://www.adafruit.com/product/5400 (retrieved 2026-10-07)
- POL-3415: https://www.pololu.com/product/3415/specs (retrieved 2026-10-07)
- POL-2858: https://www.pololu.com/product/2858/specs (retrieved 2026-10-07)
- HRM-CHASSIS-PLY6: ASSUMED (no external source)
- HRM-PAYLOAD-BIN: ASSUMED (no external source)
- HRM-WIRING-KIT: ASSUMED (no external source)

**Datasheet evidence retrieved by the research agents (RAG):**
- [battery] [Ovonic 3S 11.1 V 1400 mAh 50C LiPo (XT60 and Trx plug)] Source: https://us.ovonicshop.com/products/ovonic-11-1v-1400mah-3s-50c-lipo-battery-with-xt60-trx-plug. Net weight 116 g (deviation 20 g). Price 21.99 USD. Dimensions are not stated in the parsed listing. Nameplate energy 11.1 V x 1.4 Ah = 15.5 Wh. - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://us.ovonicshop.com/products/ovonic-11-1v-1400mah-3s-50c-lipo-battery-with-xt60-trx-plug>
- [battery] [Ovonic charging and handling notes] Ovonic listings state: use Ovonic official RC LiPo battery chargers for optimal charging performance; ensure compatibility with both voltage and plug specifications; cease charging immediately upon reaching 4.2 V per cell (normal voltage range 3.7 V to 4.2 V per cell); inspect battery condition before each use. - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://us.ovonicshop.com/>
- [battery] [Pololu Rechargeable NiMH Battery Pack: 7.2 V, 2200 mAh, 3x2 AA cells (item 2225)] Source: https://www.pololu.com/product/2225/specs. Size 43 x 29 x 51 mm. Weight 5.9 oz (167.3 g). 6 AA NiMH cells. Connector JR 3-pin female. Price 29.39 USD. Maximum discharge current is not stated. Nameplate energy 15.8 Wh. - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://www.pololu.com/product/2225/specs>
- [battery] [Pololu Rechargeable NiMH Battery Pack: 8.4 V, 2200 mAh, 4+3 AA cells (item 2226)] Source: https://www.pololu.com/product/2226/specs. Size 58 x 27 x 51 mm. Weight 6.9 oz (195.6 g). 7 AA NiMH cells. Connector JR 3-pin female. Price 33.07 USD. Maximum discharge current is not stated. Nameplate energy 18.5 Wh. - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://www.pololu.com/product/2226/specs>
- [battery] [Ovonic 3S 6000 mAh 80C 11.1 V LiPo (Deans T plug)] Source: https://us.ovonicshop.com/products/ovonic-3s-lipo-battery-6000mah-3s1p-80c-11-1v-rc-lipo-battery-with-deans-t-plug-for-rc-1-8-1-10-scale-vehicles-car-trucks-boats. Li-polymer, 6000 mAh, 11.1 V (3S). Continuous discharge rate 80C, maximum burst discharge rate 160C. Charge plug JST-XHR-4P, discharge plug Deans T, soft case. Net weight 362 g (+/-20 g). Size 134 x 42 x 29 mm (+/-5 mm). Price 3 - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://us.ovonicshop.com/products/ovonic-3s-lipo-battery-6000mah-3s1p-80c-11-1v-rc-lipo-battery-with-deans-t-plug-for-rc-1-8-1-10-scale-vehicles-car-trucks-boats>
- [battery] [Ovonic 7200 mAh 3S 11.1 V 80C LiPo hardcase (Deans plug)] Source: https://us.ovonicshop.com/products/ovonic-80c-11-1v-7200mah-3s1p-hardcase-t-lipo-battery. Net weight 458 g (deviation 20 g). Hardcase. Price 71.99 USD. Nameplate energy 79.9 Wh. - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://us.ovonicshop.com/products/ovonic-80c-11-1v-7200mah-3s1p-hardcase-t-lipo-battery>
- [electronics] VL53L1X ToF sensor: 400 cm max range, draws 20 mA @ 3.3 V, mass 0.5 g, price 22.95 USD (86 SAR). - *Pololu product 3415 search spec entry (data: sourced)*, page web <https://www.pololu.com/product/3415/specs>
- [electronics] TB6612FNG dual driver: 2 ch, 1.0 A continuous/channel (3.0 A peak, 2 A paralleled), supply 4.5-13.5 V, logic 2.7-5.5 V, 4.95 USD, 1.5 g. Pololu recommends continuous driver current above motor stall current. - *https://www.pololu.com/product/713/specs (retrieved 2026-10-07)*, page web <https://www.pololu.com/product/713/specs>
- [electronics] ESP32 Feather V2: supply current 240 mA @ 3.3 V (≈792 mW), 6 g, 19.95 USD (75 SAR). - *Adafruit product 5400 search spec entry (data: sourced)*, page web <https://www.adafruit.com/product/5400>
- [electronics] Pico W: VSYS input range 1.8-5.5 V, 3.3 V logic; weight and supply current NOT stated in cited sources (power draw unverified). - *Pico W datasheet p.13, https://datasheets.raspberrypi.com/picow/pico-w-datasheet.pdf; Adafruit product 5526 (data: partial)*, page web <https://www.adafruit.com/product/5526>
- [electronics] Dual VNH5019 shield: 2 ch, 12.0 A cont/ch (30 A peak), 5.5-24 V, 18 g, 39.95 USD (150 SAR); logic-level range not stated on specs page. - *https://www.pololu.com/product/2507/specs (retrieved 2026-10-07)*, page web <https://www.pololu.com/product/2507/specs>
- [electronics] G2 High-Power 18v17: single channel, 17 A continuous, 6.5-30 V, 44.95 USD (169 SAR) each; two units needed for differential drive. - *https://www.pololu.com/product/2991/specs (retrieved 2026-10-07)*, page web <https://www.pololu.com/product/2991/specs>
- [electronics] [TB6612FNG Dual Motor Driver Carrier (item 713)] Source: https://www.pololu.com/product/713/specs

- Motor channels: 2. Size 0.60 x 0.80 inch, weight 1.5 g.
- Operating voltage: 4.5 V minimum (can operate down to 2.5 V with reduced current capabilities), 13.5 V maximum.
- Continuous output current per channel: 1 A. Peak output current per channel: 3 A. Continuous paralleled output current: 2 A.
- Maximum PWM frequency: 100 kHz. Logic voltage 2.7 - *pololu_motor_drivers.md*, page web <https://www.pololu.com/product/713/specs>
- [electronics] [VL53L1X Time-of-Flight Distance Sensor Carrier with Voltage Regulator, 400 cm max (item 3415)] Source: https://www.pololu.com/product/3415/specs

- Size 0.5 x 0.7 x 0.085 inch; weight 0.5 g without optional headers.
- Resolution 1 mm. Maximum range 400 cm; effective range depends on configuration, target, and environment. Minimum range 4 cm; the sensor still detects closer targets but the measurement will not be accurate.
- Interface: I2C. Operating voltage 2.6 V to 5.5 V.
- Supply current: - *pololu_regulator_and_tof_sensor.md*, page web <https://www.pololu.com/product/3415/specs>
- [electronics] [Raspberry Pi Pico W (Adafruit product 5526)] Sources: https://www.adafruit.com/product/5526 and https://datasheets.raspberrypi.com/picow/pico-w-datasheet.pdf. Price 6.00 USD. Dimensions (unassembled) 51 x 21 x 1 mm. RP2040 (dual-core Cortex M0) with 2 MB QSPI flash and on-board wireless. VSYS is the main system input voltage, allowed range 1.8 V to 5.5 V, used by the on-board SMPS to generate 3.3 V. VBUS is 5 V +/-10%. The datasheet states t - *controllers_esp32_pico_w_bno055.md*, page 13 <https://www.adafruit.com/product/5526>
- [electronics] [Adafruit ESP32 Feather V2 - 8MB Flash + 2 MB PSRAM (Adafruit product 5400)] Source: https://www.adafruit.com/product/5400. Product dimensions 52.3 x 22.8 x 7.2 mm. Product weight 6.0 g. Price 19.95 USD. 240 MHz dual-core Tensilica LX6 microcontroller, 520 KB SRAM, integrated 802.11b/g/n Wi-Fi and dual-mode Bluetooth. As of June 30, 2022 the board may come with a different regulator than the AP2112K due to parts shortages; the regulator can provide at least 500 mA. The ESP - *controllers_esp32_pico_w_bno055.md*, page web <https://www.adafruit.com/product/5400>
- [electronics] [Dual VNH5019 Motor Driver Shield for Arduino (item 2507)] Source: https://www.pololu.com/product/2507/specs

- Motor channels: 2. Size 2.56 x 2.02 x 0.38 inch, weight 18 g without included hardware.
- Operating voltage: 5.5 V minimum, 24 V maximum; not recommended for use with 24 V batteries.
- Continuous output current per channel: 12 A. Peak output current per channel: 30 A.
- Current sense: 0.14 V/A. Maximum PWM frequency: 20 kHz.
- Reverse voltage pr - *pololu_motor_drivers.md*, page web <https://www.pololu.com/product/2507/specs>
- [electronics] [Selection guidance] Pololu generally recommends a motor controller that can handle continuous currents above the stall current of the motor (stated on the 37D and 25D gearmotor pages). The 12 V 37D gearmotors stall at 5.5 A and the HP 12 V 25D gearmotors at 5.0 A (extrapolated), so a 1 A-per-channel driver such as the TB6612FNG is below that recommendation, while the VNH5019 (12 A) and G2 18v17 (17 A) exceed it. - *pololu_motor_drivers.md*, page web <https://www.pololu.com/product/713/specs>
- [electronics] [Adafruit 9-DOF Absolute Orientation IMU Fusion Breakout - BNO055, STEMMA QT (Adafruit product 4646)] Source: https://www.adafruit.com/product/4646. Price 29.95 USD. The Bosch BNO055 combines a MEMS accelerometer, magnetometer and gyroscope on a single die with an ARM Cortex-M0 based processor that performs sensor fusion and outputs quaternions, Euler angles or vectors. Uses I2C address 0x28 (default) or 0x29. The product page does not state weight or supply current; these specifications are not v - *controllers_esp32_pico_w_bno055.md*, page web <https://www.adafruit.com/product/4646>
- [electronics] [5V, 2.5A Step-Down Voltage Regulator D24V22F5 (item 2858)] Source: https://www.pololu.com/product/2858/specs

- Size 0.7 x 0.7 x 0.31 inch; weight 2.3 g without optional headers.
- Input voltage: 5.3 V minimum (for small loads; this voltage rises approximately linearly up to around 5.8 V at 2.5 A output), 36 V maximum.
- Output voltage: 5 V. Continuous output current: 2.2 A typical maximum at 24 V input. Actual achievable continuous output current is a fu - *pololu_regulator_and_tof_sensor.md*, page web <https://www.pololu.com/product/2858/specs>
- [mechanical] POL-1435: Wheel 90x10mm Pair - 22.68 g, 90 mm diameter, 3.0 mm bore; needs one mounting hub per wheel to fit a larger motor shaft (data: sourced). - *search_components result for category wheel*, page component database entry
- [mechanical] POL-1430: Wheel 80x10mm Pair - 19.84 g, 80 mm diameter, 3.0 mm bore; needs one mounting hub per wheel (data: sourced). - *search_components result for category wheel*, page component database entry
- [mechanical] HRM-CHASSIS-PLY6: 300x250x6 mm plywood base plate, 270 g, 45 SAR; data provenance 'assumed' (not sourced). - *search_components result for category chassis*, page component database entry
- [mechanical] HRM-CHASSIS-AL3: 300x250x3 mm aluminium base plate, 607.5 g, 150 SAR; data provenance 'assumed' (not sourced). - *search_components result for category chassis*, page component database entry
- [mechanical] POL-1083: Universal aluminium mounting hub for 6 mm shaft, #4-40 holes, 2-pack 6.8 g, 49 SAR; POL-1081: for 4 mm shaft, 2-pack 3.2 g, 41 SAR - joins one wheel to one motor (data: sourced). - *search_components result for category hub*, page component database entry
- [mechanical] POL-2692: Ball caster with 1 in plastic ball and ball bearings, 18.5 g, 37 SAR; POL-2691: 1 in plastic ball with plastic rollers, 16.5 g, 22 SAR (data: sourced). - *search_components result for category caster*, page component database entry
- [mechanical] [Wheel 90x10mm Pair - Black (item 1435)] Source: https://www.pololu.com/product/1435/specs. Size 90 x 10 mm. Weight 0.8 oz per wheel including tire (22.7 g). Shaft (bore) diameter 3 mm, D-shaped hole for press fit onto Pololu micro metal gearmotors and mini plastic gearmotors. Price 9.49 USD per pair. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/1435/specs>
- [mechanical] [Wheel 80x10mm Pair - Black (item 1430)] Source: https://www.pololu.com/product/1430/specs. Size 80 x 10 mm. Weight 0.7 oz per wheel including tire (19.8 g). Bore 3 mm. Price 8.75 USD per pair.

Neither wheel specs page states a load rating. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/1430/specs>
- [mechanical] [Assumed structural items] - HRM-CHASSIS-AL3: custom aluminium base plate 300 x 250 x 3 mm. Mass 607.5 g is calculated from the assumed dimensions and the density of aluminium (2.70 g/cm3). Price 40 USD is an assumed fabrication estimate, not a quote.
- HRM-CHASSIS-PLY6: custom plywood base plate 300 x 250 x 6 mm. Mass 270 g is calculated with an assumed plywood density of 0.60 g/cm3. Price 12 USD is assumed.
- HRM-PAYLOAD- - *hermes_assumption_register.md*, page N/A <N/A (internal assumption register, not an external source)>
- [mechanical] [Universal Aluminum Mounting Hub for 6mm Shaft, #4-40 Holes, 2-Pack (item 1083)] Source: https://www.pololu.com/product/1083/specs. 25.4 mm diameter x 9.2 mm thick. Weight 6.8 g for a single hub without set screws. Shaft diameter 6 mm. Mounting hole size #4-40 (also the size of the set screws). Price 12.95 USD per 2-pack. The 37D gearmotor page lists this hub for attaching Pololu 80 mm and 90 mm wheels to the 6 mm output shaft. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/1083/specs>
- [mechanical] [Ball Caster with 1 inch Plastic Ball and Ball Bearings (item 2692)] Source: https://www.pololu.com/product/2692/specs. Ball diameter 1 inch, plastic ball, ball-bearing rollers. Weight 18.5 g. Price 9.95 USD. No load rating is stated. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/2692/specs>
- [mechanical] [Mounting] The 25D gearmotors have a 4 mm D-shaped output shaft. HERMES inference (from the related-products listing on the Pololu wheel pages, not an explicit statement): the Pololu universal aluminum mounting hub for 4 mm shafts can attach the 3 mm-bore 80 mm and 90 mm wheels. The Pololu 25D mm metal gearmotor bracket pair mounts these motors (two M3 screws per bracket included). - *pololu_25d_hp_metal_gearmotors.md*, page web <https://www.pololu.com/product/4843>
- [mechanical] [Stamped Aluminum L-Bracket Pair for 37D mm Metal Gearmotors (item 1084)] Source: https://www.pololu.com/product/1084/specs. Weight 11 g for a single bracket (no screws or nuts). Each bracket includes six M3 screws for securing the motor and features fourteen mounting holes. Price 11.95 USD per pair. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/1084/specs>
- [motor] POL-3204: 34.014:1 gear ratio, 300 rpm no-load, stall torque 11.0 kg-cm, continuous torque limit 4.0 kg-cm, max efficiency 44% at 260 rpm (12 V). - *Pololu product page*, page web <https://www.pololu.com/product/3204/specs>
- [motor] POL-3203: 20.4:1 gear ratio, 500 rpm no-load, stall torque 7.4 kg-cm, continuous torque limit 4.0 kg-cm, max efficiency 46% at 420 rpm (12 V). - *Pololu product page*, page web <https://www.pololu.com/product/3203/specs>
- [motor] POL-4742: 30:1 helical-pinion gear ratio, 330 rpm no-load, stall torque 14.0 kg-cm, continuous torque limit 10.0 kg-cm, max efficiency 54% at 280 rpm (12 V). - *Pololu product page*, page web <https://www.pololu.com/product/4742/specs>
- [motor] POL-4844: 34.014:1 gear ratio, 300 rpm no-load, stall torque 11.0 kg-cm, continuous torque limit 4.0 kg-cm, with 48 CPR encoder. - *Pololu product page*, page web <https://www.pololu.com/product/4844/specs>
- [motor] With 90 mm wheels, 0.8 m/s requires ~170 rpm wheel speed. Required torque per wheel: rolling resistance (0.022 N·m) + grade (0.019 N·m) + acceleration (0.056 N·m) = 0.078 N·m, ×1.5 SF = 0.118 N·m (1.2 kg-cm). All candidates exceed this. - *Mission profile calculation*, page web
- [motor] [Performance table at 12 V (HP 12V comparison table)] HP 12 V motors: stall current 5.0 A; no-load current 250 mA without encoder, 300 mA with encoder.

| Gear ratio | No-load speed | Stall torque | Max power | Without encoder | With encoder |
|---|---|---|---|---|---|
| 20.4:1 | 500 rpm | 7.4 kg-cm | 9.4 W | item 3203 | item 4843 |
| 34:1 (34.014:1) | 300 rpm | 11 kg-cm | 8.9 W | item 3204 | item 4844 | - *pololu_25d_hp_metal_gearmotors.md*, page web <https://www.pololu.com/product/4843>
- [motor] [Motor driver recommendation] Pololu's high-power motor drivers and Motoron controllers are available in various power levels, several of which can handle the 37D mm metal gearmotors. Pololu generally recommends a motor controller that can handle continuous currents above the stall current of your motor. - *pololu_37d_metal_gearmotors.md*, page web <https://www.pololu.com/product/4752>
- [motor] [Specifications per item (specs pages)] - 3203 (20.4:1, no encoder): 25D x 50L mm, 85 g, 4 mm D shaft. Max efficiency 46% at 420 rpm, 1.1 kg-cm, 0.88 A, 4.8 W output (12 V). At 6 V: 250 rpm no-load, 2.5 A stall, 3.7 kg-cm stall. Price 32.95 USD.
- 3204 (34:1, no encoder): 25D x 52L mm, 88 g, 4 mm D shaft. Max efficiency 44% at 260 rpm, 1.6 kg-cm, 0.82 A, 4.3 W output (12 V). Price 32.95 USD.
- 4843 (20.4:1, 48 CPR encoder): 25D x 65L mm - *pololu_25d_hp_metal_gearmotors.md*, page web <https://www.pololu.com/product/4843>
- [battery] OVO-3S-6000-80C: 3S LiPo, 6000 mAh, 66.6 Wh, 362 g, 34.99 USD (~131 SAR), 80C continuous discharge - *Ovonic US store product page*, page web <https://us.ovonicshop.com/products/ovonic-3s-lipo-battery-6000mah-3s1p-80c-11-1v-rc-lipo-battery-with-deans-t-plug-for-rc-1-8-1-10-scale-vehicles-car-trucks-boats>
- [battery] OVO-3S-7200-80C: 3S LiPo, 7200 mAh, 79.9 Wh, 458 g, 71.99 USD (~270 SAR), 80C continuous, hardcase - *Ovonic US store product page*, page web <https://us.ovonicshop.com/products/ovonic-80c-11-1v-7200mah-3s1p-hardcase-t-lipo-battery>
- [battery] OVO-3S-2200-50C: 3S LiPo, 2200 mAh, 24.4 Wh, 179 g, 24.34 USD (~91 SAR), 50C continuous - *Ovonic US store product page*, page web <https://us.ovonicshop.com/products/ovonic-3s-50c-11-1v-2200mah-lipo-battery-pack-with-deans-t-plug-for-rc-airplane-helicopter-quadcopter-rc-car-truck-boat>
- [electronics] POL-2507 Dual VNH5019 Motor Driver Shield: 2 channels, 12.0 A continuous per channel, input 5.5-24.0 V, 18 g, 39.95 USD (150 SAR). - *HERMES component database search (motor_driver, filters cont_current_a>=5, voltage_min_v<=12, voltage_max_v>=12, channels>=2)*, page search result
- [electronics] POL-3415 VL53L1X ToF sensor: 400 cm max range, 20 mA @ 3.3 V, 0.5 g, 22.95 USD (86 SAR). - *HERMES component database search (range_sensor)*, page search result
- [electronics] ADA-5400 ESP32 Feather V2: 8 MB flash + 2 MB PSRAM, 6 g, 240 mA @ 3.3 V, 19.95 USD (75 SAR). - *HERMES component database search (controller)*, page search result
- [electronics] ADA-5526 Raspberry Pi Pico W: 6.00 USD (22 SAR); weight not verified, data partial. - *HERMES component database search (controller)*, page search result
- [electronics] ADA-4646 BNO055 9-DOF IMU: 29.95 USD (112 SAR); weight not verified, data partial. - *HERMES component database search (imu)*, page search result
- [electronics] [Default mission-profile assumptions] - Cruise speed 1.0 m/s for the energy estimate (the top-speed requirement is checked separately).
- Design grade 5 degrees (ramps and kerb cuts); 10% of drive time spent climbing it.
- Peak acceleration 0.5 m/s2.
- Rolling resistance coefficient 0.02 for small hard wheels on paved or indoor surfaces. Rough outdoor surfaces can be several times higher.
- Torque safety factor 1.5 applied to continuo - *hermes_assumption_register.md*, page N/A <N/A (internal assumption register, not an external source)>
- [mechanical] POL-1430 wheel has a 3 mm D bore and mounts to 4/6 mm shafts with a Pololu universal mounting hub. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/1430/specs>
- [mechanical] POL-3204 25D gearmotor has a 4 mm D-shaped output shaft. - *pololu_25d_hp_metal_gearmotors.md*, page web <https://www.pololu.com/product/4843>
- [mechanical] POL-1081 universal aluminum mounting hub for 4 mm shafts can attach the 3 mm-bore 80 mm and 90 mm wheels. - *pololu_25d_hp_metal_gearmotors.md*, page web <https://www.pololu.com/product/4843>
- [mechanical] POL-1081 hub is 19 mm diameter x 5 mm thick, weighs 3.2 g per hub, fits 4 mm shaft. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/1081/specs>
- [mechanical] POL-2676 bracket pair fits 25D mm gearmotors, uses two M3 screws per bracket. - *pololu_25d_hp_metal_gearmotors.md*, page web <https://www.pololu.com/product/4843>
- [mechanical] [Universal Aluminum Mounting Hub for 4mm Shaft, #4-40 Holes, 2-Pack (item 1081)] Source: https://www.pololu.com/product/1081/specs. 19 mm diameter x 5 mm thick. Weight 3.2 g for a single hub without set screw. Shaft diameter 4 mm. Price 10.95 USD per 2-pack. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/1081/specs>
- [mechanical] [Mounting wheels] The 6 mm diameter gearbox output shaft works with the Pololu universal aluminum mounting hub for 6 mm shafts, which can be used to mount Pololu wheels (80 mm and 90 mm diameter) or custom wheels and mechanisms to the gearmotor's output shaft. Pololu's stamped aluminum L-bracket pair is made for mounting 37D mm gearmotors. - *pololu_37d_metal_gearmotors.md*, page web <https://www.pololu.com/product/4752>
- [mechanical] [Ball Caster with 1 inch Plastic Ball and Plastic Rollers (item 2691)] Source: https://www.pololu.com/product/2691/specs. Ball diameter 1 inch, plastic ball. Weight 16.5 g. Price 5.95 USD. No load rating is stated. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/2691/specs>

## Limitations

- Specifications are taken from vendor pages and datasheets on the retrieval date; prices and availability change.
- Motor performance uses a linear brushed-DC model built from extrapolated stall values; real motors stall earlier when hot.
- Energy use depends on the assumed mission profile (cruise speed, grade, rolling resistance); see Assumptions.
- Wheel and caster load ratings are not stated by the manufacturer and were not verified.
- logic_level[POL-2507]: Specification not verified. (driver logic-level range not stated in the source)
- assumed_items: HRM-CHASSIS-PLY6, HRM-PAYLOAD-BIN, HRM-WIRING-KIT (mass/cost of these items are engineering allowances)
- Critic (medium, evidence): Caster POL-2692 has no load rating in the database. With total system mass 2.42 kg and a 3-point support configuration, the caster may bear 0.8-1.2 kg. No load rating data exists for any caster in the database (POL-2691 or POL-2692), so this cannot be verified.
- Critic (medium, evidence): Logic level compatibility between ESP32 Feather V2 (3.3V I/O) and VNH5019 driver (POL-2507) is UNVERIFIED. The driver's logic input voltage range is not documented in the sourced database evidence, though the VNH5019 is known to accept 3.3V logic.
- Critic (medium, assumption): Three BOM items (HRM-CHASSIS-PLY6, HRM-PAYLOAD-BIN, HRM-WIRING-KIT) are engineering allowances with assumed mass (770 g total) and cost (195 SAR total). If actual components are heavier or costlier, mass or budget constraints could be violated.
- Critic (low, functional): VL53L1X range sensor (POL-3415) has a maximum range of 400 cm. At 1.0 m/s cruise speed, this provides only 4 seconds of detection time. Detection reliability on low-reflectivity indoor targets (dark surfaces, glass) may be significantly shorter.
- Critic (low, thermal): Motor driver POL-2507 (VNH5019) is rated for 12 A continuous per channel but the actual peak motor current is only 0.527 A. While this provides ample margin, the driver's thermal derating at 11.1 V input and the shield form factor's heat dissipation in a confined chassis are unverified.
- Critic (low, compatibility): POL-2507 is an Arduino shield form factor; the ESP32 Feather V2 does not have Arduino-compatible pin headers. Connecting them requires jumper wires rather than direct stacking, increasing wiring complexity and potential for loose connections.

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