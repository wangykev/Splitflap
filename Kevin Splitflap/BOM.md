# Split-Flap Wall BOM (Bill of Materials)

A 3 × 15 (45-module) split-flap wall: Adam G Makes modules on Kevin's ATtiny1616 driver board, an
ESP32-S3 RS-485 gateway, a WS2815 LED perimeter strip, and a Raspberry Pi running Home Assistant
with a "Hey Venus" voice satellite. See `../gateway/CLAUDE.md` for the full project plan.

- Original module design: [Adam G Makes](https://www.youtube.com/@AdamGMakes) ([build video](https://www.youtube.com/watch?v=-C8_AtxEEQc))
- Gateway / module firmware / Companion: [avandeputte](https://github.com/avandeputte) (submodules in `../gateway/`)

**Prices checked 2026-10-19, in USD, before sales tax and shipping unless a row says otherwise.**
The *Price* column marks where each number came from:
- **LIVE**: read from the product page.
- **SNIP**: taken from a search-result snippet, because the store blocked page loads.
- **EST**: an estimate.

Pack prices are rounded up to whole packs.

## Cost summary

| Section | Cost |
|---|---|
| [1. Driver PCBs, assembled by JLCPCB (50 boards)](#1-driver-pcb-jlcpcb-assembled) | $264.00 |
| [2. Bus boards (10 bare PCBs + headers)](#2-bus-board) | $18.00 |
| [3. Module hardware (45 modules)](#3-module-hardware-45-modules) | $286.65 |
| [4. Programming (UPDI flasher)](#4-programming-updi-flasher) | incl. above |
| [5. Gateway & RS-485 bus](#5-gateway--rs-485-bus) | $36.01 |
| [6. Power](#6-power) | $137.22 |
| [7. LED perimeter strip](#7-led-perimeter-strip) | $63.52 |
| **Wall total (Kevin's hardware side)** | **$805.40** |
| [8. Raspberry Pi + voice satellite (software side)](#8-raspberry-pi--voice-satellite) | $214.84 |
| **Grand total** | **≈ $1,020** |

Realistic all-in budget: **$1,050–1,100**. That leaves room for shipping from the 5–6 stores
involved and for the JLCPCB estimates (bare board price and tariff) landing ±$20.

Optional add-ons, not in the total:
- Ferrule crimp kit: +$39.95
- Pi 5 8GB instead of 4GB: +$70
- J5 header populated: +$14

3D-printed parts are not priced; see [section 9](#9-3d-printed-parts-not-priced).

---

## 1. Driver PCB (JLCPCB assembled)

Source: `PCBs/Kicad/SplitFlapDriverATtiny1616V4.kicad_pcb.kicad_pcb`. The board is 30 × 60 mm, 2-layer, 1.6 mm.

The order is 50 boards (45 needed plus 5 spares) using JLCPCB **Economic PCBA**, top side only.
Every part on the board is Economic-eligible. JLCPCB solders the through-hole connectors too.

| Ref | Part | LCSC | JLC lib | Qty/board | Order qty | Unit | Ext |
|---|---|---|---|---|---|---|---|
| U1 | ATtiny1616-MNR (VQFN-20) | [C507118](https://www.lcsc.com/product-detail/C507118.html) | Extended | 1 | 50 | $0.772 | $38.60 |
| U2 | ULN2003ADR (SOIC-16) | [C7512](https://www.lcsc.com/product-detail/C7512.html) | Basic | 1 | 50 | $0.1144 | $5.72 |
| U3 | SN65HVD72DR RS-485 (SOIC-8) | [C48125](https://www.lcsc.com/product-detail/C48125.html) | Extended | 1 | 50 | $0.8899 | $44.50 |
| U5 | SPX3819M5-L-3-3 LDO (SOT-23-5) | [C20617301](https://www.lcsc.com/product-detail/C20617301.html) | Extended | 1 | 50 | $0.0721 | $3.61 |
| U6 | SPX3819M5-L-5-0 LDO (SOT-23-5) | [C20617302](https://www.lcsc.com/product-detail/C20617302.html) | Extended | 1 | 50 | $0.1063 | $5.32 |
| C2, C3, C6, C8 | 470 nF 0603 | [C1623](https://www.lcsc.com/product-detail/C1623.html) | Basic | 4 | 200 | $0.0129 | $2.58 |
| C4, C5, C9 | 10 µF 0603 | [C19702](https://www.lcsc.com/product-detail/C19702.html) | Basic | 3 | 160 | $0.0273 | $4.37 |
| C7 | 100 nF 0603 | [C14663](https://www.lcsc.com/product-detail/C14663.html) | Basic | 1 | 50 | $0.0109 | $0.55 |
| C1 | 100 µF electrolytic 5 × 5.4 | [C3347](https://www.lcsc.com/product-detail/C3347.html) | Extended | 1 | 60 | $0.0279 | $1.67 |
| R1 | 0 Ω 0805 | [C17477](https://www.lcsc.com/product-detail/C17477.html) | Basic | 1 | 100 | $0.0045 | $0.45 |
| R2 | 51 Ω 0603 (schematic says 60R; see note) | [C23197](https://www.lcsc.com/product-detail/C23197.html) | Basic | 1 | 100 | $0.0017 | $0.17 |
| D1 | Red LED 0603 | [C2286](https://www.lcsc.com/product-detail/C2286.html) | Basic | 1 | 100 | $0.0077 | $0.77 |
| J1 | 1×3 2.54 mm header (UPDI) | [C124376](https://www.lcsc.com/product-detail/C124376.html) | Extended | 1 | 60 | $0.0345 | $2.07 |
| J3 | JST-XH B5B-XH-A, 5-pin (stepper) | [C157991](https://www.lcsc.com/product-detail/C157991.html) | Extended | 1 | 50 | $0.0703 | $3.52 |
| J4 | JST-PH B3B-PH-K, 3-pin 2.0 mm (Hall sensor) | [C131339](https://www.lcsc.com/product-detail/C131339.html) | Extended | 1 | 50 | $0.042 | $2.10 |
| J5 | 1×5 2.54 mm header (IO breakout), **optional, leave unpopulated** | [C124379](https://www.lcsc.com/product-detail/C124379.html) | Extended | – | – | $0.0559 | ($2.80) |
| J2, J6, J7, J8 | Pogo-pin pads (+VBUS, GND, A, B). The pins are hand-soldered and counted in §3 | – | – | – | – | – | – |
| | **Components** (+ ~3% JLC attrition) | | | | | | **≈ $119** |

**JLCPCB order estimate.** Fee rates were read from the [JLC fee page](https://jlcpcb.com/help/article/pcb-assembly-price) (LIVE). The bare board price, shipping and tariff are estimates.

| Item | Cost |
|---|---|
| Bare PCB, 50 pcs (EST) | ≈ $8 |
| Economic setup + stencil | $9.71 |
| Extended-part loading (8 × $3.07) | $24.56 |
| SMT joints (~79/board) + through-hole joints (11/board) + hand-solder labor | $18.92 |
| Components | ≈ $119 |
| US tariff, ~35% pre-collected on DDP orders (EST) | ≈ $63 |
| Shipping, Global Standard / DHL (EST) | ≈ $20 |
| **Total (≈ $5.90 per needed board)** | **≈ $264** |

Notes:
- **R2 has no Basic 60 Ω part.** 51 Ω (C23197) or 47 Ω (C23182) are Basic. An exact 62 Ω part would be Extended and add about $3. 51 Ω just makes the status LED slightly brighter.
- **U6 (C20617302) is low on stock:** 260 left. Order soon, or find an alternative 5 V SOT-23-5 LDO.
- **The old BOM was wrong in three places:**
  - It listed D1 and R2 as 0201. They're 0603 on this board. The 0201 parts would also have forced the more expensive Standard PCBA.
  - It listed J4 as a 2.54 mm header. It's a JST-PH 2.0 mm connector, so the Hall sensor cable in §3 needs a JST-PH 3-pin plug.
  - It didn't list J1 or J5.
- **The KiCad schematic has no LCSC part-number fields.** Add them, or map the parts in JLC's BOM tool, using the numbers above.

## 2. Bus board

Adam G's `SplitFlapBusBoard` (5-module variant) is a 202 × 24 mm bare 2-layer PCB carrying the
conductor rail for +12 V, GND, A and B. You need 3 per row, so 9 total; order 10.

| Item | Link | Qty | Unit | Ext | Price |
|---|---|---|---|---|---|
| Bare PCB, 202 × 24 mm, 2-layer, 1.6 mm (add it to the driver-board order) | [JLCPCB quote](https://jlcpcb.com/quote) | 10 | ≈ $1.00 | ≈ $10 | EST |
| 1×4 2.54 mm male header (J1 on each board) | [LCSC C124378](https://www.lcsc.com/product-detail/C124378.html) | 10 | $0.0565 | $0.57 | LIVE |
| Extra shipping + tariff when combined with §1 | – | – | – | ≈ $7.43 | EST |
| **Subtotal** | | | | **≈ $18** | |

## 3. Module hardware (45 modules)

| Part | Qty/module | Need | Product | Pack | Packs | $/pack | Ext | Price |
|---|---|---|---|---|---|---|---|---|
| M3 hex nut | 12 | 540 | [300 pcs M3 hex nuts, 304 SS](https://www.amazon.com/dp/B0DM1JHK1D) | 300 | 2 | $6.88 | $13.76 | LIVE |
| M3 × 8 mm flat head | 4 | 180 | [KADRICK M3×8 countersunk, 300 pcs](https://www.amazon.com/dp/B0H1CKZ7PS) | 300 | 1 | $9.99 | $9.99 | LIVE |
| M3 × 30 mm flat head | 4 | 180 | [KADRICK M3×30 countersunk, 200 pcs](https://www.amazon.com/dp/B0H1CMJY7Q) | 200 | 1 | $9.99 | $9.99 | LIVE |
| M3 × 40 mm flat head | 4 | 180 | [KADRICK M3×40 countersunk, 170 pcs](https://www.amazon.com/dp/B0H1CTDXTB) | 170 | 1 | $9.99 | $9.99 | LIVE |
| M3 × 40 mm (top-up, 10 short) | – | 10 | [iexcell M3×40, 50 pcs](https://www.amazon.com/dp/B0GRB2DW2T). Confirm it's flat head, or buy a 2nd KADRICK pack (+$4) | 50 | 1 | $5.98 | $5.98 | LIVE |
| A3144 Hall sensor | 1 | 45 | [A3144, 30 pcs](https://www.amazon.com/dp/B0DQ4GV916) | 30 | 2 | $6.88 | $13.76 | LIVE |
| 28BYJ-48 stepper, **12 V** | 1 | 45 | [28BYJ-48 + ULN2003 board, 10 sets](https://www.amazon.com/dp/B0D4WS7MR6). **Select the 12 V option**; the ULN2003 boards go unused | 10 | 5 | $24.00 | $120.00 | LIVE |
| Pogo pin, 9 mm (2.0 mm head, 5.0 mm tube, 1.0 mm tail) | 4 | 184 (180 + 4 for the gateway) | [Yibuy 2 mm gold pogo pins, 100 pcs](https://www.amazon.com/dp/B07FPKKK9W). This is the designer's listing | 100 | 2 | $12.99 | $25.98 | LIVE |
| 3 × 1 mm N52 magnet | 1 | 45 | [N52 D3×1 mm, 1000 pcs](https://www.amazon.com/dp/B0F4CD3GC1). Cheaper packs don't state the grade | 1000 | 1 | $21.59 | $21.59 | LIVE |
| Hall sensor cable, 3-pin | 1 | 45 | [JST 3-pin pigtails, 60 pairs](https://www.amazon.com/dp/B0F6T5CJ2T). ⚠ This listing is JST-**XH** 2.54 mm, but J4 is JST-**PH** 2.0 mm. Buy a JST-PH 3-pin pigtail pack instead (similar price) | 60 | 1 | $11.99 | $11.99 | LIVE |
| 35 mm DIN rail, 1 m (cut to ~600 mm per row) | – | 3 | [Slotted steel DIN rail, 1 m](https://www.amazon.com/dp/B019Q9E86W) | 1 | 3 | $7.95 | $23.85 | LIVE |
| **Subtotal** (incl. §4) | | | | | | | **$286.65** | |

## 4. Programming (UPDI flasher)

See `../gateway/SplitFlapUniversalFirmware/FLASHER.md`. Solder the diode across TXD/RXD on one
adapter, with the band at TXD.

| Part | Product | Qty | Price | Status |
|---|---|---|---|---|
| CH340 USB-TTL adapter | [HiLetgo CH340, 5 pcs](https://www.amazon.com/dp/B00LZV1G6K) | 1 pack | $9.79 | LIVE |
| 1N5817 Schottky diode | [BOJACK 1N5817, 125 pcs](https://www.amazon.com/dp/B07Q5H1SLY) | 1 pack | $5.99 | LIVE |
| F-M jumper wires | [40 pcs 20 cm Dupont F-M](https://www.amazon.com/dp/B0BRTHR2RL) | 1 pack | $3.99 | LIVE |

These are included in the §3 subtotal.

## 5. Gateway & RS-485 bus

The gateway clips onto the DIN rail in its printed case (`SplitFlapGatewayCase.3mf`) and takes
12 V plus the bus from the conductor rail through 4 pogo pins (counted in §3). It also needs a few
cm of thin wire and superglue.

| Item | Link | Qty | Unit | Ext | Price |
|---|---|---|---|---|---|
| Waveshare ESP32-S3-RS485-CAN | [waveshare.com](https://www.waveshare.com/esp32-s3-rs485-can.htm) (also on [Amazon](https://www.amazon.com/dp/B0FNCWZ3D1)) | 1 | $18.99 | $18.99 | LIVE |
| Resistor kit, 1/4 W, 500 pcs (includes 330 Ω for the LED strip) | [SparkFun](https://www.sparkfun.com/resistor-kit-1-4w-500-total.html) | 1 | $9.95 | $9.95 | LIVE |
| 120 Ω 1/4 W, bus termination | [Vetco](https://vetco.net/products/nte-qw112_120_ohm_1-4_watt_resistor) | 2 | $0.29 | $0.58 | LIVE |
| 10 ft Cat-6 cable. Cut it and use one twisted pair for A/B between rows | [Vetco](https://vetco.net/products/cat-6_ethernet_cable_10_ft) | 1 | $6.49 | $6.49 | LIVE |
| **Subtotal** | | | | **$36.01** | |

## 6. Power

**Load estimate:**
- 45 steppers: about 7 A
- WS2815 strip: 6–8 A at full white, much less at the capped brightness
- Gateway: under 1 A

That comes to about 16 A peak. The 29 A PSU leaves headroom.

| Item | Link | Qty | Unit | Ext | Price |
|---|---|---|---|---|---|
| Mean Well LRS-350-12 (12 V, 29 A) | [Bravo Electro](https://www.bravoelectro.com/lrs-350-12.html) | 1 | $33.30 | $33.30 | LIVE |
| C14 inlet with fuse holder and switch, 10 A (no separate switch needed) | [Amazon B00F4MFMXE](https://www.amazon.com/dp/B00F4MFMXE) | 1 | ≈ $8 | $8.00 | EST |
| 3.15 A 5×20 mm slow-blow fuse, 5 pcs | [Vetco](https://vetco.net/products/3-15amp5x20s_3-15_amp_5x20mm_slow_blow_fuse_5pk) | 1 | $7.50 | $7.50 | LIVE |
| IEC C13 power cord, 6 ft, 18/3 | [Vetco](https://vetco.net/products/6-iec-power-cord-18-3-awg-black) | 1 | $5.95 | $5.95 | LIVE |
| 18 AWG red/black zip cord (sold per ft; 25 ft may be enough, which halves this) | [Vetco](https://vetco.net/products/jsc-2440_18_awg_2_conductor_red-black_speaker_wire_-_power_wire_-usa_made) | 50 ft | $1.05/ft | $52.50 | LIVE |
| WAGO 221 combo kit, 40 pcs | [Home Depot](https://www.homedepot.com/p/WAGO-221-Lever-Nut-Combo-Kit-40-pack-887-0408/336511597) | 1 | $29.97 | $29.97 | SNIP |
| *Optional:* ferrule crimp kit with 1800 ferrules | [Vetco](https://vetco.net/products/vupn1576_ferrule_wire_crimping_tool_kit_with_1800pcs) | (1) | $39.95 | – | LIVE |
| *Alternative:* separate SPST rocker switch | [Vetco](https://vetco.net/products/ces-66-2200_spst_snap-in_illuminated_rocker_switch_on-off_20a_120vac_amber) | (1) | $2.99 | – | LIVE |
| **Subtotal** | | | | **$137.22** | |

## 7. LED perimeter strip

WS2815 12 V, 144 LED/m, about 3 m around the perimeter. Data comes from GPIO2 through a
74AHCT125 and a 330 Ω resistor. The strip is powered straight from the PSU and injected at both
ends. Details are in `../gateway/CLAUDE.md`, Phase 2.

| Item | Link | Qty | Unit | Ext | Price |
|---|---|---|---|---|---|
| WS2815 12 V 144 LED/m, IP20, 3 m option | [SuperLightingLED](https://www.superlightingled.com/dc12v-ws2815-upgraded-ws2812b-1m-144-leds-individually-addressable-digital-led-strip-lights-dual-signal-wires-waterproof-dream-color-programmable-5050-rgb-flexible-led-ribbon-light-p-2134.html) | 1 | $36.98 | $36.98 | LIVE |
| *Alternative:* BTF-LIGHTING WS2815 144/m, 1 m (buy 3) | [Amazon B07LG6J39V](https://www.amazon.com/dp/B07LG6J39V) | (3) | ≈ $19.94 | (≈ $59.82) | SNIP |
| SN74AHCT125N level shifter, DIP-14 | [LCSC C354152](https://www.lcsc.com/product-detail/C354152.html) (ships with the JLC order) | 2 | $0.693 | $1.39 | LIVE |
| Adjustable buck module, 2 A (set to 5.0 V for the 74AHCT125) | [Vetco D93](https://vetco.net/products/vupn7407_dc-dc_adjustable_step-down_voltage_regulator_module-_1-5-35vdc_output__2a_d93) | 1 | $6.95 | $6.95 | LIVE |
| 1000 µF 25 V electrolytic | [Vetco](https://vetco.net/products/1000uf25vdc_1000uf_25_volt_electrolytic_capacitor) | 2 | $2.85 | $5.70 | LIVE |
| Perma-Proto half-size, 3 pcs | [Adafruit #571](https://www.adafruit.com/product/571) | 1 | $12.50 | $12.50 | LIVE |
| 330 Ω resistor | from the §5 resistor kit | – | – | $0 | – |
| **Subtotal** | | | | **$63.52** | |

## 8. Raspberry Pi + voice satellite

This is the partner's side: Home Assistant, the Assist satellite, the LLM and the Companion app.
The USB-RS485 dongle in the original Adam G BOM is **not needed**, because the gateway replaces it.

| Item | Link | Qty | Unit | Ext | Price |
|---|---|---|---|---|---|
| Raspberry Pi 5 4GB ([8GB is $200](https://www.adafruit.com/product/5813)) | [Adafruit #5812](https://www.adafruit.com/product/5812) | 1 | $130.00 | $130.00 | LIVE |
| Official 27 W USB-C PSU | [Adafruit #5814](https://www.adafruit.com/product/5814) | 1 | $14.04 | $14.04 | LIVE |
| Official Pi 5 case + fan | [Adafruit #5816](https://www.adafruit.com/product/5816) | 1 | $12.00 | $12.00 | LIVE |
| SanDisk High Endurance microSD, 32 GB | [PiShop.us](https://www.pishop.us/product/sandisk-high-endurance-microsdhc-card-32gb-blank/) | 1 | $29.95 | $29.95 | LIVE |
| Seeed ReSpeaker Lite (USB 2-mic array) | [Seeed](https://www.seeedstudio.com/ReSpeaker-Lite-p-5928.html) | 1 | $24.90 | $24.90 | LIVE |
| Speaker, 3 W 4 Ω, JST-PH 2.0 (currently out of stock; [Seeed 5 W alternative](https://openelab.com/products/seeed-studio-mono-enclosed-speaker), $4.18) | [Adafruit #3351](https://www.adafruit.com/product/3351) | 1 | $3.95 | $3.95 | LIVE |
| **Subtotal** | | | | **$214.84** | |

Pi prices are high in 2026 because of the RAM shortage.

## 9. 3D-printed parts (not priced)

| Part | Qty/module | Qty (45 modules) |
|---|---|---|
| Enclosure Body | 1 | 45 |
| Enclosure Right Cover | 1 | 45 |
| Enclosure Left Cover | 1 | 45 |
| Drum Body | 1 | 45 |
| Drum Cap | 1 | 45 |
| DIN Rail Mount | 1 | 45 |
| Motor Gear | 1 | 45 |
| Center Gear | 1 | 45 |
| Gear Plate | 1 | 45 |
| Wire Retainer | 1 | 45 |
| Flap | 64 | 2880 |
| Gateway case (base + shell, `SplitFlapGatewayCase.3mf`) | – | 1 |
