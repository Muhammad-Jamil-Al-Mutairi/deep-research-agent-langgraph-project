# HERMES Engineering Report - Small Autonomous Delivery Robot

**AI-generated engineering proposal - not a certified engineering design.**

**Final status: STAGNATED.** LOOP / STAGNATION - the design loop stopped improving and all strategies were tried. The best candidate is reported below. Human review required.

## Executive Summary

**Executive Summary**

After five design iterations, the engineering proposal remains **unverified** (FAIL score –1.975). The final bill of materials (1,429 SAR, 1,645 g excluding payload) fails to meet multiple mandatory constraints: achievable speed is 2.26 m/s (required ≥2.5 m/s), runtime is 10.0 h (required ≥12 h), total mass including payload is 3.65 kg (required ≤3 kg), and budget is 1,429 SAR (required ≤600 SAR). Additionally, the bracket count is insufficient (one bracket pack for two motors), and two component specifications (IMU mass and supply current) remain unverified. The design stagnated after attempts to balance performance and cost (iterations #1–#5) failed to resolve these critical shortfalls. Physical validation and qualified engineering review are required before any real-world deployment.

## Requirements

| Requirement | Value | Type |
|---|---|---|
| Payload | 2.0 kg | explicit |
| Runtime | >= 12.0 h | explicit |
| Top speed | >= 2.5 m/s | explicit |
| Total mass | <= 3.0 kg (incl. payload) | explicit (payload interpretation: see assumptions) |
| Budget | <= 600 SAR | explicit |
| Feature | wheel_encoders | derived |
| Feature | imu | derived |
| Feature | range_sensor | derived |

## Assumptions

| ID | Assumption | Value | Rationale / origin |
|---|---|---|---|
| A1 | The 3 kg total mass limit includes the 2 kg payload. | true | Conservative interpretation: the user said 'total mass below 3 kg' without specifying whether payload is included. Assuming it includes the payload ensures the robot chassis + components stay within 1 kg, which is the stricter constraint. |
| A2 | Budget is in Saudi Riyals (SAR) as stated. | 600 SAR | The user explicitly specified 'budget below 600 SAR'. |
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

- wheel_encoders: Required for odometry to track distance traveled and estimate position during autonomous navigation.
- imu: Required for heading estimation and orientation awareness during autonomous navigation.
- range_sensor: Required for obstacle detection and avoidance during autonomous operation.

### Open questions for a human engineer

- What terrain type will the robot operate on (indoor/outdoor, flat/rough)?
- What is the operating environment temperature range?
- Is the robot expected to climb slopes or stairs?
- What type of payload (solid box, liquid, fragile)?
- Should the robot operate in GPS-denied environments?
- What charging method is available (docking station, battery swap)?
- What is the acceptable recharge time?

## Selected Architecture - Best candidate (not fully compliant) #4

Differential-drive platform: two direct-drive gearmotors with wheels on universal hubs, a ball caster, one battery pack feeding the motor driver directly and the controller through a step-down regulator.

- **motor**: 2 x 19:1 Metal Gearmotor 37Dx68L mm 12V with 64 CPR Encoder (Helical Pinion) (POL-4751)
- **motor_driver**: 1 x Dual VNH5019 Motor Driver Shield for Arduino (POL-2507)
- **battery**: 1 x OVONIC 3S 6000mAh 80C 11.1V LiPo Battery (Deans T) (OVO-3S-6000-80C)
- **regulator**: 1 x 5V 2.5A Step-Down Voltage Regulator D24V22F5 (POL-2858)
- **controller**: 1 x ESP32 Feather V2 - 8MB Flash + 2 MB PSRAM (ADA-5400)
- **imu**: 1 x 9-DOF Absolute Orientation IMU Fusion Breakout - BNO055 (STEMMA QT) (ADA-4646)
- **range_sensor**: 1 x VL53L1X Time-of-Flight Distance Sensor Carrier, 400 cm max (POL-3415)
- **wheel**: 2 x Wheel 90x10mm Pair - Black (POL-1435)
- **hub**: 2 x Universal Aluminum Mounting Hub for 6mm Shaft, #4-40 Holes (2-Pack) (POL-1083)
- **bracket**: 1 x Stamped Aluminum L-Bracket Pair for 37D mm Metal Gearmotors (POL-1084)
- **caster**: 1 x Ball Caster with 1in Plastic Ball and Plastic Rollers (POL-2691)
- **chassis**: 1 x Custom plywood base plate 300x250x6 mm (HRM-CHASSIS-PLY6)
- **structure**: 1 x Payload bin / enclosure (2 kg class) (HRM-PAYLOAD-BIN)
- **wiring**: 1 x Wiring, connectors, fuse, switch and fasteners allowance (HRM-WIRING-KIT)

## Component Selection

Performance strategy: fix the most critical failures first. (1) hub_shaft_match: replaced POL-1081 (4mm hub) with POL-1083 (6mm hub) to match POL-4751's 6mm shaft. (2) bracket_match: replaced POL-2676 (25D bracket) with POL-1084 (37D bracket) to fit the 37D motors. (3) driver_current: replaced POL-713 (1A/ch) with POL-2507 (12A/ch) to handle motor stall current up to 5.5A. (4) runtime: replaced OVO-3S-2200-50C (24.4Wh) with OVO-3S-6000-80C (66.6Wh) for ~2.7x more energy, targeting ~10h runtime. (5) speed: kept 90mm wheels and 18.75:1 motors as the only available combination; speed may still be marginal. (6) mass and budget remain concerns but the performance strategy prioritises fixing functional constraints first.

## Engineering Calculations

| Quantity | Value | Unit | Provenance | Formula / inputs | Note |
|---|---|---|---|---|---|
| component_mass | 1.6453 | kg | CALCULATED | sum of BOM line masses = 1645.3 g | 1 item(s) without a verified mass |
| total_mass | 3.6453 | kg | CALCULATED | components 1.645 kg + payload 2.000 kg |  |
| bom_cost_sar | 1428.68 | SAR | CALCULATED | 380.98 USD x 3.75 SAR/USD (BOM) |  |
| n_drive_motors | 2.0 | - | CALCULATED | count of drive motors in BOM |  |
| supply_voltage | 11.1 | V | SOURCED | nominal voltage of OVO-3S-6000-80C |  |
| rolling_force | 0.715 | N | CALCULATED | Crr*m*g = 0.02 x 3.645 x 9.807 |  |
| grade_force | 3.1157 | N | CALCULATED | m*g*sin(5.0 deg) = 3.645 x 9.807 x sin(5.0) |  |
| accel_force | 1.8226 | N | CALCULATED | m*a = 3.645 x 0.5 |  |
| torque_level | 0.0161 | N-m | CALCULATED | F_rr*r/n = 0.715 x 0.0450 / 2 |  |
| torque_continuous | 0.0862 | N-m | CALCULATED | (F_rr+F_grade)*r/n = (0.715+3.116) x 0.0450 / 2 |  |
| torque_peak | 0.1272 | N-m | CALCULATED | (F_rr+F_grade+F_acc)*r/n = (0.715+3.116+1.823) x 0.0450 / 2 |  |
| torque_continuous_design | 0.1293 | N-m | CALCULATED | T_cont x SF = 0.0862 x 1.5 |  |
| torque_peak_design | 0.1908 | N-m | CALCULATED | T_peak x SF = 0.1272 x 1.5 |  |
| motor_stall_torque_at_supply | 0.771 | N-m | CALCULATED | Ts*V/Vr = 0.8336 x 11.1/12.0 |  |
| motor_stall_current_at_supply | 5.0875 | A | CALCULATED | Is*V/Vr = 5.5 x 11.1/12.0 |  |
| required_wheel_rpm | 530.5165 | rpm | CALCULATED | v/(pi*d)*60 = 2.5/(pi x 0.09) x 60 |  |
| loaded_wheel_rpm | 480.0217 | rpm | CALCULATED | n0'*(1-T_level/Ts') at 11.1 V |  |
| achievable_speed | 2.262 | m/s | CALCULATED | rpm*pi*d/60 = 480.0 x pi x 0.09/60 |  |
| motor_current_continuous | 0.748 | A | CALCULATED | I0 + T_cont/Kt = 0.2 + 0.0862/0.1573 |  |
| motor_current_peak | 1.4131 | A | CALCULATED | I0 + T_peak_design/Kt = 0.2 + 0.1908/0.1573 |  |
| motor_thermal_current_limit | 1.2719 | A | CALCULATED | 25% of stall current at supply voltage (Pololu guidance) |  |
| motor_power_level | 1.5989 | W | CALCULATED | per motor, T=0.0161 N-m at 212 rpm (cruise 1.0 m/s) |  |
| motor_power_grade | 4.684 | W | CALCULATED | per motor, T=0.0862 N-m at 212 rpm |  |
| mechanical_power_level | 0.715 | W | CALCULATED | n x T_level x w_cruise |  |
| drive_power_avg | 4.0156 | W | CALCULATED | n x ((1-0.1) x P_level + 0.1 x P_grade) / eta_driver(0.95) |  |
| logic_power | 1.108 | W | CALCULATED | sum of device supply current x voltage (allowance for unverified devices) |  |
| electronics_power_battery | 1.3035 | W | CALCULATED | logic power / eta_regulator(0.85) |  |
| regulator_output_current | 0.2216 | A | CALCULATED | logic power / 5.0 V |  |
| system_power_avg | 5.3192 | W | CALCULATED | P_drive 4.02 + P_electronics 1.30 |  |
| battery_energy | 66.6 | Wh | CALCULATED | V x C = 11.1 x 6000.0 mAh |  |
| battery_usable_energy | 53.28 | Wh | CALCULATED | E x usable fraction = 66.60 x 0.8 |  |
| runtime | 10.0166 | h | CALCULATED | E_usable / P_avg = 53.28 / 5.32 |  |
| capacity_needed_for_runtime | 7188.0743 | mAh | CALCULATED | t x P / (V x usable) = 12.0 x 5.32 / (11.1 x 0.8) |  |
| battery_peak_current | 2.9437 | A | CALCULATED | n x I_peak + P_elec/V = 2 x 1.413 + 1.30/11.1 |  |
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
| PASS | hard | hub_shaft_match | >= 2 hubs | 2 hubs | +0.0% | hubs must fit the 6 mm motor shaft |
| FAIL | hard | bracket_match | >= 2 brackets | 1 brackets | -50.0% | brackets must fit 37D gearmotors |
| PASS | hard | driver_channels | >= 2 channels | 2 channels | +0.0% |  |
| PASS | hard | driver_voltage[POL-2507] | 5.5-24.0 V | 11.1 V battery |  |  |
| PASS | hard | driver_current[POL-2507] | >= 1.41 A | 12 A | +749.2% | driver continuous rating vs motor current at design peak torque |
| PASS | soft | driver_stall_rating[POL-2507] | >= 5.09 A | 12 A | +135.9% | Pololu recommends drivers rated above motor stall current |
| UNVERIFIED | soft | logic_level[POL-2507] | controller logic within driver logic range | Specification not verified. |  | driver logic-level range not stated in the source |
| PASS | soft | motor_voltage | <= 13.2 V | 11.1 V | +15.9% | battery nominal voltage vs motor rated voltage (+10%) |
| PASS | hard | logic_supply | regulator required (battery 11.1 V > 3.3 V) | regulator present |  |  |
| PASS | hard | regulator_input[POL-2858] | 5.3-36.0 V | 11.1 V battery |  |  |
| PASS | hard | regulator_current[POL-2858] | <= 2.2 A | 0.222 A | +89.9% |  |
| FAIL | hard | speed | >= 2.5 m/s | 2.26 m/s | -9.5% | full-throttle speed on level ground with payload |
| PASS | hard | torque_continuous | <= 0.981 N-m | 0.129 N-m | +86.8% | climb torque x safety factor vs manufacturer continuous-load limit |
| PASS | hard | torque_peak | <= 0.771 N-m | 0.191 N-m | +75.3% | accelerating up the design grade x safety factor vs instantaneous limit / stall torque |
| PASS | soft | motor_thermal | <= 1.27 A | 0.748 A | +41.2% | continuous current vs 25% of stall current |
| FAIL | hard | runtime | >= 12 h | 10 h | -16.5% |  |
| PASS | hard | battery_current | <= 480 A | 2.94 A | +99.4% |  |
| FAIL | hard | mass | <= 3 kg | 3.65 kg | -21.5% | includes payload |
| FAIL | hard | budget | <= 600 SAR | 1,429 SAR | -138.1% |  |
| UNVERIFIED | soft | evidence_coverage | all specs verified | 2 unverified |  | mass of ADA-4646; supply current of ADA-4646 (allowance 0.25 W used) |
| WARN | soft | assumed_items | sourced parts | HRM-CHASSIS-PLY6, HRM-PAYLOAD-BIN, HRM-WIRING-KIT |  | mass/cost of these items are engineering allowances |

## Iteration History

| Design | Strategy | Verification | Score | Cost (SAR) | Runtime (h) | Failed hard checks | Changes / rationale |
|---|---|---|---|---|---|---|---|
| #1 | economy | FAIL | -3.683 | 1,250 | 3.7549 | hub_shaft_match, bracket_match, driver_current[POL-713], speed, runtime, mass, budget | Economy strategy: POL-4751 (19:1, 530 rpm) is the cheapest motor with encoder that can reach 2.5 m/s with 90 mm wheels. POL-1435 wheels (90 mm) give better grou |
| #2 | balanced | FAIL | -4.363 | 1,166 | 8.1867 | feature_imu, hub_shaft_match, bracket_match, driver_current[POL-713], speed, runtime, mass, budget | From CLOSEST DESIGN SO FAR #1: (1) Motors: POL-4751 (37D, 200g, 229 SAR each) → POL-4843 (25D, 98g, 214 SAR each) — lighter, cheaper, still has encoder. (2) Hub |
| #3 | balanced | FAIL | -3.934 | 1,392 | 3.7485 | hub_shaft_match, bracket_match, speed, runtime, mass, budget | Starting from CLOSEST DESIGN SO FAR #1. Changes: (1) POL-713 motor driver replaced with POL-2507 (12A cont/ch) to fix driver_current failure. (2) POL-1084 brack |
| #4 | performance | FAIL | -1.975 | 1,429 | 10.0166 | bracket_match, speed, runtime, mass, budget | Starting from CLOSEST DESIGN SO FAR #1: (1) hub: POL-1081 (4mm) → POL-1083 (6mm) to match POL-4751 6mm shaft, fixing hub_shaft_match. (2) bracket: POL-1084 was  |
| #5 | relax_soft_preferences | FAIL | -3.452 | 1,264 | 7.8292 | hub_shaft_match, bracket_match, driver_current[POL-713], speed, runtime, mass, budget | From CLOSEST DESIGN SO FAR #4: (1) Motors: POL-4751→POL-4843 (25D instead of 37D, saves 204g total mass and 30 SAR total). (2) Brackets: POL-1084→POL-2676 (25D  |

## Critic Findings

The critic did not run (no design passed verification).

## Final Design

LOOP / STAGNATION - the design loop stopped improving and all strategies were tried. The best candidate is reported below. Human review required.

## Bill of Materials

| Component | Manufacturer | Part number | Qty | Packs | Unit price (USD) | Total (SAR) | Weight (g) | Key specification | Data |
|---|---|---|---|---|---|---|---|---|---|
| 19:1 Metal Gearmotor 37Dx68L mm 12V with 64 CPR Encoder (Helical Pinion) | Pololu | 4751 | 2 |  | 60.95 | 457.12 | 400.0 | 18.75:1, 530 rpm no-load, stall 8.5 kg-cm / 5.5 A @ 12 V, encoder | sourced |
| Wheel 90x10mm Pair - Black | Pololu | 1435 | 2 | 1 | 9.49 | 35.59 | 45.4 | 90 mm diameter, 3.0 mm bore | sourced |
| Universal Aluminum Mounting Hub for 6mm Shaft, #4-40 Holes (2-Pack) | Pololu | 1083 | 2 | 1 | 12.95 | 48.56 | 13.6 | for 6 mm shaft | sourced |
| Stamped Aluminum L-Bracket Pair for 37D mm Metal Gearmotors | Pololu | 1084 | 1 | 1 | 11.95 | 44.81 | 11.0 | for 37D gearmotors | sourced |
| Ball Caster with 1in Plastic Ball and Plastic Rollers | Pololu | 2691 | 1 |  | 5.95 | 22.31 | 16.5 | sourced | sourced |
| Dual VNH5019 Motor Driver Shield for Arduino | Pololu | 2507 | 1 |  | 39.95 | 149.81 | 18.0 | 2 ch, 12.0 A cont/ch, 5.5-24.0 V | sourced |
| ESP32 Feather V2 - 8MB Flash + 2 MB PSRAM | Adafruit | 5400 | 1 |  | 19.95 | 74.81 | 6.0 | 240 mA @ 3.3 V | sourced |
| 9-DOF Absolute Orientation IMU Fusion Breakout - BNO055 (STEMMA QT) | Adafruit | 4646 | 1 |  | 29.95 | 112.31 | not verified | partial | partial |
| VL53L1X Time-of-Flight Distance Sensor Carrier, 400 cm max | Pololu | 3415 | 1 |  | 22.95 | 86.06 | 0.5 | 20 mA @ 3.3 V | sourced |
| OVONIC 3S 6000mAh 80C 11.1V LiPo Battery (Deans T) | Ovonic | 3S-6000-80C | 1 |  | 34.99 | 131.21 | 362.0 | LiPo 11.1 V 6000 mAh (66.6 Wh), 80C | sourced |
| 5V 2.5A Step-Down Voltage Regulator D24V22F5 | Pololu | 2858 | 1 |  | 18.95 | 71.06 | 2.3 | 5.0 V out, 2.2 A, 5.3-36.0 V in | sourced |
| Custom plywood base plate 300x250x6 mm | Local fabrication | N/A | 1 |  | 12.00 | 45.00 | 270.0 | assumed | assumed |
| Payload bin / enclosure (2 kg class) | Local fabrication | N/A | 1 |  | 20.00 | 75.00 | 350.0 | assumed | assumed |
| Wiring, connectors, fuse, switch and fasteners allowance | Various | N/A | 1 |  | 20.00 | 75.00 | 150.0 | assumed | assumed |
| **TOTAL** |  |  |  |  |  | **1,428.68** | **1645.3** |  |  |

Prices: single-unit list prices (USD) converted at the fixed 3.75 SAR/USD peg; shipping, customs and VAT excluded.

## Sources / Evidence

**Component specifications (structured database):**
- POL-4751: https://www.pololu.com/product/4751/specs (retrieved 2026-10-07)
- POL-1435: https://www.pololu.com/product/1435/specs (retrieved 2026-10-07)
- POL-1083: https://www.pololu.com/product/1083/specs (retrieved 2026-10-07)
- POL-1084: https://www.pololu.com/product/1084/specs (retrieved 2026-10-07)
- POL-2691: https://www.pololu.com/product/2691/specs (retrieved 2026-10-07)
- POL-2507: https://www.pololu.com/product/2507/specs (retrieved 2026-10-07)
- ADA-5400: https://www.adafruit.com/product/5400 (retrieved 2026-10-07)
- ADA-4646: https://www.adafruit.com/product/4646 (retrieved 2026-10-07)
- POL-3415: https://www.pololu.com/product/3415/specs (retrieved 2026-10-07)
- OVO-3S-6000-80C: https://us.ovonicshop.com/products/ovonic-3s-lipo-battery-6000mah-3s1p-80c-11-1v-rc-lipo-battery-with-deans-t-plug-for-rc-1-8-1-10-scale-vehicles-car-trucks-boats (retrieved 2026-10-07)
- POL-2858: https://www.pololu.com/product/2858/specs (retrieved 2026-10-07)
- HRM-CHASSIS-PLY6: ASSUMED (no external source)
- HRM-PAYLOAD-BIN: ASSUMED (no external source)
- HRM-WIRING-KIT: ASSUMED (no external source)

**Datasheet evidence retrieved by the research agents (RAG):**
- [battery] [Ovonic charging and handling notes] Ovonic listings state: use Ovonic official RC LiPo battery chargers for optimal charging performance; ensure compatibility with both voltage and plug specifications; cease charging immediately upon reaching 4.2 V per cell (normal voltage range 3.7 V to 4.2 V per cell); inspect battery condition before each use. - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://us.ovonicshop.com/>
- [battery] [Pololu Rechargeable NiMH Battery Pack: 8.4 V, 2200 mAh, 4+3 AA cells (item 2226)] Source: https://www.pololu.com/product/2226/specs. Size 58 x 27 x 51 mm. Weight 6.9 oz (195.6 g). 7 AA NiMH cells. Connector JR 3-pin female. Price 33.07 USD. Maximum discharge current is not stated. Nameplate energy 18.5 Wh. - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://www.pololu.com/product/2226/specs>
- [battery] [Pololu Rechargeable NiMH Battery Pack: 7.2 V, 2200 mAh, 3x2 AA cells (item 2225)] Source: https://www.pololu.com/product/2225/specs. Size 43 x 29 x 51 mm. Weight 5.9 oz (167.3 g). 6 AA NiMH cells. Connector JR 3-pin female. Price 29.39 USD. Maximum discharge current is not stated. Nameplate energy 15.8 Wh. - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://www.pololu.com/product/2225/specs>
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
- [mechanical] [Assumed structural items] - HRM-CHASSIS-AL3: custom aluminium base plate 300 x 250 x 3 mm. Mass 607.5 g is calculated from the assumed dimensions and the density of aluminium (2.70 g/cm3). Price 40 USD is an assumed fabrication estimate, not a quote.
- HRM-CHASSIS-PLY6: custom plywood base plate 300 x 250 x 6 mm. Mass 270 g is calculated with an assumed plywood density of 0.60 g/cm3. Price 12 USD is assumed.
- HRM-PAYLOAD- - *hermes_assumption_register.md*, page N/A <N/A (internal assumption register, not an external source)>
- [mechanical] [Wheel 90x10mm Pair - Black (item 1435)] Source: https://www.pololu.com/product/1435/specs. Size 90 x 10 mm. Weight 0.8 oz per wheel including tire (22.7 g). Shaft (bore) diameter 3 mm, D-shaped hole for press fit onto Pololu micro metal gearmotors and mini plastic gearmotors. Price 9.49 USD per pair. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/1435/specs>
- [mechanical] [Wheel 80x10mm Pair - Black (item 1430)] Source: https://www.pololu.com/product/1430/specs. Size 80 x 10 mm. Weight 0.7 oz per wheel including tire (19.8 g). Bore 3 mm. Price 8.75 USD per pair.

Neither wheel specs page states a load rating. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/1430/specs>
- [mechanical] [Ball Caster with 1 inch Plastic Ball and Ball Bearings (item 2692)] Source: https://www.pololu.com/product/2692/specs. Ball diameter 1 inch, plastic ball, ball-bearing rollers. Weight 18.5 g. Price 9.95 USD. No load rating is stated. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/2692/specs>
- [mechanical] [Ball Caster with 1 inch Plastic Ball and Plastic Rollers (item 2691)] Source: https://www.pololu.com/product/2691/specs. Ball diameter 1 inch, plastic ball. Weight 16.5 g. Price 5.95 USD. No load rating is stated. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/2691/specs>
- [mechanical] [Mounting] The 25D gearmotors have a 4 mm D-shaped output shaft. HERMES inference (from the related-products listing on the Pololu wheel pages, not an explicit statement): the Pololu universal aluminum mounting hub for 4 mm shafts can attach the 3 mm-bore 80 mm and 90 mm wheels. The Pololu 25D mm metal gearmotor bracket pair mounts these motors (two M3 screws per bracket included). - *pololu_25d_hp_metal_gearmotors.md*, page web <https://www.pololu.com/product/4843>
- [mechanical] [Stamped Aluminum L-Bracket Pair for 37D mm Metal Gearmotors (item 1084)] Source: https://www.pololu.com/product/1084/specs. Weight 11 g for a single bracket (no screws or nuts). Each bracket includes six M3 screws for securing the motor and features fourteen mounting holes. Price 11.95 USD per pair. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/1084/specs>
- [motor] POL-4751 (19:1) no-load speed 530 rpm @ 12V, stall torque 8.5 kg-cm, continuous torque limit 10 kg-cm, weight 200 g, price 60.95 USD, integrated 64 CPR encoder. - *Pololu product page*, page web <https://www.pololu.com/product/4751/specs>
- [motor] POL-4752 (30:1) no-load speed 330 rpm @ 12V, stall torque 14 kg-cm, continuous torque limit 10 kg-cm, weight 200 g, price 60.95 USD, integrated 64 CPR encoder. - *Pololu product page*, page web <https://www.pololu.com/product/4752/specs>
- [motor] POL-4843 (20.4:1) no-load speed 500 rpm @ 12V, stall torque 7.4 kg-cm, continuous torque limit 4 kg-cm, weight 98 g, price 56.95 USD, 48 CPR encoder. - *Pololu product page*, page web <https://www.pololu.com/product/4843/specs>
- [motor] POL-4844 (34:1) no-load speed 300 rpm @ 12V, stall torque 11 kg-cm, continuous torque limit 4 kg-cm, weight 101 g, price 56.95 USD, 48 CPR encoder. - *Pololu product page*, page web <https://www.pololu.com/product/4844/specs>
- [motor] POL-4753 (50:1) no-load speed 200 rpm @ 12V, stall torque 21 kg-cm, continuous torque limit 10 kg-cm, weight 205 g, price 60.95 USD, 64 CPR encoder. - *Pololu product page*, page web <https://www.pololu.com/product/4753/specs>
- [motor] Wheel diameter ~90 mm assumed for speed calculation. Speed (m/s) = (rpm/60) * pi * wheel_diameter. - *Standard kinematics*, page web
- [motor] [Specifications per item (specs pages)] - 4741 (19:1, no encoder): 37D x 52L mm, 185 g. Max efficiency 55% at 470 rpm, 1.0 kg-cm, 0.76 A, 5.0 W output (12 V). At 6 V: 270 rpm no-load, 3.0 A stall, 5.0 kg-cm stall.
- 4742 (30:1, no encoder): 37D x 52L mm, 185 g. Max efficiency 54% at 280 rpm, 1.8 kg-cm, 0.78 A, 5.1 W output (12 V). At 6 V: 170 rpm, 3.0 A stall, 7.9 kg-cm stall.
- 4743 (50:1, no encoder): 37D x 54L mm, 190 g. Max efficien - *pololu_37d_metal_gearmotors.md*, page web <https://www.pololu.com/product/4752>
- [motor] [Specifications per item (specs pages)] - 3203 (20.4:1, no encoder): 25D x 50L mm, 85 g, 4 mm D shaft. Max efficiency 46% at 420 rpm, 1.1 kg-cm, 0.88 A, 4.8 W output (12 V). At 6 V: 250 rpm no-load, 2.5 A stall, 3.7 kg-cm stall. Price 32.95 USD.
- 3204 (34:1, no encoder): 25D x 52L mm, 88 g, 4 mm D shaft. Max efficiency 44% at 260 rpm, 1.6 kg-cm, 0.82 A, 4.3 W output (12 V). Price 32.95 USD.
- 4843 (20.4:1, 48 CPR encoder): 25D x 65L mm - *pololu_25d_hp_metal_gearmotors.md*, page web <https://www.pololu.com/product/4843>
- [battery] [Ovonic 3S 6000 mAh 80C 11.1 V LiPo (Deans T plug)] Source: https://us.ovonicshop.com/products/ovonic-3s-lipo-battery-6000mah-3s1p-80c-11-1v-rc-lipo-battery-with-deans-t-plug-for-rc-1-8-1-10-scale-vehicles-car-trucks-boats. Li-polymer, 6000 mAh, 11.1 V (3S). Continuous discharge rate 80C, maximum burst discharge rate 160C. Charge plug JST-XHR-4P, discharge plug Deans T, soft case. Net weight 362 g (+/-20 g). Size 134 x 42 x 29 mm (+/-5 mm). Price 3 - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://us.ovonicshop.com/products/ovonic-3s-lipo-battery-6000mah-3s1p-80c-11-1v-rc-lipo-battery-with-deans-t-plug-for-rc-1-8-1-10-scale-vehicles-car-trucks-boats>
- [battery] [Voltage compatibility note] A 3S LiPo pack is 11.1 V nominal and 12.6 V at 4.2 V per cell, close to the 12 V rating of the 12 V gearmotors. The NiMH packs (7.2 V and 8.4 V) run 12 V gearmotors at reduced speed, because brushed-motor no-load speed scales approximately with supply voltage. - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://us.ovonicshop.com/>
- [battery] [Ovonic 3S 11.1 V 1400 mAh 50C LiPo (XT60 and Trx plug)] Source: https://us.ovonicshop.com/products/ovonic-11-1v-1400mah-3s-50c-lipo-battery-with-xt60-trx-plug. Net weight 116 g (deviation 20 g). Price 21.99 USD. Dimensions are not stated in the parsed listing. Nameplate energy 11.1 V x 1.4 Ah = 15.5 Wh. - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://us.ovonicshop.com/products/ovonic-11-1v-1400mah-3s-50c-lipo-battery-with-xt60-trx-plug>
- [battery] [Ovonic 7200 mAh 3S 11.1 V 80C LiPo hardcase (Deans plug)] Source: https://us.ovonicshop.com/products/ovonic-80c-11-1v-7200mah-3s1p-hardcase-t-lipo-battery. Net weight 458 g (deviation 20 g). Hardcase. Price 71.99 USD. Nameplate energy 79.9 Wh. - *batteries_ovonic_lipo_pololu_nimh.md*, page web <https://us.ovonicshop.com/products/ovonic-80c-11-1v-7200mah-3s1p-hardcase-t-lipo-battery>
- [electronics] [Dual VNH5019 Motor Driver Shield for Arduino (item 2507)] Source: https://www.pololu.com/product/2507/specs

- Motor channels: 2. Size 2.56 x 2.02 x 0.38 inch, weight 18 g without included hardware.
- Operating voltage: 5.5 V minimum, 24 V maximum; not recommended for use with 24 V batteries.
- Continuous output current per channel: 12 A. Peak output current per channel: 30 A.
- Current sense: 0.14 V/A. Maximum PWM frequency: 20 kHz.
- Reverse voltage pr - *pololu_motor_drivers.md*, page web <https://www.pololu.com/product/2507/specs>
- [electronics] [Selection guidance] Pololu generally recommends a motor controller that can handle continuous currents above the stall current of the motor (stated on the 37D and 25D gearmotor pages). The 12 V 37D gearmotors stall at 5.5 A and the HP 12 V 25D gearmotors at 5.0 A (extrapolated), so a 1 A-per-channel driver such as the TB6612FNG is below that recommendation, while the VNH5019 (12 A) and G2 18v17 (17 A) exceed it. - *pololu_motor_drivers.md*, page web <https://www.pololu.com/product/713/specs>
- [mechanical] [Universal Aluminum Mounting Hub for 6mm Shaft, #4-40 Holes, 2-Pack (item 1083)] Source: https://www.pololu.com/product/1083/specs. 25.4 mm diameter x 9.2 mm thick. Weight 6.8 g for a single hub without set screws. Shaft diameter 6 mm. Mounting hole size #4-40 (also the size of the set screws). Price 12.95 USD per 2-pack. The 37D gearmotor page lists this hub for attaching Pololu 80 mm and 90 mm wheels to the 6 mm output shaft. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/1083/specs>
- [mechanical] [Universal Aluminum Mounting Hub for 4mm Shaft, #4-40 Holes, 2-Pack (item 1081)] Source: https://www.pololu.com/product/1081/specs. 19 mm diameter x 5 mm thick. Weight 3.2 g for a single hub without set screw. Shaft diameter 4 mm. Price 10.95 USD per 2-pack. - *pololu_wheels_hubs_brackets_casters.md*, page web <https://www.pololu.com/product/1081/specs>

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