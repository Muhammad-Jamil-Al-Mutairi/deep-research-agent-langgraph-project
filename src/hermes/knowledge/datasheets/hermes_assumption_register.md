---
title: HERMES assumption register - assumed items and default mission-profile values
manufacturer: HERMES
source_url: N/A (internal assumption register, not an external source)
page: N/A
component_ids: HRM-CHASSIS-AL3, HRM-CHASSIS-PLY6, HRM-PAYLOAD-BIN, HRM-WIRING-KIT
part_numbers: N/A
retrieved_on: 2026-10-07
---

# HERMES assumption register

Everything in this document is an ASSUMPTION, not a sourced fact. It exists so the
research agents can retrieve and cite assumptions explicitly instead of inventing them.

## Assumed structural items

- HRM-CHASSIS-AL3: custom aluminium base plate 300 x 250 x 3 mm. Mass 607.5 g is calculated from the assumed dimensions and the density of aluminium (2.70 g/cm3). Price 40 USD is an assumed fabrication estimate, not a quote.
- HRM-CHASSIS-PLY6: custom plywood base plate 300 x 250 x 6 mm. Mass 270 g is calculated with an assumed plywood density of 0.60 g/cm3. Price 12 USD is assumed.
- HRM-PAYLOAD-BIN: payload bin or enclosure sized for a 2 kg payload, 280 x 220 x 150 mm. Mass 350 g and price 20 USD are allowances.
- HRM-WIRING-KIT: wiring, battery connector, inline fuse, power switch, standoffs and fasteners. Mass 150 g and price 20 USD are allowances.

## Default mission-profile assumptions

- Cruise speed 1.0 m/s for the energy estimate (the top-speed requirement is checked separately).
- Design grade 5 degrees (ramps and kerb cuts); 10% of drive time spent climbing it.
- Peak acceleration 0.5 m/s2.
- Rolling resistance coefficient 0.02 for small hard wheels on paved or indoor surfaces. Rough outdoor surfaces can be several times higher.
- Torque safety factor 1.5 applied to continuous and peak torque.
- Usable battery energy 80% of nameplate, to avoid deep discharge.
- Logic regulator efficiency 85%; motor driver efficiency 95%.
- Devices with no verified supply current receive a 0.25 W power allowance.

## Modelling assumptions

- Differential drive: two driven wheels plus one ball caster; drive motors are direct-drive (no extra reduction).
- Gearmotor behaviour follows the linear brushed-DC model built from the manufacturer's no-load speed, no-load current, stall torque and stall current, with speed and stall values scaled by supply voltage / rated voltage.
- Battery voltage is taken at its nominal value (11.1 V for 3S LiPo).
- Prices are single-unit list prices in USD on the retrieval date, converted at the fixed 3.75 SAR/USD peg. Shipping, customs and VAT are excluded.
