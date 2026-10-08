---
title: Controllers and IMU - Adafruit ESP32 Feather V2 (Espressif ESP32 datasheet), Raspberry Pi Pico W, Adafruit BNO055
manufacturer: Espressif; Adafruit; Raspberry Pi; Bosch
source_url: https://documentation.espressif.com/esp32_datasheet_en.pdf
page: 52
component_ids: ADA-5400, ADA-5526, ADA-4646
part_numbers: 5400, SC0918, 4646
retrieved_on: 2026-10-07
---

# Controllers and IMU

## ESP32 RF current consumption (Espressif ESP32 Series Datasheet v5.3, Table 5-4)

Components: ADA-5400

Page: 52

The current consumption measurements are taken with a 3.3 V supply at 25 C ambient temperature at the RF port. All transmitter measurements are based on a 50% duty cycle. Typical values: transmit 802.11b, DSSS 1 Mbps, POUT = +19.5 dBm: 240 mA. Transmit 802.11g, OFDM 54 Mbps, POUT = +16 dBm: 190 mA. Transmit 802.11n, OFDM MCS7, POUT = +14 dBm: 180 mA. Receive 802.11b/g/n: 95 to 100 mA.

## ESP32 power modes (Espressif ESP32 Series Datasheet v5.3)

Components: ADA-5400

Page: 5

Five power modes designed for typical scenarios: Active, Modem-sleep, Light-sleep, Deep-sleep, Hibernation. Power consumption in Deep-sleep mode is 10 uA. When Wi-Fi is enabled, the chip switches between Active and Modem-sleep modes, so power consumption changes accordingly (page 31).

## Adafruit ESP32 Feather V2 - 8MB Flash + 2 MB PSRAM (Adafruit product 5400)

Components: ADA-5400

Page: web

Source: https://www.adafruit.com/product/5400. Product dimensions 52.3 x 22.8 x 7.2 mm. Product weight 6.0 g. Price 19.95 USD. 240 MHz dual-core Tensilica LX6 microcontroller, 520 KB SRAM, integrated 802.11b/g/n Wi-Fi and dual-mode Bluetooth. As of June 30, 2022 the board may come with a different regulator than the AP2112K due to parts shortages; the regulator can provide at least 500 mA. The ESP32 runs at 3.3 V logic, so a battery above the board's input range must be regulated down (for example with a 5 V step-down regulator).

## Raspberry Pi Pico W (Adafruit product 5526)

Components: ADA-5526

Page: 13

Sources: https://www.adafruit.com/product/5526 and https://datasheets.raspberrypi.com/picow/pico-w-datasheet.pdf. Price 6.00 USD. Dimensions (unassembled) 51 x 21 x 1 mm. RP2040 (dual-core Cortex M0) with 2 MB QSPI flash and on-board wireless. VSYS is the main system input voltage, allowed range 1.8 V to 5.5 V, used by the on-board SMPS to generate 3.3 V. VBUS is 5 V +/-10%. The datasheet states that VBUS and VSYS current depend on the use-case; no single supply-current figure is given. The board weight is not stated in the cited sources. If using lithium-ion cells they must have, or be provided with, adequate protection against over-discharge, over-charge, charging outside the allowed temperature range and overcurrent (datasheet page 17).

## Adafruit 9-DOF Absolute Orientation IMU Fusion Breakout - BNO055, STEMMA QT (Adafruit product 4646)

Components: ADA-4646

Page: web

Source: https://www.adafruit.com/product/4646. Price 29.95 USD. The Bosch BNO055 combines a MEMS accelerometer, magnetometer and gyroscope on a single die with an ARM Cortex-M0 based processor that performs sensor fusion and outputs quaternions, Euler angles or vectors. Uses I2C address 0x28 (default) or 0x29. The product page does not state weight or supply current; these specifications are not verified in the HERMES knowledge base.
