# Split-Flap Wall BOM (Bill of Materials)

A 3 × 15 (45-module) split-flap wall: Adam G Makes modules on Kevin's ATtiny1616 driver board, an
ESP32-S3 RS-485 gateway, a WS2815 LED perimeter strip, and a Raspberry Pi running Home Assistant
with a "Hey Venus" voice satellite. See `../gateway/CLAUDE.md` for the full project plan.

**Prices checked 2026-10-19 (JLCPCB driver + bus board quote 2026-10-27, not yet ordered; power supply 2026-10-27), in USD, before sales tax and shipping unless a row says otherwise.**
The *Price* column marks where each number came from:
- **LIVE**: read from the product page.
- **SNIP**: taken from a search-result snippet, because the store blocked page loads.
- **EST**: an estimate.

Pack prices are rounded up to whole packs.

## Cost summary

| Section | Cost |
|---|---|
| [1. Driver PCBs V5, assembled by JLCPCB (50 boards)](#1-driver-pcb-jlcpcb-assembled) | $327.23 |
| [2. Bus boards (15 bare PCBs, same JLCPCB order)](#2-bus-board) | $21.52 |
| ↳ *JLCPCB quote for §1 + §2 together* | *$348.75* |
| [3. Module hardware (45 modules)](#3-module-hardware-45-modules) | $237.66 |
| [4. Programming (UPDI flasher)](#4-programming-updi-flasher) | incl. above |
| [5. Gateway & RS-485 bus](#5-gateway--rs-485-bus) | $18.99 |
| [6. Power](#6-power) | $62.10 |
| [7. LED perimeter strip](#7-led-perimeter-strip) | $38.37 |
| [9. Case (plywood back, laser-cut acrylic)](#9-case) | ≈ $70.12 |
| **Wall total (Kevin's hardware side)** | **≈ $775.99** |
| [8. Raspberry Pi + voice satellite (software side)](#8-raspberry-pi--voice-satellite) | $224.43 |
| **Grand total** | **≈ $1,000** |

Realistic all-in budget: **≈ $1,045–1,070**, about $95–120 over the $950 the proposal asks for.
- The total above already includes shipping and tariffs for JLCPCB (the full checkout quote) and Elecrow.
- Add roughly $45–70 for shipping from the other stores: Vetco, Adafruit, Seeed, Jameco, DigiKey, Waveshare and Laser by the Creek. Amazon is usually free over $35 or with Prime; Home Depot is store pickup.

Owned parts are listed with **Already have** and count as $0.

Optional add-ons, not in the total:
- Ferrule crimp kit: +$39.95
- Pi 5 8GB instead of 4GB: +$70
- J5 header populated: +$14

3D-printed parts are not priced; see [section 10](#10-3d-printed-parts-not-priced).

---

## 1. Driver PCB (JLCPCB assembled)

Source: `PCBs/Driverv5/SplitFlapDriverV5.kicad_pcb.kicad_pcb` (driver board **V5**). The board is 30 × 60 mm, 2-layer, 1.6 mm.

The order is 50 boards (45 needed plus 5 spares) using JLCPCB **Economic PCBA**, top side only.
JLCPCB solders the two through-hole connectors (J3, J4) too. Parts marked DNP are left off the
BOM and CPL and are fitted by hand.

| Ref | Part | LCSC | JLC lib | Qty/board | Order qty |
|---|---|---|---|---|---|
| U1 | ATtiny1616-MNR (VQFN-20, 3 × 3 mm) | [C507118](https://www.lcsc.com/product-detail/C507118.html) | Extended | 1 | 50 |
| U2 | TI ULN2003ADR (SOIC-16, 3.9 mm narrow body) | [C7512](https://www.lcsc.com/product-detail/C7512.html) | Basic | 1 | 50 |
| U3 | TI SN65HVD72DR RS-485 (SOIC-8, 3.9 mm narrow body) | [C48125](https://www.lcsc.com/product-detail/C48125.html) | Extended | 1 | 50 |
| U5 | MaxLinear SPX3819M5-L-3-3/TR, 3.3 V LDO (SOT-23-5) | [C9055](https://www.lcsc.com/product-detail/C9055.html) | Extended | 1 | 50 |
| U6 | MaxLinear SPX3819M5-L-5-0/TR, 5 V LDO (SOT-23-5) | [C13417](https://www.lcsc.com/product-detail/C13417.html) | Extended | 1 | 50 |
| F1 | Ruilon SMD1812P075TF/24 resettable fuse: 750 mA hold, 1.5 A trip, 24 V (1812) | [C12557](https://www.lcsc.com/product-detail/C12557.html) | Extended | 1 | 50 |
| D3 | MDD SS34 Schottky, 40 V 3 A (SMA), reverse-polarity protection | [C8678](https://www.lcsc.com/product-detail/C8678.html) | Basic | 1 | 50 |
| C1 | KNSCHA 100 µF 25 V electrolytic (6.3 × 5.4 mm) | [C4747964](https://www.lcsc.com/product-detail/C4747964.html) | Extended | 1 | 50 |
| C2, C3, C6, C8 | Samsung 470 nF 25 V X7R 0603 | [C1623](https://www.lcsc.com/product-detail/C1623.html) | Basic | 4 | 200 |
| C4 | Samsung 10 µF 25 V X5R 0805 (12 V rail) | [C15850](https://www.lcsc.com/product-detail/C15850.html) | Basic | 1 | 50 |
| C5, C9 | Samsung 10 µF 10 V X5R 0603 (3.3 V / 5 V rails) | [C19702](https://www.lcsc.com/product-detail/C19702.html) | Basic | 2 | 100 |
| C7, C10, C11 | Yageo 100 nF 50 V X7R 0603 | [C14663](https://www.lcsc.com/product-detail/C14663.html) | Basic | 3 | 150 |
| R2 | 470 Ω 0603 (status LED) | [C23179](https://www.lcsc.com/product-detail/C23179.html) | Basic | 1 | 50 |
| R3, R4 | 10 kΩ 0603 (R3: DE/RE pull-down; R4: RXD pull-up) | [C25804](https://www.lcsc.com/product-detail/C25804.html) | Basic | 2 | 100 |
| D1 | Red LED 0603 (KENTO KT-0603R) | [C2286](https://www.lcsc.com/product-detail/C2286.html) | Basic | 1 | 50 |
| J3 | JST-XH B5B-XH-A, 5-pin (stepper) | [C157991](https://www.lcsc.com/product-detail/C157991.html) | Extended | 1 | 50 |
| J4 | JST-PH B3B-PH-K-S, 3-pin 2.0 mm (Hall sensor) | [C131339](https://www.lcsc.com/product-detail/C131339.html) | Extended | 1 | 50 |
| J1 | 1×3 2.54 mm UPDI header, **DNP**: program through a temporary header or pogo clip | – | – | – | – |
| J5 | 1×5 2.54 mm IO breakout header, **DNP** | – | – | – | – |
| J2, J6, J7, J8 | Pogo-pin pads (+VBUS, GND, A, B), **DNP**. The pins are hand-soldered and counted in §3 | – | – | – | – |

**JLCPCB order, driver boards alone (quote 2026-10-25), not yet placed.** The checkout quote with
the §2 bus boards added comes to **$348.75**.

| Item | Cost |
|---|---|
| Boards, parts, assembly and Extended-part fees, 50 assembled boards | $205.12 |
| Customs and duties | $71.80 |
| Shipping | $45.00 |
| Other checkout fees (the difference between the line items and the quoted checkout total) | $5.31 |
| **Total (≈ $7.27 per needed board)** | **$327.23** |

Notes:
- **Changes from V4:**
  - RS-485 moved to the ATtiny's hardware USART: TXD on PA1, RXD on PA2, DE/RE on PA4 (XDIR). The firmware must use `Serial.swap(1)`; firmware built for V4 (SoftwareSerial on PA5/PA6/PA7) won't talk on the bus.
  - U2 and U3 now use the narrow 3.9 mm SOIC footprints that match the parts JLCPCB places. V4 had 5.3 mm footprints.
  - Added F1 (polyfuse) and D3 (reverse-polarity diode) in the 12 V input, R3 (DE/RE pull-down), R4 (RXD pull-up), and C10/C11 (decoupling).
  - R1 (0 Ω link) removed. R2 changed to 470 Ω; the LED runs at about 3 mA.
  - PC0 is tied to GND as a board ID. With `INPUT_PULLUP` it reads LOW on V5 and HIGH on V4 (floating), so one firmware can pick the right serial pins at boot. Never drive PC0 as an output.
- **8 Extended parts** (U1, U3, U5, U6, F1, C1, J3, J4), each with a JLC loading fee. These are included in the quote.
- **Motors must be the 12 V 28BYJ-48** (coils about 130–200 Ω). A 5 V motor (about 50 Ω) draws about 0.47 A per module on this board, overheats, and breaks the power budget. Measure one coil (red to any other wire) on every batch.
- **Check the stock column** when JLC matches the BOM, especially for the Extended parts.
- In JLC's assembly preview, check pin 1 on U1, U2, U3, U5 and U6, the polarity of C1, D1 and D3, and that J3 and J4 sit on their holes.

## 2. Bus board

Source: `PCBs/bus-board-5-module/` (Gerbers: `FAB/SplitFlapBusBoard-5module-202mm.zip`). This is
Adam G's 5-module bus board rebuilt in KiCad with the A/B labels fixed. It's a 202 × 24 mm bare
2-layer PCB with exposed copper strips for +12 V, B, A and GND on the front, where the module pogo
pins ride. A row of 15 modules is 15 × 40.4 mm = 606 mm, so each row uses 3 boards: 9 needed, 15 to order.

| Item | Link | Qty | Unit | Ext | Price |
|---|---|---|---|---|---|
| Bare PCB, 202 × 24 mm, 2-layer, 1.6 mm, ordered together with the §1 driver boards | JLCPCB | 15 | $0.753 | $11.30 | LIVE |
| Extra shipping, customs and fees from adding them to the §1 order ($348.75 − $327.23 − $11.30) | – | – | – | $10.22 | LIVE |
| **Subtotal** | | | | **$21.52** | |

Notes:
- **Labels:** Adam's original files print `12V / A / B / GND`. The strip next to 12 V actually meets
  the driver's **B** pin, so this version reads `12V / B / A / GND` (back silkscreen), and the nets
  match the driver board. Wire the gateway's A and B terminals to the strips by these labels.
- **Joining boards:** each end has 4 holes (1.0 mm), 2.54 mm in from the edge, so matching holes on
  two butted boards are 5.08 mm apart. Bridge each strip with a short wire, or a 3-pin 2.54 mm
  header with the middle pin pulled: 4 bridges per joint, 24 in total. Use **20 AWG** for 12 V and
  GND (the joint nearest the feed carries up to ~3.75 A); 18 AWG is too thick for the holes.
- Keep solder off the strip faces where the pogo pins slide, and wipe the strips with isopropyl
  alcohol before installing.
- `PCBs/bus-board/` holds a single-piece 606 mm version of the same board, not ordered: it would
  have cost about $41.18 for 5 boards.

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

An **external** 12 V brick: no mains wiring enters the case. The brick plugs into the wall, and its
DC cable plugs into a panel jack on the case.

**Load estimate:**
- 45 steppers: about 7 A typical, 9 A worst case (45 × ~0.2 A), only while flaps are moving. The firmware releases the coils after every move, so they draw nothing at rest.
- Driver logic and gateway: about 1.5 A.
- WS2815 strip: 6–8 A at full white uncapped. It runs straight off the switched 12 V, with no fuse.

**LED cap:** the gateway gives the strip whatever the motors leave, to keep the 15 A brick under 12 A (80%):

`LED cap = 10.5 A − 0.2 A × (modules moving)`, limited to the strip's ~7 A maximum

- 0–17 modules moving: no dimming; the strip can run at full white.
- All 45 moving: the cap drops to 1.5 A.
- The gateway counts a module as moving from the moment it sends that module a move. It lowers the cap *before* sending, and raises it only after the move's expected time has passed, so the LEDs and motors never briefly overlap.

**Calibrate the cap:** FastLED's `setMaxPowerInVoltsAndMilliamps` uses a power model for 5 V WS2812B LEDs, not WS2815. Measure the strip's current at full white and set the model with `setPowerModel()`, or the cap will be off.

**Voltage at the modules:** 12.0 V from the brick, minus about 0.1 V (typical) to 0.4 V (peak) in its DC cable, minus the 0.3 V drop of each driver's D3 Schottky diode. That leaves about **11.25–11.6 V**, which is fine: the ULN2003 already drops about 1 V, and the 5 V regulator needs only about 5.4 V. No boost converter is needed. Don't extend the brick's DC cable; if you need more reach, extend the AC side.

| Item | Link | Qty | Unit | Ext | Price |
|---|---|---|---|---|---|
| Mean Well OWA-200U-12: 12 V, 15 A, 180 W brick. Fully potted, IP67, fanless, Class II (no earth). US plug cord attached; 4-pin power DIN output plug (Kycon KPPX-4P or equivalent). 195 × 68 × 39.5 mm | [Jameco 2324383](https://www.jameco.com/z/OWA-200U-12-MEAN-WELL-12V-15A-180W-Moisture-proof-Power-Adaptor-DIN4_2324383.html) / [Bravo Electro](https://www.bravoelectro.com/owa-200u-12.html) ($61.80) | 1 | $59.50 | $59.50 | SNIP |
| Kycon KPJX-PM-4S-S: female 4-pin power DIN jack, panel mount, shielded. Mates with the brick's plug; it goes through the case side and is wired to the power board. **Before wiring, confirm which pins are +V and −V with a multimeter on the brick's plug** (two pins each) | [DigiKey 9990082](https://www.digikey.com/en/products/detail/kycon-inc/KPJX-PM-4S-S/9990082) | 1 | $2.60 | $2.60 | SNIP |
| 18 AWG red/black wire for 12 V runs. About 15 ft: jack → 3 bus rows + both strip ends + gateway. Keep the jack-to-distribution run short (under ~20 cm), since it carries the full current | [Vetco](https://vetco.net/products/jsc-2440_18_awg_2_conductor_red-black_speaker_wire_-_power_wire_-usa_made) ($1.05/ft) | ~15 ft | – | $0 | **Already have** |
| WAGO 221 lever connectors, for 12 V distribution until the power board replaces them | [Home Depot](https://www.homedepot.com/p/WAGO-221-Lever-Nut-Combo-Kit-40-pack-887-0408/336511597) ($29.97 / 40) | a few | – | $0 | **Already have** |
| Heat-shrink tubing | – | – | – | $0 | **Already have** |
| *Optional:* ferrule crimp kit with 1800 ferrules | [Vetco](https://vetco.net/products/vupn1576_ferrule_wire_crimping_tool_kit_with_1800pcs) | (1) | $39.95 | – | LIVE |
| **Subtotal** | | | | **$62.10** | |

Notes:
- **No power switch.** The brick has none, and the C14 inlet with its rocker switch is gone. Unplug the brick, or let the gateway blank the display; a 12 V switch can go on the power board later.
- **Protection:** the brick shuts down on a short, overload or overheating, and each driver has its own 1.5 A polyfuse (F1). Per-branch fuses are planned for the power board.
- **Removed from the earlier internal-supply plan:** Mean Well LRS-350-12 ($33.30), C14 inlet with fuse and switch ($13.89), 4 A fuses ($7.50), IEC C13 cord ($5.95; the brick's cord is attached), and the mains wire.

## 7. LED perimeter strip

WS2815 12 V, 144 LED/m, about 3 m around the perimeter. Data comes from GPIO2 through a
74AHCT125 and a 330 Ω resistor. The strip is powered straight from the 12 V supply and injected at both
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
| Ambient light sensor: VEML7700 lux sensor, I2C, STEMMA QT (see note) | [Adafruit #4162](https://www.adafruit.com/product/4162) | 1 | $4.95 | $4.95 | LIVE |
| STEMMA QT to female-header cable, 150 mm (sensor to Pi GPIO header) | [Adafruit #4397](https://www.adafruit.com/product/4397) | 1 | $0.95 | $0.95 | LIVE |
| **Subtotal** | | | | **$224.43** | |

- **Speaker:** not needed now; the wall gives feedback through its LEDs. If spoken replies are added later:
  - Put a spare 8 Ω speaker next to the ReSpeaker on the floor, below the display.
  - Wire it to the ReSpeaker's JST speaker port, which has an onboard 5 W amp.
  - The ReSpeaker's 3.5 mm jack can feed a JBL. The Pi 5 has no 3.5 mm jack. Test whether plugging into the jack mutes the JST speaker.
  - Nothing audio-related goes in the display.
  - Because the ReSpeaker plays the audio, its echo cancellation works.

- **Ambient light → LED brightness:** the brighter the room, the brighter the LEDs.
  - **Why this sensor:** a bare photodiode needs an analog input, which the Pi doesn't have. The VEML7700 measures lux itself and talks I2C, so it plugs straight into the Pi with no other parts.
  - **Wiring:** Pi 3V3 (pin 1), SDA (GPIO2, pin 3), SCL (GPIO3, pin 5) and GND (pin 6). Enable I2C on the Pi.
  - **Placement:** mount the sensor at the Pi, below the display, facing into the room. Point it away from the LED strip, or the strip's own light will brighten itself.
  - **The 150 mm cable:** if the sensor needs to sit further away, about 1 m of 4-wire cable still works at the standard 100 kHz I2C speed.
  - **Home Assistant (Jace):** HA has no built-in VEML7700 integration. Read it with a small script or add-on that publishes lux over MQTT, or with a custom integration.
  - **Brightness curve:** an automation turns lux into a brightness level and sends it to the gateway.
    - Eyes see brightness logarithmically, so map log(lux) to brightness. For example, about 10% at 10 lux, rising to 100% at 1,000 lux or more.
    - Average the reading over about 30 s and add a little hysteresis, so passing shadows don't make the LEDs pump.
  - **The power cap still wins:** the gateway uses the lower of the brightness from HA and the motor-budget cap in §6. A bright room never pushes the brick past its limit.

Pi prices are high in 2026 because of the RAM shortage.

## 9. Case

The modules (606 × 240 mm) sit in the middle, with a bay on each side for the electronics. That makes the case about **880 × 280 × 95 mm** outside. The height is 240 mm of modules, plus about 15 mm above and below for the LED strip and its standoff, plus the two 3 mm panels.

- **Left bay:** no longer holds mains or a power supply, since the 12 V brick sits outside the case. It only needs the 4-pin DIN power jack and the 12 V distribution (later the power board), so it can shrink. The case size will be revisited once the power board is laid out.
- **Right bay (low voltage):** the gateway, on the top rail extended into the bay, plus the level-shifter board and buck converter.

How it goes together:
- **Back:** 1/4" plywood, cut to 880 × 280 mm. It carries the 3 DIN rails, the bay electronics and the wall hangers.
- **Front:** 1/8" black acrylic, laser-cut in one piece. It has one window per module, sized from the module CAD. It's held on with M3 countersunk screws into printed brackets, so it comes off for service.
- **Sides:** 1/8" black LED acrylic, about 95 mm deep. It looks matte black when the LEDs are off and passes about 29% of their light, in the LEDs' own colour. The WS2815 strip sits on printed clips about 10 mm inside the panels so the LEDs blend instead of showing as dots. The 4-pin DIN power jack goes through the left end panel.
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
