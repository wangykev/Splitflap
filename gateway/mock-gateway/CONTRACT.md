# Split-Flap Wall: Pi ↔ Wall Contract

This is the agreement between the **hardware side** (Kevin: modules, ESP32 gateway, LED strip) and
the **software side** (partner: Home Assistant, voice, LLM). Build against the mock gateway in this
folder. When the real wall is ready, the only change is an IP address.

**Verified against:** gateway firmware **v3.17.0**, emulated by `mock_gateway.py`, and
SplitFlapGatewayCompanion **v2.10.23** (commit `ada131e`, 2026-10-12), run unmodified against
the mock. If either one is upgraded, re-run the checks in [§10](#10-checks-to-re-run-after-any-upgrade).

---

## 1. Architecture and rules

```
 voice satellite (Pi) ──► Home Assistant Assist ──► LLM
                               │
         display (text, apps)  │  LED states only
                 ▼             ▼
            Companion  ─────► Gateway (ESP32) ──RS-485──► 45 flap modules
         (only writer)          └──────────────GPIO2────► LED perimeter strip
```

1. **The Companion is the only thing that writes to the flaps.** Everything displayed (answers,
   the time, the weather) goes through the Companion's API (§2).
2. **The Pi's own code never calls the gateway's display routes:** `/api/display/cells`,
   `/api/flap/*`, `/api/rs485/*`. It also never publishes the gateway's MQTT `splitflap/display/set`,
   `splitflap/flap/set` or `splitflap/send` topics. A second writer would fight the Companion, and
   the Companion would overwrite it on its next refresh (within 15 s).
3. **The Pi calls the gateway directly for LEDs only** (§4). It may also *read* the gateway's
   `GET /api/capabilities` and `GET /api/status`.
4. **Nothing sends characters that aren't on the flaps** (§3).

## 2. Your display API is the Companion

Base URL `http://<pi>:8000` (`COMPANION_PORT`). No authentication on the LAN. Add `?display=default`
to every call (the first wall is always `default`; `GET /api/displays` lists them).

| What | Call | Result |
|---|---|---|
| Show the time | `POST /api/apps/run` `{"app":"time"}` | `{"ok":true,"active_app":"time"}`. The time is centred on the middle row and updates on the minute. The first draw can take about 5 s. |
| Show the weather | `POST /api/apps/run` `{"app":"weather"}` | Cycles pages about every 8 s: conditions, UV, a 3-day forecast. Uses keyless Open-Meteo, so **no API key is needed**. |
| Show an answer | `POST /api/message` `{"text":"…"}` with **no `seconds`** | `{"ok":true}`. **It replaces the running app and stays up** until something else is shown. The app does not come back. |
| Blank the wall | `POST /api/apps/stop` | Stops the app **and blanks the wall**. **You don't need to call this before a message.** |
| What's showing | `GET /api/current_state` | `active_app` (null while a message is up), `string` (45 chars, row-major), `transport.connected` |
| Live updates | `GET /api/events` (SSE) | `event: display` with the same JSON whenever something changes |
| Health | `GET /api/health` | `{"ok":true,"version":"2.10.23"}` |

Weather location is a Companion global setting:
`POST /api/global-settings` `{"values":{"zip_code":"94110","timezone":"America/Los_Angeles"}}`.

**How the Companion lays out a message:** `\n` forces a line break. Long lines are word-wrapped,
and each line is centred. **If the text needs more than 3 lines, the Companion keeps the middle 3
and drops the first and last. It doesn't page.** This is why `sanitize` (§3) does the wrapping
itself.

**What the Companion remembers.** After a Companion restart, a running *app* resumes by itself.
A *message* does not: the Companion then believes the wall is blank. Also, a message sent while
the gateway is in maintenance gets a 503 and is **dropped, with no retry**. The Companion reports
`transport.connected:false` until its next successful send. So the Pi keeps the last answer and
**re-sends it** when either happens (§6, implemented in both the HA package and `venus_client.py`).

## 3. The character rule

**Policy (the requirement): nothing sends characters that aren't on the flaps.**

**Filter (the guarantee): `sanitize()` runs on every answer, immediately before it is handed to
the Companion.** Don't rely on the LLM or any other source to follow formatting instructions. Even
when told "uppercase only", LLMs produce curly apostrophes, accented letters, `°`, `…` and emoji.

The flaps carry the gateway's `charset.common` from `GET /api/capabilities`. On the default reel:

```
 ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$&()-+=;":%'.,/?*     (plus 7 colour flaps)
```

`sanitize(text)` does the following, in order:
1. Folds lookalikes: `’ ‘` → `'`, `“ ”` → `"`, `– —` → `-`, `…` → `...`.
2. Uppercases.
3. Transliterates letters: `é` → `E`, `ß` → `SS`.
4. Replaces **anything still off the reel with a space**.
5. Word-wraps to 15 columns.
6. Keeps 3 lines, ending with `...` when cut.

| LLM wrote | Wall shows |
|---|---|
| `It’s 72°F ☀️ café` | `IT'S 72 F CAFE` |
| `Dinner at 7:30 — don't be late…` | `DINNER AT 7:30` / `- DON'T BE` / `LATE...` |
| a 110-character weather ramble | `THE WEATHER` / `TODAY IN SAN` / `FRANCISCO IS...` |

The same function exists twice, with identical output on the test strings: `sanitize()` in
`venus_client.py` and the `clean` template in `ha/splitflap_venus.yaml`. The Companion's own
apps (Time, Weather) are the Companion's responsibility; it already checks the wall's character
set. The mock logs a **WARN** line, and shows it in the viewer, for any off-reel character that
reaches it. During development that list should stay empty.

## 4. LED perimeter strip (gateway)

The hardware side treats this as fully supported. The mock implements it today, and the real
firmware will implement exactly this.

**Capability gating, read once at startup:**

```
GET /api/capabilities → "features": [..., "led", ...] ?
    yes → send LED commands
    no  → skip LED commands entirely (no requests at all)
```

This is like reading a chip's ID register before configuring it. The same client code is then
correct on the mock, on today's real gateway (no `"led"`: display only, zero LED traffic) and on
the real gateway after the LED firmware lands. **Hardware-side obligation: when LED support is
added to the firmware, add `"led"` to `features` and the `led` object below to
`/api/capabilities`. That single entry turns the LEDs on, with no change on the Pi.**

```
POST /api/led   {"state":"listening"|"thinking"|"speaking"|"idle"}
                optional "color":"#RRGGBB", "brightness":0..255
  → {"ok":true,"state":"thinking","color":"#A855F7","brightness":128,"effectiveBrightness":128,
     "expiresIn":30.0,"seq":4,"count":300,"startCorner":"bl","direction":"cw"}
  400 {"error":"'state' must be one of: idle, listening, thinking, speaking"}
GET  /api/led   → the same object
MQTT splitflap/led/set   payload "thinking"  (or the same JSON); state on splitflap/led/state
capabilities: "led": {"count":300, "startCorner":"bl", "direction":"cw"}
```

| State | Animation (runs on the gateway) | Default colour | Auto-expires to idle |
|---|---|---|---|
| `listening` | whole strip glows | `#3B82F6` | after 10 s |
| `thinking` | a comet circles the perimeter from `startCorner` in `direction` | `#A855F7` | after 30 s |
| `speaking` | gentle pulse | `#22C55E` | after 30 s |
| `idle` | off | | |

- The strip goes **around the display** and will be cut to the real perimeter. **Read `count`, never
  assume a number.** The Pi sends states only, never frames, and the gateway scales the animation
  to `count`. (Mock default: 300. Change it with `--leds`, `--start-corner tl|tr|bl|br`,
  `--direction cw|ccw`.)
- **Expiry** protects against a crashed Pi leaving the ring spinning forever. Re-send the state if a
  phase runs longer.
- LED calls are **never blocked** by maintenance. During quiet time, brightness is capped at 40.
- LED calls are fire-and-forget: use a short timeout and never block the voice pipeline on one.

## 5. Answer length

The wall is **3 lines × 15 characters**. **This limit must be in the LLM's instructions**: the
Assist agent's prompt and the `show_answer` script description. For example: *"At most 3 short
lines of 15 characters, about 40 characters total, no emoji or symbols."* `sanitize` truncates as
a backstop, so a long answer is shortened deliberately, at a word boundary with `...`, instead of
the Companion cropping its first and last lines.

## 6. Home Assistant recipe (the main integration)

Voice runs in **HA Assist** with a **voice satellite on the Pi**, not a custom loop. Everything is
in one package, **`ha/splitflap_venus.yaml`**. Copy it to `<config>/packages/`, enable packages,
and edit the lines marked `# EDIT`: `GATEWAY_HOST`, `COMPANION_HOST` and `assist_satellite.venus_pi`.

| Piece | What it does |
|---|---|
| `sensor.splitflap_gateway_capabilities` | REST sensor on `/api/capabilities`. Attributes: `features`, `charset`, `grid`, `led`. |
| `binary_sensor.splitflap_led_supported` | `'led' in features`. Gates every LED call. |
| `binary_sensor.splitflap_gateway_maintenance` | `/api/status` → `maint` |
| `sensor.splitflap_companion` | `/api/current_state`. State is the active app or `none`. Attributes: `string`, `transport`. |
| `automation` *LEDs follow the voice satellite* | Satellite `listening` → `listening`, `processing` → `thinking`, `responding` → `speaking`, anything else → `idle`, via `rest_command.splitflap_led`, only if LEDs are supported. |
| `automation` *show the time / weather / clear* | Sentence triggers ("show the time", "show the weather", "clear the board") → the Companion's Time/Weather apps, or stop. |
| `script.splitflap_show_answer` | **Expose it to Assist** so the LLM can call it. It sanitizes the text, stores it in `input_text.splitflap_last_answer`, then sends a Companion message with no `seconds`. |
| `automation` *re-send the last answer* | Every 30 s: if an answer is stored, no app is running, and the Companion believes the wall is blank (after a restart) or its link is down (after a 503), and the gateway isn't in maintenance → re-send it. |

As an alternative to the `rest_command`s, the Companion's HACS integration (`custom_components/splitflap`)
provides a `splitflap.message` service and an app `select` entity. The package uses plain REST so
it has no extra dependency. Either way, the answer must go through `sanitize` first.

**Wake word:** configured entirely in Home Assistant (a custom "Hey Venus" model, or a stock wake
word during development). It is outside the scope of the mock and this contract. The LED
`listening` state comes from the satellite's state, whichever wake word is used.

## 7. Standalone reference: `venus_client.py`

Uses the same rules, for testing without Home Assistant. Standard library only.

```
python venus_client.py --companion http://<pi>:8000 --gateway http://<gw> mode time
python venus_client.py ... say "It's 72°F and sunny"     # sanitize → Companion message
python venus_client.py ... stop
python venus_client.py ... led thinking                  # skipped unless "led" is in features
python venus_client.py ... demo "Dinner is at 7"         # listening → thinking → speaking → answer → idle
python venus_client.py ... watch                         # re-sends a lost answer (restart / 503)
python venus_client.py sanitize "It’s 72°F ☀️ café"
```

## 8. Running against the mock

```
python mock_gateway.py --state-file mock.json          # http://localhost:8080 = viewer
# in the Companion repo, backend/:
GATEWAY_URL=http://<this-machine>:8080 python -m app    # unmodified Companion → mock
```

The viewer shows the 3×15 flaps, the LED strip around them, the Companion registration, and any
off-reel warnings. Its **Maintenance** and **Quiet time** buttons let you test the failure paths.
Use `--no-led` to behave like today's real firmware, and `--mqtt host:1883` (needs `paho-mqtt`)
to also speak the gateway's MQTT topics.

**Moving to the real wall:** point the Companion's `GATEWAY_URL`, and the HA package's
`GATEWAY_HOST`, at the gateway's IP. Nothing else changes. The LEDs stay off until the firmware
advertises `"led"`.

## 9. Reference: what the gateway does underneath (not your API)

This is what the mock emulates and the Companion uses. **Don't call these from the Pi's own code.**

- `POST /api/rs485/batch` `{"frames":["m00-A\n","m01-B\n",…],"step_ms":15}` is the Companion's page
  path on a split-flap wall. The body is windows-1252. Up to 512 frames, `step_ms` 0..100. Returns
  `{"ok":true,"sent":n}`. Frames: `m<id>-<char>` show a character, `m<id>+<index>` show a flap by
  index, `m<id>h` homes (blank), `*` broadcasts.
- `POST /api/display/cells` `{"start":0,"step_ms":15,"cells":[{"ch":"A"}|{"color":"red"}|{"blank":true}|{"skip":true}]}`
  is the Matrix-compatible path. It's lenient: cells that can't be shown are skipped and counted.
  The real firmware does **not** advertise the `cells` feature, so the Companion uses batch.
  Guidance for any direct writer: send whole frames in one call, use `skip` for unchanged cells,
  and never stream per character.
- `POST /api/flap/text` `{"text","start"}`, `/api/flap/char` `{"id","char"}`, `/api/flap/index`,
  `/api/flap/home` `{"id":-1}`. There is no wrapping: module id = row × 15 + col.
- `GET /api/display/state` `{rows, cols, cells[]}`.
- Character resolution: lowercase folds to uppercase, except the colour codes `r o y g b p w`, and
  `"` maps to the reel's `q` flap.
- **Maintenance** (`POST /api/maintenance {"on":true}`, or any calibration/provisioning job): all
  display content gets **503** `{"error":"maintenance in progress -- display content is paused","reason":"maintenance","level":1,"remaining":0}`.
  Homing and LEDs still work.
- **Quiet time** (`POST /api/quiet {"on":true}`, or the schedule): the wall blanks and later
  requests are held. When quiet ends, each module shows the last thing it was asked for.
- Registration: the Companion `POST /api/companion`s every 30 s. Its settings are mirrored to
  `PUT /api/companion/settings` (an opaque gzip blob, ≤ 64 KB).
- MQTT, prefix `splitflap`: `display/set` (plain text), `flap/set`, `flap/home`, `send`,
  `quiet/set`, `maintenance/set`, `led/set`. The gateway publishes `display/state`,
  `availability`, `led/state`.

## 10. Checks to re-run after any upgrade

These were run on 2026-10-19 with the real Companion against the mock:

1. **Connects:** the Companion registers, reads capabilities, mirrors its settings blob (663 bytes)
   to the gateway, and the blob survives a mock restart (`--state-file`).
2. **Time / Weather:** both render correctly on 3×15. Weather needed no API key.
3. **A message over a running app** replaces it and stays up past the next minute. Stop is not
   needed first.
4. **Restart:** after a Companion restart, an app resumes but a message doesn't (the Companion then
   believes the wall is blank). `watch` / the HA automation re-sends the answer, including on a
   fast restart.
5. **Maintenance:** a message sent during maintenance gets a 503 and is lost, and the Companion
   stays `connected:false`. The re-send fires once maintenance ends. Quiet blanks the wall and then
   restores the last request.
6. **LEDs:** a demo turn goes listening → thinking → speaking → idle. `thinking` auto-expires after
   30 s. With `--no-led` the client sends **zero** LED requests.
7. **sanitize:** the Python and HA-template versions give identical output on the test strings, and
   the mock logged no off-reel warnings.
8. **HA package:** YAML parses and every template renders in a sandboxed Jinja environment with
   HA-like filters. It has **not yet been loaded into a running Home Assistant.** Do that first on
   the Pi (Developer Tools → *Check configuration*).
