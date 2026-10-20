# Split-Flap Wall BOM (Bill of Materials)

A 3 × 15 (45-module) split-flap wall: Adam G Makes modules on Kevin's ATtiny1616 driver board, an
ESP32-S3 RS-485 gateway, a WS2815 LED perimeter strip, and a Raspberry Pi running Home Assistant
with a "Hey Venus" voice satellite. See `../gateway/CLAUDE.md` for the full project plan.

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
| [3. Module hardware (45 modules)](#3-module-hardware-45-modules) | $237.66 |
| [4. Programming (UPDI flasher)](#4-programming-updi-flasher) | incl. above |
| [5. Gateway & RS-485 bus](#5-gateway--rs-485-bus) | $18.99 |
| [6. Power](#6-power) | $60.64 |
| [7. LED perimeter strip](#7-led-perimeter-strip) | $38.37 |
| [9. Case (plywood back, laser-cut acrylic)](#9-case) | ≈ $70.12 |
| **Wall total (Kevin's hardware side)** | **≈ $707.78** |
| [8. Raspberry Pi + voice satellite (software side)](#8-raspberry-pi--voice-satellite) | $218.53 |
| **Grand total** | **≈ $926** |

Realistic all-in budget: **≈ $970–995**. The proposal asks for $950; the savings checks (Pi, IEC cord/fuses) cover the gap.
- The total above already includes shipping and tariffs for JLCPCB and Elecrow.
- Add roughly $45–70 for shipping from the other stores: Vetco, Adafruit, Seeed, Bravo Electro, Waveshare and Laser by the Creek. Amazon is usually free over $35 or with Prime; Home Depot is store pickup.
- The JLCPCB estimates can still move ±$20.

Owned parts are listed with **Already have** and count as $0.

Optional add-ons, not in the total:
- Ferrule crimp kit: +$39.95
- Pi 5 8GB instead of 4GB: +$70
- J5 header populated: +$14

3D-printed parts are not priced; see [section 10](#10-3d-printed-parts-not-priced).

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
| 28BYJ-48 stepper, **12 V** | 1 | 45 (+5 spare) | [Elecrow 28BYJ-48 12 V](https://www.elecrow.com/28byj48-high-quality-stepper-motor-12v-p-784.html). Ships from China; check the cart for real shipping and confirm the 5-pin JST-XH plug | 1 | 50 | $1.00 | $50.00 | LIVE |
| ↳ Elecrow shipping (~2.2 kg) + possible tariff | – | – | – | – | – | – | ≈ $25.00 | EST |
| *Alternative:* 28BYJ-48 12 V + ULN2003, 10 sets | – | – | [Amazon](https://www.amazon.com/dp/B0D4WS7MR6), select the 12 V option | 10 | (5) | $24.00 | ($120.00) | LIVE |
| Pogo pin, 9 mm (2.0 mm head, 5.0 mm tube, 1.0 mm tail) | 4 | 184 (180 + 4 for the gateway) | [Yibuy 2 mm gold pogo pins, 100 pcs](https://www.amazon.com/dp/B07FPKKK9W). This is the designer's listing | 100 | 2 | $12.99 | $25.98 | LIVE |
| 3 × 1 mm N52 magnet | 1 | 45 | [N52 D3×1 mm, 1000 pcs](https://www.amazon.com/dp/B0F4CD3GC1). Cheaper packs don't state the grade | 1000 | 1 | $21.59 | $21.59 | LIVE |
| Hall sensor cable, 3-pin | 1 | 45 | [JST 3-pin pigtails, 60 pairs](https://www.amazon.com/dp/B0F6T5CJ2T). ⚠ This listing is JST-**XH** 2.54 mm, but J4 is JST-**PH** 2.0 mm. Buy a JST-PH 3-pin pigtail pack instead (similar price) | 60 | 1 | $11.99 | $11.99 | LIVE |
| 35 mm DIN rail, 1 m (cut to ~600 mm per row) | – | 3 | [Slotted steel DIN rail, 1 m](https://www.amazon.com/dp/B019Q9E86W) | 1 | 3 | $7.95 | $23.85 | LIVE |
| **Subtotal** (incl. §4) | | | | | | | **$237.66** | |

## 4. Programming (UPDI flasher)

See `../gateway/SplitFlapUniversalFirmware/FLASHER.md`. Solder the diode across TXD/RXD on one
adapter, with the band at TXD.

| Part | Product | Qty | Price | Status |
|---|---|---|---|---|
| CH340 USB-TTL adapter | [HiLetgo CH340, 5 pcs](https://www.amazon.com/dp/B00LZV1G6K) | 1 pack | $9.79 | LIVE |
| 1N5817 Schottky diode | [BOJACK 1N5817, 125 pcs](https://www.amazon.com/dp/B07Q5H1SLY) | 1 pack | $5.99 | LIVE |
| F-M jumper wires | [40 pcs 20 cm Dupont F-M](https://www.amazon.com/dp/B0BRTHR2RL) ($3.99) | 1 pack | $0 | **Already have** |

These are included in the §3 subtotal.

## 5. Gateway & RS-485 bus

The gateway clips onto the DIN rail in its printed case (`SplitFlapGatewayCase.3mf`) and takes
12 V plus the bus from the conductor rail through 4 pogo pins (counted in §3). It also needs a few
cm of thin wire and superglue.

| Item | Link | Qty | Unit | Ext | Price |
|---|---|---|---|---|---|
| Waveshare ESP32-S3-RS485-CAN | [waveshare.com](https://www.waveshare.com/esp32-s3-rs485-can.htm) (also on [Amazon](https://www.amazon.com/dp/B0FNCWZ3D1)) | 1 | $18.99 | $18.99 | LIVE |
| Resistors: 330 Ω (LED data line) and 120 Ω (bus termination). Make sure you have both values | [SparkFun kit](https://www.sparkfun.com/resistor-kit-1-4w-500-total.html) ($9.95) / [Vetco 120 Ω](https://vetco.net/products/nte-qw112_120_ohm_1-4_watt_resistor) ($0.29) | 1 + 2 | – | $0 | **Already have** |
| Twisted pair for RS-485 A/B between rows, ~2–3 m (self-made) | [Vetco Cat-6](https://vetco.net/products/cat-6_ethernet_cable_10_ft) ($6.49) | 1 | – | $0 | **Already have** |
| **Subtotal** | | | | **$18.99** | |

## 6. Power

**Load estimate:**
- 45 steppers: about 7 A
- WS2815 strip: 6–8 A at full white, much less at the capped brightness
- Gateway: under 1 A

That comes to about 16 A peak. The 29 A PSU leaves headroom.

| Item | Link | Qty | Unit | Ext | Price |
|---|---|---|---|---|---|
| Mean Well LRS-350-12 (12 V, 29 A) | [Bravo Electro](https://www.bravoelectro.com/lrs-350-12.html) | 1 | $33.30 | $33.30 | LIVE |
| C14 inlet with fuse holder and **black** rocker switch, 10 A 250 V, 3-pack with 18 AWG leads (no separate switch needed). If it ships with a 10 A fuse, replace it with the 4 A slow-blow below | [Amazon B0GYWP9JJ2](https://www.amazon.com/dp/B0GYWP9JJ2) | 1 pack | $13.89 | $13.89 | User-checked |
| 5×20 mm slow-blow fuse, 5 pcs (goes in the C14 inlet's fuse drawer). **Pick the 4 A pack**, same price; 3.15 A is tight | [Vetco](https://vetco.net/products/3-15amp5x20s_3-15_amp_5x20mm_slow_blow_fuse_5pk) | 1 | $7.50 | $7.50 | LIVE |
| IEC C13 power cord, 6 ft, 18/3 | [Vetco](https://vetco.net/products/6-iec-power-cord-18-3-awg-black) | 1 | $5.95 | $5.95 | LIVE |
| 18 AWG red/black wire for 12 V runs. About 15 ft: PSU → 3 bus rows + both strip ends | [Vetco](https://vetco.net/products/jsc-2440_18_awg_2_conductor_red-black_speaker_wire_-_power_wire_-usa_made) ($1.05/ft) | ~15 ft | – | $0 | **Already have** |
| Mains wire, C14 inlet → PSU (L, N, earth). **Must be mains-rated 3-wire:** cut ~30 cm from an old IEC or extension cord. Earth goes to the PSU's FG terminal | old cord | ~30 cm | – | $0 | **Already have** |
| WAGO 221 lever connectors | [Home Depot](https://www.homedepot.com/p/WAGO-221-Lever-Nut-Combo-Kit-40-pack-887-0408/336511597) ($29.97 / 40) | a few | – | $0 | **Already have** |
| Heat-shrink tubing | – | – | – | $0 | **Already have** |
| *Optional:* ferrule crimp kit with 1800 ferrules | [Vetco](https://vetco.net/products/vupn1576_ferrule_wire_crimping_tool_kit_with_1800pcs) | (1) | $39.95 | – | LIVE |
| *Alternative:* separate SPST rocker switch | [Vetco](https://vetco.net/products/ces-66-2200_spst_snap-in_illuminated_rocker_switch_on-off_20a_120vac_amber) | (1) | $2.99 | – | LIVE |
| **Subtotal** | | | | **$60.64** | |

## 7. LED perimeter strip

WS2815 12 V, 144 LED/m, about 3 m around the perimeter. Data comes from GPIO2 through a
74AHCT125 and a 330 Ω resistor. The strip is powered straight from the PSU and injected at both
ends. Details are in `../gateway/CLAUDE.md`, Phase 2.

| Item | Link | Qty | Unit | Ext | Price |
|---|---|---|---|---|---|
| WS2815 12 V 144 LED/m, IP20, 3 m option | [SuperLightingLED](https://www.superlightingled.com/dc12v-ws2815-upgraded-ws2812b-1m-144-leds-individually-addressable-digital-led-strip-lights-dual-signal-wires-waterproof-dream-color-programmable-5050-rgb-flexible-led-ribbon-light-p-2134.html) | 1 | $36.98 | $36.98 | LIVE |
| *Alternative:* BTF-LIGHTING WS2815 144/m, 1 m (buy 3) | [Amazon B07LG6J39V](https://www.amazon.com/dp/B07LG6J39V) | (3) | ≈ $19.94 | (≈ $59.82) | SNIP |
| SN74AHCT125N level shifter, DIP-14 | [LCSC C354152](https://www.lcsc.com/product-detail/C354152.html) (ships with the JLC order) | 2 | $0.693 | $1.39 | LIVE |
| 330 Ω resistor | from the §5 resistor kit | – | – | $0 | – |
| 12 V → 5 V buck converter (for the 74AHCT125). Set and check it at 5.0 V before connecting | [Vetco D93](https://vetco.net/products/vupn7407_dc-dc_adjustable_step-down_voltage_regulator_module-_1-5-35vdc_output__2a_d93) ($6.95) | 1 | – | $0 | **Already have** |
| 1000 µF capacitor, ≥16 V (across the strip's power input) | [Vetco](https://vetco.net/products/1000uf25vdc_1000uf_25_volt_electrolytic_capacitor) ($2.85 ea) | 1–2 | – | $0 | **Already have** |
| Perfboard (for the level shifter) | [Adafruit #571](https://www.adafruit.com/product/571) ($12.50 / 3) | 1 | – | $0 | **Already have** |
| **Subtotal** | | | | **$38.37** | |

Strip length: the strip runs around the inside of the case's side panels (§9). The case is about 880 × 280 mm, so that's about 2.3 m. 3 m is bought to leave margin for the corners and mounting.

## 8. Raspberry Pi + voice satellite

This is Jace's side: Home Assistant, the Assist satellite, the LLM and the Companion app.
The USB-RS485 dongle in the original Adam G BOM is **not needed**, because the gateway replaces it.

| Item | Link | Qty | Unit | Ext | Price |
|---|---|---|---|---|---|
| Raspberry Pi 5 4GB ([8GB is $200](https://www.adafruit.com/product/5813)) | [Adafruit #5812](https://www.adafruit.com/product/5812) | 1 | $130.00 | $130.00 | LIVE |
| Official 27 W USB-C PSU | [Adafruit #5814](https://www.adafruit.com/product/5814) | 1 | $14.04 | $14.04 | LIVE |
| Official Pi 5 Active Cooler. The Pi 5 throttles under sustained HA + voice load without one | [Adafruit #5815](https://www.adafruit.com/product/5815) | 1 | $13.50 | $13.50 | LIVE |
| Seeed ReSpeaker XVF3800 USB 4-Mic Array: 360° far-field pickup rated to 5 m, with beamforming, noise suppression and echo cancellation. Has a 3.5 mm out and a 5 W JST speaker amp. Buy the USB version, not the XIAO version | [Seeed](https://www.seeedstudio.com/ReSpeaker-XVF3800-USB-Mic-Array-p-6488.html) | 1 | $60.99 | $60.99 | LIVE |
| Pi 5 case. Leave an opening above the Active Cooler's fan | [Adafruit #5816](https://www.adafruit.com/product/5816) ($12.00) | 1 | – | $0 | **3D-printing own** |
| microSD, 32 GB or more, A1/A2, ideally an endurance card (HA writes constantly) | [PiShop.us SanDisk High Endurance](https://www.pishop.us/product/sandisk-high-endurance-microsdhc-card-32gb-blank/) ($29.95) | 1 | – | $0 | **Already have** |
| Speaker, 8 Ω (later, for spoken replies; see note) | [Adafruit #3351](https://www.adafruit.com/product/3351) ($3.95) | 1 | – | $0 | **Already have** |
| **Subtotal** | | | | **$218.53** | |

- **Speaker:** not needed now; the wall gives feedback through its LEDs. If spoken replies are added later:
  - Put a spare 8 Ω speaker next to the ReSpeaker on the floor, below the display.
  - Wire it to the ReSpeaker's JST speaker port, which has an onboard 5 W amp.
  - The ReSpeaker's 3.5 mm jack can feed a JBL. The Pi 5 has no 3.5 mm jack. Test whether plugging into the jack mutes the JST speaker.
  - Nothing audio-related goes in the display.
  - Because the ReSpeaker plays the audio, its echo cancellation works.

Pi prices are high in 2026 because of the RAM shortage.

## 9. Case

The modules (606 × 240 mm) sit in the middle, with a bay on each side for the electronics. That makes the case about **880 × 280 × 95 mm** outside. The height is 240 mm of modules, plus about 15 mm above and below for the LED strip and its standoff, plus the two 3 mm panels.

- **Left bay (mains):** the PSU, mounted flat on the plywood (215 mm tall), plus the C14 inlet. All mains wiring stays in this bay.
- **Right bay (low voltage):** the gateway, on the top rail extended into the bay, plus the level-shifter board and buck converter.

How it goes together:
- **Back:** 1/4" plywood, cut to 880 × 280 mm. It carries the 3 DIN rails, the PSU and the bay electronics. It also has vent slots behind the PSU and the wall hangers.
- **Front:** 1/8" black acrylic, laser-cut in one piece. It has one window per module, sized from the module CAD, and a vent grille over the PSU's fan. It's held on with M3 countersunk screws into printed brackets, so it comes off for service.
- **Sides:** 1/8" black LED acrylic, about 95 mm deep. It looks matte black when the LEDs are off and passes about 29% of their light, in the LEDs' own colour. The WS2815 strip sits on printed clips about 10 mm inside the panels so the LEDs blend instead of showing as dots. The C14 inlet goes through the left end panel.
- **Joints:** printed corner brackets plus M3 screws and nuts left over from §3, which has about 120 spare M3×8 screws and 60 spare nuts.
- **Laser bed:** the front and back each need a bed of at least about 900 × 290 mm. The 18 × 36" front sheet fits whole on a 36 × 24" bed; on a smaller bed, trim it to about 290 mm tall on a table saw first.

| Item | Link | Qty | Unit | Ext | Price |
|---|---|---|---|---|---|
| 1/4" × 2 × 4 ft sanded plywood (back). If it's laser-cut, birch cuts cleaner than pine | [Home Depot 203438872](https://homedepot.com/p/1-4-in-x-2-ft-x-4-ft-Pine-Sanded-Plywood-1502100/203438872) | 1 | $11.22 | $11.22 | SNIP |
| 1/8" black acrylic, 18 × 36" (front: 880 × 280 in 914 × 457, which leaves room for a border or a taller case). The price is an estimate scaled by area between the 12 × 36" ($17.49) and 24 × 36" ($40.92) sheets; check the listing | [Amazon Falken Design B07NR99K5Z](https://www.amazon.com/dp/B07NR99K5Z) | 1 | ≈ $29.00 | ≈ $29.00 | EST |
| *Alternative:* 24 × 36" of the same sheet, if 18 × 36" is out of stock | [Home Depot 308669314](https://www.homedepot.com/p/Falken-Design-24-in-x-36-in-x-1-8-in-Thick-Acrylic-Black-Opaque-Sheet-Falken-Design-ACRYLIC-BK-1-8-2436/308669314) | (1) | $40.92 | (+$11.92) | SNIP |
| 1/8" black LED cast acrylic, 12 × 18" (sides). Two sheets give six 95 mm strips: the top and bottom are two strips each, joined at the centre, plus the two end panels | [Laser by the Creek](https://laseredbythecreek.com/products/1-8-black-led-cast-acrylic-sheets-matte-gloss-finish) | 2 | $14.95 | $29.90 | LIVE |
| *Alternative:* the same material in 24 × 36", for seamless top and bottom strips | same listing | (1) | $59.95 | (+$30.05) | LIVE |
| M3 screws and nuts for the brackets and front panel | spares from §3 | ~24 | – | $0 | **Already have** |
| **Subtotal** | | | | **≈ $70.12** | |

## 10. 3D-printed parts (not priced)

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
| Case corner brackets (side ↔ back and side ↔ front), front-panel screw brackets, top/bottom strip splices, LED strip clips, wall hangers (to design) | – | ~30 |
