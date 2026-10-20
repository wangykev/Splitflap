# Split-flap wall: project game plan

A 3 × 15 (45-module) split-flap display with an LED perimeter strip and a "Hey Venus" voice
assistant. This file is the living plan: what exists, what's decided, and what still has to be
built. Update the **Status** and **Roadmap** sections as work lands.

## Who owns what

| Side | Owner | Scope |
|---|---|---|
| Hardware + gateway | Kevin | Modules, RS-485 bus, the ESP32 gateway firmware, the LED strip and its firmware support |
| Software | Jace | Raspberry Pi: Home Assistant, Assist voice satellite, LLM, the Companion app |

The boundary between the two is **`mock-gateway/CONTRACT.md`**. If a change affects that
interface, update the contract first and re-run its §10 checks.

## Workspace layout

| Folder | What | Notes |
|---|---|---|
| `SplitFlapGateway/` | ESP32 gateway firmware (upstream clone, v3.17.0) | PlatformIO. Waveshare ESP32-S3-RS485-CAN. `openapi.yaml` is the REST spec. |
| `SplitFlapUniversalFirmware/` | Module firmware (upstream clone) | Runs on each flap module. |
| `SplitFlapGatewayCompanion/` | Companion app (upstream clone, v2.10.23) | Runs on the Pi. It's the only writer to the flaps. |
| `mock-gateway/` | **Ours.** Mock gateway, contract, HA package, reference client | Lets the software side build with no hardware. |
| `../Kevin Splitflap/PCBs/` | Module driver PCB (ATtiny1616, KiCad) | |
| `../adamGsplitflap/` | Original module hardware/protocol (Adam G Makes) | |

The three upstream clones are third-party repos (CC BY-NC-SA 4.0). Keep our changes minimal and
isolated so upstream updates can still be merged.

## Architecture (decided)

```
voice satellite (Pi) → HA Assist → LLM ──calls──► script.splitflap_show_answer
                         │                               │ sanitize()
          satellite state│                               ▼
                         ▼                          Companion ──REST /api/rs485/batch──► Gateway ──RS-485──► 45 modules
                 rest_command /api/led ──────────────────────────────────────────────► Gateway ──GPIO2────► LED strip
```

**Rules (CONTRACT.md §1):**
- The Companion is the only display writer.
- The Pi never calls the gateway's display routes or MQTT display topics.
- The Pi calls the gateway directly only for LEDs.
- Nothing sends characters that aren't on the flaps; `sanitize()` runs on every answer right
  before it is sent.
- LED commands are sent only if `GET /api/capabilities` lists `"led"` in `features`.

## Status (2026-10-19)

**Done**
- [x] Read through the gateway, Companion and module firmware. The interface is mapped and the gateway
      firmware stays **unmodified** for the first hardware bring-up.
- [x] `mock-gateway/mock_gateway.py`: emulates firmware v3.17.0 closely enough that an unmodified
      Companion works against it. Also implements the LED API. Has a viewer at `/`.
- [x] `mock-gateway/CONTRACT.md`: the Pi ↔ wall contract.
- [x] `mock-gateway/ha/splitflap_venus.yaml`: Home Assistant package (LEDs, time/weather voice commands,
      the `show_answer` script, re-sending a lost answer).
- [x] `mock-gateway/venus_client.py`: standalone reference client plus `sanitize()`.
- [x] Verified end to end with the real Companion against the mock (CONTRACT.md §10).

**Not yet verified**
- [ ] The HA package has not been loaded into a running Home Assistant. Templates were only
      validated offline in sandboxed Jinja.
- [ ] The mock's MQTT mode (`--mqtt`) has not been tested; no broker was available.

## Roadmap

### Phase 1: hardware bring-up, no firmware changes (Kevin)
- [ ] Build or buy the gateway: Waveshare ESP32-S3-RS485-CAN. Flash the stock `SplitFlapGateway`
      firmware (`pio run -t upload`, or the prebuilt `.factory.bin` at `0x0`).
- [ ] First boot: join the `Split-Flap-GW` / `12345678` AP, open `192.168.4.1`, enter WiFi. Set the
      **grid to 3 rows × 15 cols** in Settings.
- [ ] Build the modules, flash `SplitFlapUniversalFirmware`, then provision IDs 0–44 (id = row × 15 + col)
      and calibrate each one from the gateway dashboard.
- [ ] Smoke test: `curl -X POST http://<gw>/api/flap/text -d '{"text":"HELLO","start":0}'`.
- [ ] Hand the gateway IP to Jace. Jace points the Companion's `GATEWAY_URL` and the HA
      package's `GATEWAY_HOST` at it. **Nothing else should change.**
- [ ] Re-run CONTRACT.md §10 against the real wall. Note anything that differs from the mock and
      fix the mock to match.

### Phase 2: LED strip hardware (Kevin)
- [ ] Strip: WS2815 (12 V), 144 LEDs/m, mounted around the display perimeter. **Cut it to the real
      perimeter and record the exact LED count, start corner and direction here:**
      `LED_COUNT = ___`, `start corner = ___`, `direction = ___`.
- [ ] Data: **GPIO2** on the Waveshare 2.0 mm header (GPIO1 is a spare; neither pin is used by the
      firmware or is a strapping pin). Run it through a 74AHCT125 level shifter (3.3 V → 5 V,
      needs its own small 5 V buck) and a 330 Ω series resistor at the strip. Tie BI to GND on
      the first pixel.
- [ ] Power: feed the strip **directly from the 12 V PSU, injected at both ends**. Do **not** power
      it through the Waveshare board or the module rail/pogo pins. Use a common ground with the
      gateway and a 1000 µF capacitor at the strip input. Worst case is roughly 6–8 A at 12 V for
      3 m of 144/m at full white, so check the seller's W/m. Size the PSU for the modules plus
      the strip at its brightness cap.
- [ ] Bench-test the strip with a tiny standalone sketch before touching the gateway firmware.

### Phase 3: LED support in the gateway firmware (Kevin). The contract is the spec.
Implement exactly CONTRACT.md §4. The mock (`mock_gateway.py`, `Wall.set_led` / `h_led` /
`led_doc`) is the reference behaviour.

| File | Change |
|---|---|
| `src/led.h`, `src/led.cpp` (new) | LED state machine (`idle`/`listening`/`thinking`/`speaking`) and the animations: listening = whole strip glows, thinking = a comet circling from the start corner in the configured direction, speaking = pulse, idle = off. Auto-expiry: listening 10 s, thinking/speaking 30 s. Cap brightness at 40 during quiet time. A `taskLED` FreeRTOS task draws at about 60 fps. |
| `src/common.h` | `LED_PIN 2`, `LED_COUNT`, `LED_START_CORNER`, `LED_DIRECTION`, `LED_MAX_BRIGHTNESS`. Put them next to the RS-485 pins (around line 116). |
| `platformio.ini` | Add `adafruit/Adafruit NeoPixel` to `lib_deps`. It uses RMT, so WiFi can't glitch it. |
| `src/main.cpp` | `ledInit()` in `setup()`. Spawn `taskLED` on **core 1**, low priority, next to the other tasks (around line 140), so it never competes with RS-485 on core 0. Optionally add it to `[WDG]` stack telemetry. |
| `src/web.cpp` | `GET`/`POST /api/led` plus `OPTIONS`. **Don't wrap it in `CONTENTGATED`**: LEDs must work during maintenance. Validation and errors match the contract. **Add `"led"` to `features` and the `"led":{count,startCorner,direction}` object to `/api/capabilities`** (around line 1190). That single entry turns LEDs on for the Pi. |
| `src/mqtt.cpp` | Subscribe to `<prefix>/led/set` (plain state or JSON) and handle it **before** the `busBusy()` gate, like `maintenance/set`. Publish `<prefix>/led/state`. |
| `src/config.*` (optional) | Persist the count, corner, direction and brightness so they can be changed from the dashboard without reflashing. |
| `openapi.yaml` | Document `/api/led`. |

Done when: Jace's unchanged HA package and `venus_client.py` drive the real strip, the
`thinking` comet goes the right way from the right corner, expiry works, and display
behaviour is unchanged.

### Phase 4: software side (Jace), tracked here for visibility
- [ ] Load `ha/splitflap_venus.yaml` on the Pi and pass *Check configuration*. Expose
      `script.splitflap_show_answer` to Assist. Put the 3 × 15 limit in the agent's instructions.
- [ ] Voice satellite on the Pi. Wake word: a stock one for development, then a custom
      "Hey Venus" model (openWakeWord or Porcupine). This is configured entirely in HA and is
      outside the contract.
- [ ] Set the Companion's weather location (`zip_code` / `timezone` global settings).
- [ ] Decide which other Companion apps or voice commands to add. Each one follows the same rule:
      it goes through the Companion, and free text goes through `sanitize`.

### Later / ideas (not committed)
- Per-state LED colours chosen by the Pi (the API already accepts `color` and `brightness`).
- An HA `light` entity for the strip via MQTT discovery.
- A physical button on GPIO1 (for example, push-to-talk or clearing the wall).
- Contribute the LED feature upstream to `SplitFlapGateway` once it's stable.

## Gotchas learned (keep these in mind)
- **A message sent during maintenance is dropped.** The gateway returns 503, the Companion does not
  retry, and it stays `transport.connected:false` until its next successful send. Calibration and
  provisioning count as maintenance.
- **A Companion restart forgets messages** (apps resume) and then believes the wall is blank. The HA
  re-send automation and `venus_client.py watch` cover both cases. Detect a lost answer from the
  Companion's state (no app running, and it believes the wall is blank or its link is down), not
  from "it went down", because short restarts are missed that way.
- **The Companion crops text longer than 3 lines to the middle 3.** `sanitize` wraps and truncates
  first.
- **The real firmware does not advertise `cells`**, so the Companion sends pages as `/api/rs485/batch`
  frames (windows-1252). The mock must keep doing the same.
- **Never put both "matrix" and "gateway" in the product name**: the Companion would treat the device
  as a Matrix gateway.
- **The Time app takes about 5 s for its first draw.** Don't treat a blank wall right after
  `apps/run` as failure.
- **HA renders templates to native types,** so `"72"` becomes the number 72. The package forces
  `| string` on payloads; keep that.
- **HA's `slugify` turns `°` into "deg".** The package transliterates letters only.

## How to test (no hardware)
```
cd mock-gateway
python mock_gateway.py --state-file mock.json            # viewer: http://localhost:8080/
# Companion (from SplitFlapGatewayCompanion/backend, in a venv with requirements.txt):
GATEWAY_URL=http://<this-machine>:8080 python -m app       # Companion on :8000
python venus_client.py --companion http://localhost:8000 --gateway http://localhost:8080 demo "Hello"
python mock_gateway.py --no-led                          # behave like today's real firmware
```
After any change to the mock, the HA package, `venus_client.py`, or an upgrade of the firmware
or Companion, re-run **CONTRACT.md §10**.

## Working conventions
- Hardware-side firmware changes stay out of the gateway until Phase 1 bring-up works on stock firmware.
- Keep `mock_gateway.py` faithful to the real firmware: when the real wall behaves differently,
  fix the mock, not the contract (unless the contract itself was wrong).
- Keep `sanitize()` in `venus_client.py` and the `clean` template in the HA package in sync.
  They must give identical output.
