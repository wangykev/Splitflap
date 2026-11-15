# Improvements backlog

Ideas noted while reading through the code. **Nothing here is scheduled or started.** When an
item gets picked up, move it into the Roadmap in `CLAUDE.md` (and, if it touches the Pi ↔ wall
interface, update `mock-gateway/CONTRACT.md` first).

Each entry: where it lives, what happens today, what I'd like instead, and anything to watch out for.

---

## Module firmware (`SplitFlapUniversalFirmware/`)

### 1. Power-on ripple instead of the current stagger

**Where:** `setup()` in `src/SplitFlapUniversalFirmware.cpp`, the "Staggered startup" block
(around line 2344 in v36), just before the watchdog starts and the module homes.

**Today:** the stagger exists to spread motor inrush so the whole wall powering on at once doesn't
brown out the supply. It looks random on the wall, but for a provisioned module it isn't:

```cpp
staggerMs = (unsigned long)(moduleId % 32) * 120UL;  // 0–3.7 s window
```

Only an unprovisioned module (`moduleId == 255`) uses a true random delay (`lcgRand(4000)`).
On a 3 × 15 wall (id = row × 15 + col) the `% 32` wraps at id 32 (row 2, col 2), so the bottom
row starts partway through, then jumps back near the start of the sequence. The result reads as
noise rather than a pattern.

**Idea:** make the start order a diagonal ripple from the top left to the bottom right:

```cpp
// row/col from id; GRID_COLS = 15 for this wall
uint8_t row = moduleId / GRID_COLS;
uint8_t col = moduleId % GRID_COLS;
staggerMs = (unsigned long)(row + col) * RIPPLE_STEP_MS;
```

On 3 × 15 that gives 17 diagonals (0…16). At 120 ms per step the whole ripple takes about 2 s,
shorter than today's 3.7 s window.

**Things to work out:**
- **The module doesn't know the grid width.** It only knows its own id. Options: a compile-time
  `GRID_COLS` (simple, but every module has to be built for this wall), a new EEPROM field set
  by a provisioning command (more flexible, needs a new command and gateway/dashboard support),
  or keeping it 1-D (a plain `id × step` with no `% 32` wrap). That would be a left-to-right,
  row-by-row sweep, which is cheaper and might already look good enough.
- **Inrush:** a diagonal starts up to 3 modules at once instead of 1. Check this against the
  PSU and power-board budget, or lengthen `RIPPLE_STEP_MS`. Today's `% 32` cap exists so high
  ids aren't unresponsive for long; the ripple keeps the total short, so that's fine.
- **Only the start times ripple.** After the delay each module homes, and homing length depends
  on where its reel stopped, so the finish won't be a clean wave. If the visual matters, a
  cleaner option is to let modules home in a ripple and then have the gateway/Companion send a
  rippled "settle" frame (for example, all blanks) once everything reports homed.
- **Unprovisioned modules (id 255)** should keep the random delay. They have no position.
- **Non-rectangular or larger walls:** keep the step and the formula in one place so the
  ripple can change (center-out, column sweep, and so on) without touching the rest of `setup()`.

### 3. Find the fastest reliable step speed (and maybe go faster)

**Where:** `stepDelay` (`src/SplitFlapUniversalFirmware.cpp:568`) and the one place it's used,
`delay(stepDelay)` inside `advance()` (`:1719`), the firmware's only motion loop.

**Today:**

```cpp
const int stepDelay = 1;    // ms between half-steps   (cpp:568)
...
delay(stepDelay);           // inside advance()         (cpp:1719)
```

One half-step per ~1 ms, so 4096 half-steps take **~4.2 s per revolution** (about 14 RPM). The
worst-case move (nearly a full revolution, e.g. `Z` → blank) takes about 4 s.

**1 ms is already the floor of this code.** `delay()` counts whole milliseconds, so the only
smaller value is 0. That would step as fast as the loop runs (tens of µs per step) and certainly
stall the motor. To go "a bit faster" you need microsecond resolution. And because `stepDelay`
is `const`, every new value means a rebuild and reflash, which makes incremental tuning painful.

**Idea:** switch to microseconds and make the value settable from the bus, so you can try
950, 900, 850… µs without reflashing. Measure each value with the built-in `M` test, and keep
the fastest one that still never misses a step, with margin.

```cpp
uint16_t stepDelayUs = 1000;      // was: const int stepDelay = 1;
...
delayMicroseconds(stepDelayUs);   // was: delay(stepDelay);
```

The real step period is the delay **plus** the loop's own work: four `digitalWrite`s, a
`digitalRead` of the Hall pin, a watchdog pet, and the occasional bus/timer interrupt. That's a
few tens of µs, so the number you set is slightly less than the true period. That doesn't
matter for tuning, since you measure the result. But record the *measured* time per revolution,
not just the setting.

#### A temporary tuning command

- Add a numeric command, e.g. **`k<µs>`** (`k` is unused; taken so far:
  `- + h c T P U Q M o t s g w i a N d A R v F e`, plus `X` for provisioning). Clamp the value
  to a sane range (e.g. 300–3000 µs) so a typo can't stall or crawl.
- It's a "digits until a non-digit" command like `o`/`t`. Copy that pattern **and add the new
  parser state to the idle-timeout list** (`cpp:3005–3007`, the `(parseState >= 5 &&
  parseState <= 12) || … == 24` condition). Otherwise a `k900` sent without a newline just
  times out after 200 ms instead of being applied.
- Keep it RAM-only while tuning (a reset goes back to the default). That's safer when an
  experiment goes wrong.
- Send it through the gateway's Bus Monitor "Send Frame" box or `/api/rs485/send`, followed by
  `m<id>M10` to measure.
- Flash is no problem: the v5 build uses 13,675 of 15,356 bytes.

#### How to measure: the `M` test is the instrument

`m<id>M<n>` turns the reel n revolutions (5–20) and counts the steps between magnet passes for
each one. **A missed step shows up directly:** if the motor fails to move on a commanded step,
it takes *more* commanded steps to get round, so that revolution's count goes **up**. In normal
operation missed steps are hidden, because `advance()` re-syncs the position every time the
magnet passes. That's why you test with `M` and not by watching letters.

1. **Baseline at the current speed (1000 µs)** on each test module: `m<id>M20`. Note the
   average steps per revolution, the spread (`spreadTenthsPct`) and the raw per-revolution
   counts. A healthy module shows nearly identical counts every revolution.
2. **Step down** (950, 900, 850, …), running `M20` at each value.
   - **Pass:** code 0, the average matches the baseline within a step or two, and the spread
     is as small as the baseline's.
   - **First signs of trouble:** a few revolutions reading high, or the spread growing. Under
     the firmware's own 5% rule that's still "code 0", so use your own, much tighter, limit.
   - **Too fast:** code 1 (inconsistent) or code 2 (no motion; the motor buzzes but stalls).
3. **Stop at the first failing value** and call the last clean value the *edge*.
4. **Pick the wall's setting with margin:** about 20–30% slower than the edge of the *worst*
   module. Use one value for the whole wall rather than per-module tuning. The motors then
   behave alike, and a single constant is all you need.

#### Test under the worst conditions, not the bench's

The edge you find on one module on a quiet bench is optimistic. Motor torque drops with speed,
so anything that weakens it moves the edge:

- **Supply sag:** test with **all 45 moving at once** (a full-wall text change), not one module
  alone. The power board's notes budget ~0.2 A per moving module.
- **The stiffest mechanism:** test several modules, including any that feel tight by hand, and
  re-check after the wall has run for a while (wear, dust, lubricant thickening when cold).
- **Momentum at the stop:** `advance()` ends with `releaseMotor()`, which cuts the coils right
  after the last step. At higher speed the reel carries more momentum and could coast past the
  target flap. After tuning, watch real character changes, not just `M`. If flaps overshoot,
  hold the coils energised for ~20–50 ms before releasing.

#### Possible bigger win: acceleration

A stepper can **keep running** faster than it can **start from rest** (pull-out torque vs
pull-in torque). Today every move starts at full speed. A short ramp would let the cruising
speed go well past the from-rest limit:

- start at ~1500 µs and shrink toward the tuned value over the first ~50–100 steps;
- optionally ramp down over the last few steps too, which also fixes coasting.

That's a few lines in `advance()`, but `advance()` is also called **one step at a time** by
homing, calibration and the self-tests (`advance(1)` in loops), so the ramp has to live in the
callers that make long moves (`moveToIndex`, `gotoRawStep`, `nudge`) or be keyed to "steps
since the motor started". Do the simple tuning first. Add the ramp only if the gain isn't
enough. If #4 (timer-driven motion) is done, the ramp belongs there instead: a ramp is just
which interval the step interrupt loads next. #4 has the details.

#### After choosing a value

- **Make it permanent** as the new compile-time default and update the comments that assume
  "~4 s per revolution" (`cpp:112`, `:617`). Remove the `k` command, or keep it and store the
  value in EEPROM. If you store it, use a new field after the flap set (`0xCE`–`0xCF`), with
  `0xFFFF` meaning "use the default", as the layout rules require.
- **Re-run `c` (calibrate) on every module.** The stored steps per revolution were measured at
  the old speed. A value measured with even occasional misses is wrong at the new one. Then
  check the home offset (blank centred) once more.
- **Nothing else depends on the speed:**
  - the watchdog is petted every step;
  - gateway timeouts for `M`/`T`/`c` are upper bounds, so faster just finishes sooner;
  - the Hall sensor responds in microseconds, and the magnet is still ~150–200 steps wide;
  - the Hall pin is sampled once per step, so faster stepping doesn't skip it.

**Expectations:** a 12 V 28BYJ-48 is a slow, geared motor, and 1000 half-steps/s is already a
common practical speed for it. Without a ramp, 10–30% faster is a realistic hope. With a ramp,
perhaps more. The measurement decides.

### 4. Non-blocking, timer-driven motion: a new message retargets a moving reel

**Where:** `advance()` (`src/SplitFlapUniversalFirmware.cpp:1708`), `moveToIndex()` (`:2239`),
the `-` display-character handler (`case 4`, `:2648`), `stepDelay` (`:568`), `saveState()`
(`:1267`). The coil pins are `IN1`–`IN4` = Arduino 9/8/7/6 = **PB0–PB3** and the Hall pin is
4 = PB5 (`:543–552`). Line numbers are for the v36 working tree.

**Today:** motion is blocking. The parser calls `moveToChar(c)` directly, and it doesn't return
until the reel stops (up to ~4 s). Each half-step is `applyStep()` followed by `delay(1)`, and
that `delay()` polls `micros()`. While a move runs:

- `loop()` doesn't run. A new `m05-X` for this module waits in the receive ring, and the module
  finishes the old move before it starts the new one.
- **Frames can be lost.** The ring is 128 bytes (`busRing`, `:864`) and the receive ISR **drops
  new bytes** once it's full (`:873`). A full page is ~45 × 6 = 270 bytes, so a module still
  moving from page 1 can miss its own frame for page 2. That's presumably why the gateway
  advertises `"motion":{"kind":"mechanical","settleMs":4000}` (`SplitFlapGateway/src/web.cpp:1224`):
  clients wait 4 s between pages.
- The speed can't go below 1 ms per half-step without code changes (see #3).

**Goal:**
1. If a new character arrives mid-move, go **straight** to it, without finishing the old move.
2. **No visible stutter, ever.** Step timing must not depend on what else the firmware is
   doing (replies, EEPROM writes, restores, parsing).
3. The step interval can be set finer than 1 ms (e.g. 0.7 ms), with acceleration if the motor
   needs it.

#### Why not just "step from `loop()` when 1 ms has passed"

That is the obvious non-blocking version, and it **fails goal 2**. A step can only happen when
`loop()` comes round, and some things block `loop()`:

- a `v` reply, ~35 ms (sending is blocking);
- a full `A` dump, ~0.75 s;
- EEPROM writes, a few ms each;
- receiving a restore payload, ~650 ms.

The motor would pause during each one. That's safe for position (a late step only makes it
slower), but it is a visible stutter.

#### The design: a hardware timer interrupt takes every step

**Timer:** TCB0 in periodic-interrupt mode. It's free today: `millis()` is on TCD0, and the
firmware uses no `tone()`, `Servo` or `analogWrite()`. It counts the 10 MHz CPU clock and resets
to 0 **in hardware** on reaching `CCMP`, so the interval is exact and never drifts.

```c
// Period in timer counts at 10 MHz (0.1 µs resolution): 1.0 ms = 9999, 0.7 ms = 6999.
TCB0.CCMP      = stepPeriodUs * 10 - 1;
TCB0.CTRLB     = TCB_CNTMODE_INT_gc;          // periodic interrupt
TCB0.INTCTRL   = TCB_CAPT_bm;
CPUINT.LVL1VEC = TCB0_INT_vect_num;           // high priority: cuts into the USART and millis ISRs
TCB0.CTRLA     = TCB_CLKSEL_CLKDIV1_gc | TCB_ENABLE_bm;   // start; stop it when the move ends
```

**The ISR does one step and nothing else:**

```c
ISR(TCB0_INT_vect) {
  TCB0.INTFLAGS = TCB_CAPT_bm;
  // Hall resync, exactly as in advance() today, reading the pin directly (VPORTB.IN, PB5)
  // next half-step pattern: PB0..PB3, written in ONE atomic port write
  //   PORTB.OUTTGL = (VPORTB.OUT ^ pattern) & 0x0F;
  // currentStepPos++ and wrap at totalStepsPerRev
  // ramp: load the next interval into TCB0.CCMP (see "Acceleration")
  // if (currentStepPos == targetStepPos) { stop TCB0, release coils, arrived = true; }
}
```

**The main code only sets a target:**

```c
void moveToIndex(int idx) {          // now returns immediately
  ...work out the target step as today...
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { targetStepPos = target; targetIndex = idx; }
  currentFlapIndex = -2;             // "in motion" (-2 already means "not on a known flap")
  start TCB0 if it isn't running;
}
// in loop(): if (arrived) { arrived = false; currentFlapIndex = targetIndex; saveState(); }
```

**Retargeting is free** because the reel only turns one way. A new character just overwrites
`targetStepPos`, and the reel carries on forward from wherever it is. If the new flap is just
behind the current position, it goes most of the way round, as today.

#### Why it can't stutter

A step can only be late by however long interrupts are blocked when the timer fires. On v5:

| What blocks it | Worst case |
|---|---|
| Getting into the ISR | ~0.5 µs |
| `micros()` reading its counters (`cli`) | ~3 µs |
| `EEPROM.write` starting the write (`cli`, megaTinyCore `EEPROM.h:107`) | ~1 µs |
| `_PROTECTED_WRITE` | 4 cycles |
| USART RX and `millis()` ISRs | 0 (the step ISR is level 1 and preempts them) |

So a step is at most ~5 µs late out of 700 µs (<1%). Replies, EEPROM, dumps and restores no
longer touch the motor at all. The ISR costs ~15 µs per step (~2% CPU at 0.7 ms).

**v5 only.** On v4, SoftwareSerial masks interrupts for ~1 ms per received byte, so steps would
still slip during bus traffic. Fine for this wall (all Driverv5); drop v4 or accept it there.

#### Acceleration (probably needed for any real speed-up)

A stepper can **start from rest** only up to its pull-in (start-stop) rate. Once moving, it can
run faster, up to its pull-out rate, but only if it gets there gradually. 1 ms per half-step
(~15 RPM at the output) is already around where many 28BYJ-48s top out from a standstill, so
going meaningfully faster most likely needs a ramp. Slowing down before the target also helps at
higher speed, so the rotor doesn't coast past the last step.

The ISR already loads the next interval each step, so a ramp is a table lookup:

```c
// rampTable[0] = slow start interval … rampTable[N-1] = cruise interval (precomputed;
// no division in the ISR). N ≈ 100–200 entries, a few hundred bytes of flash.
uint16_t remaining = stepsToTarget();
if (rampIdx < N - 1 && rampIdx < remaining) rampIdx++;   // speeding up
if (rampIdx > remaining) rampIdx = remaining;           // slowing down for the target
TCB0.CCMP = rampTable[rampIdx];
```

The same table works forwards for speeding up and backwards for slowing down.

**Retargeting and the ramp:** if the reel is at cruise speed and the new flap is closer than the
slow-down distance, there are three options:

1. stop harder than the ramp allows;
2. overshoot and go round again (nearly a full revolution on a one-way reel, the worst choice);
3. keep the ramp short (~2 flaps) so a full stop nearly always fits.

Go with 3. The code above already does 1 for the rare too-close case. A missed step there is
corrected at the next magnet pass.

**Second speed limit, the flaps:** each flap falls under gravity. If the drum reaches the next
flap before the last one has landed, flaps bunch, flutter or blur. On many split-flap designs
that, not the motor, sets the top speed. At 0.7 ms per half-step (~2.9 s per revolution) each
flap has a few tens of ms. Probably fine, but watch it on the bench.

#### Things to work out

- **Shared variables.** `currentStepPos`, `targetStepPos` and the Hall state are written by the
  ISR, so make them `volatile`. They're 4-byte `long`s, so every main-code read or write needs
  `ATOMIC_BLOCK`. Audit **every** reader of `currentStepPos`/`currentFlapIndex`: the `v`/`A`/`Q`
  replies, `saveState()`, `gotoRawStep`, the nudge `s`, calibration.
- **`lastHallState`** is a `static` inside `advance()`. It becomes a global shared by the ISR and
  the blocking paths, so the magnet-edge resync stays right.
- **The blocking paths stay blocking:** homing (`h`, and the first move when the position is
  unknown), calibrate, `T`, `M`, `measureOneRev`, `detectHallPolarity`. They're maintenance and
  rare. Each one must **stop TCB0 and cancel any move first**, so two pieces of code never drive
  the coils. Homing could become part of the state machine later, but it doesn't need to.
- **Coil writes** go straight to PORTB with `OUTTGL` (atomic, one instruction), not
  `digitalWrite()`, which is slower and has `cli` paths. Nothing else in the firmware should
  write PORTB bits 0–3 except `releaseMotor()`, and that must stop the timer first.
- **`releaseMotor()` straight after the last step:** at higher speed the reel may coast. If flaps
  overshoot, keep the coils on for ~20–50 ms after `arrived` before releasing (`loop()` can do
  that with `millis()`; it doesn't need to be exact).
- **EEPROM:** `saveState()` only on arrival, from `loop()`, never in the ISR. Retargeting
  mid-move then means fewer EEPROM writes, not more.
- **`stepPeriodUs`** replaces `stepDelay`. #3's tuning command (`k<µs>`) would just set `CCMP`,
  and could later be stored in EEPROM (`0xCE`–`0xCF`, `0xFFFF` = default) so the speed changes
  over the bus without a reflash.
- **Flash/RAM:** the v5 build uses ~13.7 KB of the ~15.3 KB image space. This adds a couple of
  hundred bytes plus the ramp table.
- **Gateway / Companion / contract:** nothing breaks. Once every module runs this, pages could
  be sent faster than `settleMs: 4000`, but that's a CONTRACT.md change. Gate it on module
  firmware version (old and new modules may share a wall during rollout).
- **Rollout:** after Phase 1 bring-up on stock v36. The bus bootloader can push the new image to
  the whole wall in under a minute, and the bootloader itself doesn't change.

#### How to find the speed numbers (bench)

Use the bench-test sketch (`Kevin Splitflap/arduino_test/module_test/module_test.ino`), which
moves the drum exactly like v36, with flaps fitted and at the real supply voltage:

1. **No ramp:** shorten the interval until starts fail or buzz, or stops land a step off. That
   is the start-stop limit.
2. **With a ramp:** push the cruise interval until the reel loses steps (use the `M` test from #3:
   per-revolution counts go up) or the flaps stop landing cleanly.
3. Use ~70–80% of each limit across the wall (motors, flaps and supplies vary across 45 modules).

If the speed you want is under the start-stop limit, skip the ramp and just set the interval.

**Effort:** a day or two plus bench time. Under a few hundred lines, all in the module
firmware. Most of the risk is in the shared-variable audit, not the stepping code.

### 6. Bug: `nudge()` (`s<n>`) moves the home but leaves the position counter in the old frame

Flagged in the learning guide (Part 9, note 5), and confirmed by reading the code.

**Where:** `nudge()` (`src/SplitFlapUniversalFirmware.cpp:1785`), called from the `s<n>` command
(parser state 7, `:2663`). Related: the `o<n>` handler (state 5, `:2655`). Line numbers are for
the v36 working tree.

**Today:**

```cpp
void nudge(int n) {
  long fwd = n % totalStepsPerRev;
  if (fwd < 0) fwd += totalStepsPerRev;
  for (long k = 0; k < fwd; k++) advance(1);   // each step does currentStepPos++
  releaseMotor();
  stepsFromHallToZero = (stepsFromHallToZero + n) mod totalStepsPerRev;   // new home
  saveHomeOffset();
  // missing: currentStepPos is still counted from the OLD home
}
```

`currentStepPos` means "steps from flap 0", and flap 0 is defined by the home offset. The nudge
moves the reel n steps **and** moves flap 0 n steps, so the reel is at the same position
relative to the new home as it was before. But `advance()` added n to `currentStepPos`, and
nothing takes it off again.

**What goes wrong** (the usual calibration flow: home, nudge, check):

1. `m5h`: the reel is at flap 0, `currentStepPos = 0`.
2. `m5s5`: the reel moves 5 steps and the offset grows by 5. The reel *is* at the new flap 0,
   but `currentStepPos = 5`.
3. `m5-C`: `moveToIndex()` computes `target − 5` steps, so the reel lands **exactly where it
   would have without the nudge**.

The nudge looks as though it did nothing, so the natural reaction is to nudge again, which
overcorrects. The error clears itself only when the reel next passes the magnet: `advance()`'s
Hall resync then sets `currentStepPos = totalStepsPerRev − stepsFromHallToZero` using the new
offset. A move from flap 0 to a later flap usually doesn't pass the magnet (it sits just before
flap 0), so the error typically survives the first check move or two.

**Fix:** after the move, take the nudge back off the counter. The reel hasn't moved relative to
the new home:

```cpp
  // The reel moved n steps and so did flap 0: relative to the new home it hasn't moved.
  long p = (currentStepPos - n) % totalStepsPerRev;
  if (p < 0) p += totalStepsPerRev;
  currentStepPos = p;
  saveState();          // keep the saved position right when auto-home is off
```

- This works from any starting position, not just after homing, and for negative `n`
  (`fwd = T + n` adds `T + n`, which is `+n` mod T).
- It also works if the nudge itself passes the magnet. During the move, the Hall resync still
  uses the **old** offset, because the offset only changes afterwards. So the counter stays in
  the old frame throughout, and subtracting `n` converts it.
- `currentFlapIndex` stays as it is: the reel is still on the same flap, now better centred.
  That's the point of a nudge.
- `saveState()` was also missing: with auto-home off, the saved position (`0x07`) would be
  stale until the next move.

**Related: `o<n>` (set offset directly)** has the same mismatch without any motion. It changes
`stepsFromHallToZero` but not `currentStepPos`, so the counter is off by `(new − old)` until the
next magnet pass or `h`. Either apply the same correction there
(`currentStepPos -= new − old`, wrapped) or document that `o` must be followed by `h`. The gateway
dashboard and `restore.cpp` should be checked for whether they already home after setting `o`.

**Test (bench, one module):**
1. `m5h`, then `m5s20`, then `m5-` followed by a character a few flaps after the blank. Before
   the fix it lands 20 steps short of where the new offset says. After the fix it lands on the
   new position.
2. The same with `m5s-20`.
3. Nudge from a flap other than 0 (`m5-C`, then `m5s10`, then `m5-E`).
4. Nudge by more than the distance to the magnet, so the nudge itself passes the magnet.
5. `m5o<n>` followed by a move, before and after whatever `o` fix you choose.
6. Check `m5A` (`curIndex`) and, with auto-home off, reboot and confirm the restored position
   is right.

**Effort:** a few lines. Worth folding into the next firmware change (for example #4, which
rewrites the position handling anyway and must keep this right).

---

## Whole bus (module firmware, bootloader, gateway, tools)

### 2. Faster RS-485 bus: 9600 → 115200 baud

**Where:** every device and tool on the bus. That means the module firmware, the module
**bootloader** (only replaceable over UPDI), the gateway, `provision.py`, `tools/busflash.py`,
the mock and the docs. Line numbers below are for module firmware v36 and gateway 4.4.0.

**Today:** everything runs at 9600 8N1, so one byte takes 1.04 ms. The speed isn't one setting.
It is written into code in several places, and it is also baked into dozens of **millisecond
constants** that were sized from 9600-baud frame times. Changing `rs485.begin(9600)` alone
leaves the bootloader deaf, the broadcast reply slots 10× too wide, and some timing assumptions
quietly wrong.

**Idea:** run the whole bus at **115200**, make it a single compile-time constant (`BUS_BAUD`)
in the module and bootloader builds, and derive every byte-time constant from it. Since every
board will be a v5, drop the v4 code path entirely. That's what makes this possible:
SoftwareSerial at 10 MHz can't do 115200.

#### What gets faster (and what doesn't)

| | 9600 | 115200 |
|---|---|---|
| One byte | 1.04 ms | 87 µs |
| Display frame `m05-A\n` (6 B) | 6.3 ms | 0.5 ms |
| `v` reply (~33 B) | 35 ms | 2.9 ms |
| Worst `A` reply (~709 B with checksum) | 740 ms | 62 ms |
| `m*v` roll call, IDs 0–44 | ~4.5 s | ~0.7 s (with the new slots below) |
| `m*A` full dump, IDs 0–44 | ~31 s | ~3.5 s |
| Bus firmware update (240 pages) | ~41 s | ~8 s (≈5 s if the page gap is trimmed) |
| Showing a full 45-cell page | ~0.7 s of pacing + motor time | **about the same** |

The win is in queries, dumps, restores, roll calls, soak tests and bus updates. **Showing text
on the wall barely changes.** It is dominated by the gateway's per-module pacing (`step_ms`, 15 ms
× 45 = 675 ms) and by the motors (up to ~4 s per revolution), not by the wire. See "Pacing"
below.

#### Why 115200 and not faster

- **Module transceiver:** the Driverv5 board uses a **THVD1400** (U3; the schematic symbol is
  named SN65HVD72DR, but the value is THVD1400DR). It's a slew-rate-limited part, rated about
  **500 kbps** (confirm on the TI datasheet). 115200 leaves 4× headroom. The slow edges also mean
  the star topology from the power board needs no extra care at this speed: three row branches
  plus the gateway, with one 120 Ω terminator on JP1.
- **Gateway transceiver:** check the Waveshare ESP32-S3-RS485-CAN schematic for its part and
  rated speed. It's almost certainly fine at 115200, but confirm. The gateway already drives DE
  itself (`RS485_EN_PIN 21`, `UART_MODE_RS485_HALF_DUPLEX`), so there's no auto-direction RC
  circuit tuned to a baud rate.
- **ATtiny1616 at 10 MHz** (it has to stay 10 MHz: the logic rail is 3.3 V):
  - The USART's fractional divider handles any rate up to 625 kbaud (BAUD register ≥ 64).
    115200 → BAUD = 347.2 → 347, an error of 0.06%.
  - The CPU cost per byte is the real limit. At 115200 there are ~870 cycles per byte for the
    ISR plus `loop()` and parsing. At 500k there are only ~200, which is marginal for the
    firmware's per-byte loop and for the bootloader's polled hex-decode plus bitwise CRC.
- **Diminishing returns:** above ~115200 the fixed costs dominate. Those are:
  - EEPROM writes (~4 ms each);
  - flash page writes (~4 ms);
  - `millis()`'s ~1 ms resolution;
  - carrier sense;
  - FreeRTOS scheduling on the gateway;
  - motor moves.

  250000 would save maybe another 10–20% on dumps and almost nothing elsewhere.
- **Tools:** every USB–RS485 adapter does 115200.

#### The key distinction: two kinds of timing constant

1. **Byte-time constants** were sized from how long something takes on the wire at 9600. These
   must be **recomputed** for the new baud: slot widths, carrier-sense windows, idle timeouts,
   status-reply waits, guard gaps.
2. **Physical constants** are set by EEPROM and flash write times, the motor, inrush, the chip
   restarting, or the gateway's tasks. These must **not** be scaled with the baud. Examples: the
   page-write gap, the `mXW` settle time, the go/enter waits, `step_ms`, the boot stagger.

Several constants are **paired across the two codebases**. The module's slot widths match the
gateway's broadcast window, and the module's 200 ms parser timeout matches the gateway's
`BUS_GAP_LONG_MS = 260`. Change both sides of a pair together.

#### Module firmware (`SplitFlapUniversalFirmware/src/SplitFlapUniversalFirmware.cpp`)

| Line | Today | Change |
|---|---|---|
| 2278 | `rs485.begin(9600)` | `rs485.begin(BUS_BAUD)`, with `-DBUS_BAUD=115200` in `platformio.ini`. |
| 880–890 | `UsartBus::begin` divisor + `OSC20ERR3V` correction | Already generic. Add `static_assert` that the divisor is ≥ 64. Note that the correction fixes the **baud only**: `millis()` still runs on the uncorrected oscillator (±1–2%), which matters for slots (below). |
| 583–593 | Slots sized for 9600: `REPLY_LEADIN_MS 30`, `REPLY_SLOT_MS 100`, `REPLY_ALL_SLOT_MS 700`, `CSMA_LISTEN_MS 20` | Derive from `BUS_BAUD` (see "New slot timing"). Delete `REPLY_DIRECT_MS`: nothing uses it since direct replies became synchronous. |
| 1297–1303 `txBegin` | `delayMicroseconds(200)` before the start bit | Keep it as a **fixed µs turnaround**, not scaled. It gives the gateway time to drop its driver after its last byte. Confirm the margin on a scope (gateway DE falling → module DE rising). |
| 1304–1319 `txEnd` | `delay(2)`, then **drain everything in the receive ring** | On v5, `finish()` already waits for the stop bit and the USART drops DE itself, so the `delay(2)` is v4-only. Remove it. The drain was for v4 self-echo; with /RE tied to DE (verify on the Driverv5 schematic) the receiver is off during TX and there's no echo. **At 115200 the drain becomes dangerous:** anything the gateway sends within those 2 ms (a whole command is 0.5 ms) is silently thrown away. Keep only the overflow bookkeeping. |
| 1123 | `RX_RESYNC_GAP_MS 5` ("bytes ~1 ms apart") | Can drop to 2–3 ms. Keep it ≥ 2 because `millis()` ticks ~1 ms. |
| 3005 | 50 ms of silence → synthetic `\n` | Bytes are now 87 µs apart. 10 ms is plenty and makes unterminated commands respond faster. Off the critical path (the gateway terminates everything except direct `v`), so this is optional. |
| 3048 | Catch-all 200 ms parser reset | Can drop to ~50 ms. **Paired with the gateway's `BUS_GAP_LONG_MS 260`** ("over the module's 200 ms resync"). |
| 128-byte ring (`busRing`, 864–876) | Fills in 132 ms at 9600; in **11 ms** at 115200 | Same logic, but a busy module (mid-move, mid-EEPROM) overflows after far less traffic. Consider 256 bytes if RAM allows (check the build's RAM figure). `rxCut` is `uint8_t` and `available()` would max out at 255, so it still fits. |
| Comments | "9600", "~1 ms per byte", "~0.75 s" in the header (186–190), config (578–580), 1116–1122, 1294–1296, 3011–3013, 2938–2947 | Update. |
| `#if SF_BOARD == 4` blocks, `SoftwareSerial`, `RS485_RX/TX/DE` pins, `[env:v4]`, `-D_SS_MAX_RX_BUFF=128` | v4 support | Delete (v5-only). Keep the PC0 strap check and the board tag `5` in the image: they cost little, and the gateway's update code reads the tag. |

**Unchanged:** the watchdog (2 s ≫ 62 ms worst reply), advertisement timing (10–15 s), the
boot stagger, `delay(20)`/`delay(50)` before the `mXack` and calibrate replies (gateway
turnaround), all EEPROM and motor timing, and the `static_assert`s on `workBuf`.

**Interrupt-masked sections:** at 115200 the USART's 2-byte receive buffer covers only ~260 µs
with interrupts off (it was ~3 ms at 9600). The firmware's own ISR is µs-short. Check whether
megaTinyCore's `EEPROM.write` busy-waits for the previous write **with interrupts disabled**: the
core isn't installed here, so read `EEPROM.h` in the PlatformIO package. If it does, a restore
or factory reset loses received bytes. The overflow guard catches the loss and counts it in
`rxOverflows`, but the frame is still lost.

#### New slot timing (module and gateway, change together)

The rules: slot width ≥ longest reply on the wire + `CSMA_LISTEN_MS` + margin. `CSMA_LISTEN_MS` <
the quiet gap an on-time slot sees, so an on-time reply is never held back. And everything
should be a few `millis()` ticks wide.

| Constant | 9600 | 115200 (proposed) | Why |
|---|---|---|---|
| `CSMA_LISTEN_MS` | 20 | 5 | ≫ the gap between bytes in one frame (µs), ≥ several ms ticks |
| `REPLY_LEADIN_MS` | 30 | 10 | ≥ CSMA + gateway turnaround |
| `REPLY_SLOT_MS` (`v`) | 100 | 15 | 3.3 ms frame + 11.7 ms quiet ≥ CSMA |
| `REPLY_ALL_SLOT_MS` (`A`) | 700 | 80 | 62 ms worst frame + 18 ms quiet ≥ CSMA |

Better still, compute them in the source from `BUS_BAUD` and the worst-case frame lengths the
`static_assert`s already know. Add a `static_assert(slot − frame ≥ CSMA_LISTEN_MS + 2)` so a
future change can't make on-time replies late.

**Clock drift between modules:** each module's `millis()` can be ±1–2% off (the oscillator
correction applies only to the baud). Over a 3.5 s `m*A` train, two neighbours can drift up to
~140 ms relative to each other, more than one 80 ms slot. That's not a collision risk: carrier
sense makes the later one wait. But replies may arrive **out of ID order**, and the gateway's
window has to allow for it. This was already true at 9600 and was hidden by the 100/700 ms
slots and the v4 `millis()` lag. The v4 lag (~15% slow) is gone on v5, so the gateway's "+20%
for drift" can become ~+5%. Keep a fixed tail.

#### Bootloader (`SplitFlapUniversalFirmware/bootloader/`)

**The bootloader can only be replaced over UPDI.** Every module carries the bootloader it was
last flashed with, and a bus update never touches it. So the baud **must be the same in the
firmware and the bootloader**. A split, such as a fast firmware and a 9600 bootloader with the
gateway switching speed mid-update, isn't safe: modules not in update mode would read 9600
bootloader traffic at 115200 as garbage that can happen to look like `m…` frames.

| Where | Today | Change |
|---|---|---|
| `bootloader.c:145` | `USART0.BAUD = 4167 + 4 * (int8_t)SIGROW.OSC20ERR3V;` — the base **and** the correction factor (4167/1024 ≈ 4) are 9600-only | 115200: base **347**, factor 347/1024 ≈ 0.34 per count. The ATtiny has **no hardware multiplier**, so use shifts: `347 + (e >> 2) + (e >> 4)` with `e` the `int8_t` value (0.3125/count, under 0.2% residual error). It must give the same divisor as the firmware's formula (to within a count) for every possible `OSC20ERR3V`. Check that in a host test. |
| Code size | The v5 build is **1,018 of 1,020 bytes** (2 spare) | The new correction probably costs a few bytes. Make room by removing the **PC0 strap check** from `SET_UP_UPDATE_MODE` (`bootloader.c:139–141`; pointless once there are no v4 boards), about a dozen bytes. `build.py` refuses an oversize build, so you'll know. |
| `uart.S` | v4 bit-banged `rx`/`tx`, cycle-counted for 9600 (`HALF_BIT_LOOPS 171`) | Delete `rx`/`tx`. v5 uses `half_bit` only as a delay: 64 × 52 µs ≈ 3.3 ms of turnaround before the status reply (`bootloader.c:264`). It still works, as a plain delay. Rename it or replace it with a C loop so it doesn't claim to be a "half bit" any more. |
| `BL_VERSION` | 2 on v5 | Bump to **3**, so `Q`'s last field and the update-mode status show which bootloader (which baud) a module has. The gateway parses status frames **by length** (41/42 bytes, `modfw.cpp:46–78`), not by version, so keep the trailing board byte and the frame stays compatible. |
| `test/host_hal.h:24` | `BIT_TIME (1.0 / 9600)` | `1.0 / BUS_BAUD`. Rerun `build.py --test` and fix any test whose timing expectations assumed 9600 byte times ("frames sent too close together", the watchdog cases). |
| `build.py`, `merge.py` | Build/merge v4 and v5 | v5 only. Pass `-DBUS_BAUD` to the bootloader build from the same place `platformio.ini` gets it, so the two can't disagree. Commit the rebuilt `bootloader-v5.hex`, which `merge.py` puts in every firmware image. |
| Per-byte CPU | Polled RX, hex-decode plus bitwise CRC per byte, ~100–150 cycles | Fine at 115200 (~870 cycles per byte). Another reason not to go to 500k. |
| Comments | `bootloader.c:29`, `134–135`, `uart.S:2` | Update. |

**Unchanged:** the frame format, the 8 s watchdog, the `0xB007` request handshake, the page and
CRC logic, and the EEPROM-untouched guarantee.

#### Gateway (`SplitFlapGateway/src/`)

The gateway's baud is already **runtime-configurable**: `cfg.rs485Baud`, Settings → bus, and
`rs485.end(); rs485Begin()` on change. But:

- **`DEFAULT_BAUD` (`common.h:147`) is only used when NVS has no value** (`config.cpp:49`). A
  gateway that has ever saved its settings keeps **9600** after a reflash. Set 115200 in Settings
  (or clear NVS) as part of the rollout. Better: once the change is done, make `DEFAULT_BAUD` a
  build constant and stop persisting it, so it can't drift from the modules.
- Byte-time constants to recompute (and pairs to keep in step with the module):

| Constant / place | Today | Change |
|---|---|---|
| `TX_BUS_GUARD_MS` (`common.h:163`) | 12 ("12 byte-times at 9600") | ~3 ms. It only has to span gaps *within* a frame. Reply trains are protected by `busHold`, not by this guard. |
| `soakBroadcastWindow` (`modules.cpp:909–912`) | Hard-coded `700`/`100` ms slots, `700`/`40` ms reply, +20% drift | The new module slots (80/15), reply 62/3 ms, +5% drift, the same fixed tail. **Same numbers as the module, changed together.** |
| `BUS_GAP_SHORT_MS` / `BUS_GAP_LONG_MS` / `BUS_RETRY_GAP_MS` (`common.h:219–221`) | 150 / 260 / 300 | `LONG` is "over the module's 200 ms resync". Shrink it with the module's catch-all timeout (e.g. 50 → ~80). `SHORT` can drop a lot. |
| `MODULE_PROBE_SPACING_MS` | 150 | ~30. |
| `RESTORE_ENTRY_GAP_MS` | 60 ("~12 ms on the wire + ~7 ms EEPROM") | ~15 (≈1 ms on the wire + EEPROM). `RESTORE_MXW_SETTLE_MS 1000` is physical: keep it. |
| `RESTORE_VERIFY_TIMEOUT_MS`, `sfSendVersionAndWait(…, 700)`, `web.cpp:844` (`500 + id×100`) | Sized for 9600 replies | Can shrink. As upper bounds they're harmless if left alone. |
| `modfw.h:48–51` | `PAGE_GAP 20`, `STATUS_WAIT 250` ("reply takes ~90 ms"), `GO 500`, `ENTER 200` | `STATUS_WAIT` → ~50 (the reply is ~8 ms now). `PAGE_GAP` is physical (page erase, write and read-back ≈ 5 ms): ~10 is safe, and 20 is fine. `GO`/`ENTER` are physical: keep. |
| `busHold("identify", …, 20000)` (`web.cpp:2607`) | 20 s for the `m*v` train | Fine as is (the train is now <1 s). Shrink it if you want Identify to finish faster. |
| `sfIsDirectVersionQuery` no-newline exception (`rs485.cpp:441–460`) | Exists because at 9600 the trailing `\n` (1 ms) was still on the wire when the module answered | At 115200 the `\n` is 87 µs, well inside the module's 200 µs turnaround, so it's probably unneeded. Leave it (harmless) but **re-run the "40 out of 40" test** with and without the newline. |
| UART buffers (`rs485Begin`) | 1024 B RX ring + 128 B HW FIFO | Fine. The FIFO now covers 11 ms of preemption instead of 133 ms, but the driver ISR empties it into the 1024 B ring. |
| Comments and `openapi.yaml` examples (`baud: 9600`) | | Update. |

#### Pacing (`step_ms`), the one to measure rather than guess

`DEFAULT_STEP_MS 15` (gateway `common.h`, the mock, and inherited by the Companion) was measured
on a v4 wall: on 60 modules, 15 ms lost 27 frames, 20 ms lost 9, and 25 ms was stable. A frame is
6 ms on the wire at 9600, so the pacing isn't just byte time. The losses came from either:

- **receive-side limits:** v4 SoftwareSerial, ring overflow while a neighbour's motor starts,
  which faster v5 hardware could improve; or
- **physics:** motor inrush and supply noise as reels start within milliseconds of each other,
  which no baud rate fixes.

**Don't change it blindly.** After the switch, rerun the soak test with a `step_ms` sweep
(5/10/15/25) on the real 45-module v5 wall, and watch `rxOverflows`, `crcErrors` and `Q`'s
brown-out bit. Only lower the default (in the gateway, `mock_gateway.py` and anything that
documents it) if the data says so. If the losses turn out to be inrush, the ripple idea in #1 is
the better lever.

#### Tools, mock and docs

| File | Change |
|---|---|
| `provision.py:435` | `--baud` default 9600 → 115200 (the flag already exists). |
| `tools/busflash.py:42, 58` | `BYTE_TIME = 10/9600` and `Serial(port, 9600)` are hard-coded. Add a `--baud` flag (default 115200) and derive `BYTE_TIME`. Its gaps (`PAGE_GAP` etc.) match `modfw.h`: change them together. |
| `platformio.ini` | `monitor_speed 9600` and the comment near it. **`upload_speed = 57600` is SerialUPDI programming speed, not the bus: leave it.** The same goes for `flasher/updi.js` (`BAUD = 57600`). |
| `mock-gateway/mock_gateway.py:430, 451` | Reports `"baud": 9600` in `/api/status` and `/api/config`. Change it to match the real gateway, then re-run CONTRACT.md §10 (CLAUDE.md: the mock stays faithful). |
| Companion `backend/tests/test_gateway.py:17` | A fixture with `"baud": 9600`. Cosmetic. |
| `README.md`, `ARCHITECTURE.md`, `BUS-UPDATE.md` (timing table), `SETUP.md`, `FLASHING.md`, `openapi.yaml` | Every "9600" and every derived timing ("~0.75 s dump", "~40 s update", "100 ms slot"). |

#### Rollout order (this is what keeps it cheap)

1. **Decide before the 45-module UPDI flash.** Changing the bootloader later means visiting all
   45 modules with a UPDI programmer again. Today none are flashed, so it's nearly free.
2. **Bring up 1–2 bench modules on stock v36 at 9600 first.** That follows Phase 1's "no
   firmware changes" rule. It also matters because v5 **receiving** and v5 **bus updates** have
   never been tried upstream, even at 9600. Prove the hardware there, so a later fault is clearly
   about the baud change and not the board.
3. Implement the firmware, bootloader, gateway and tool changes. Run `bootloader/build.py --test`
   and check the build's flash and RAM figures.
4. Re-flash the bench modules over UPDI (fuses unchanged) and set the gateway to 115200. Test:
   - adverts;
   - `mXI`;
   - `v`/`A`/`Q`/`d`;
   - checksummed frames;
   - ranged `m*v`/`m*A`;
   - a **full bus update** (`U` → `P` → `S` → `G`).

   Scope the turnaround: gateway DE falling → module DE rising.
5. Flash the remaining 43 modules directly with the new image.
6. Soak test, `step_ms` sweep, CONTRACT.md §10, then update the docs.

#### Things to watch out for

- **This is a permanent fork from upstream on the wire.** Every upstream release `.hex`/`.bin`,
  and the hosted web flasher (it bundles upstream images), are 9600:
  - A module UPDI-flashed with one gets a 9600 bootloader too and is **deaf on this bus** until
    it's re-flashed over UPDI.
  - A module **bus-updated** with an upstream `firmware-update-v5.bin` gets 9600 firmware under
    a 115200 bootloader. To recover it, set the gateway to 9600, send it `~HHHHm<id>U`, set the
    gateway back to 115200, and bus-update it with the right image.

  Re-apply this change on every upstream merge, and always build images from this repo.
- **There's no way to talk to a module at an unknown speed.** Keep the baud in one place
  (`BUS_BAUD`) for the firmware and bootloader builds, and print it in the build output.
  Consider putting the baud in the image (next to the board tag at 0x3FFC; 0x3FFD is free) and
  having the gateway refuse to send an image whose baud doesn't match its own.
- **The gateway setting is persisted (NVS) and the module setting is compiled in.** Change the
  gateway's from the dashboard. If they ever disagree, the wall goes silent but nothing is
  damaged: set the gateway back.
- **The firmware's own docs say v5 receiving is untested.** Step 2 isn't optional.

---

## Gateway firmware (`SplitFlapGateway/`)

- The gateway's share of the bus speed change is listed under #2.

### 5. Checksum every display frame, not just reads and writes

**Where:** `handleApiSendBatch()` (`src/web.cpp:286`, the `/api/rs485/batch` route the Companion
draws every page through), `handleApiDisplayCells()` (`web.cpp:1266`), `sfSendCharRaw()`
(`src/modules.cpp:488`, behind `/api/flap/text`). The checksum helpers already exist:
`rs485SendChecked()` (`src/rs485.cpp:33`), `sfModuleChecksums()` and `sfSendToModule()`
(`modules.cpp:1262–1278`). Line numbers are for gateway 4.4.0.

**Today:** module firmware v33+ accepts `~HHHH<frame>\n` (CRC-16/CCITT-FALSE; see CHECKSUMS in
the module firmware header). The gateway checksums the exchanges where a bad frame does lasting
damage (reads, `w` position writes, restores, the bus-update enter command), but **display
frames go out plain**. The Companion sends `"m05-A\n"`, and the batch handler passes it to
`rs485Send()` / `rs485SendScheduled()` unchanged. The reason given (`src/common.h:223–229`) is
traffic: "five extra bytes on a six-byte display command is 80% more traffic for a frame that
the next update overwrites". Backward compatibility isn't the reason: the same comment notes
that older firmware skips the prefix and runs the frame unchecked, so checksummed frames are
safe on a mixed wall. In any case, this wall will be all v5 boards on v36.

With a plain frame, a flipped bit on the wire either:
- changes the character, so the module shows the wrong letter until the next update. For a
  static answer that might be minutes. The gateway's display tracking (`sfTrackFromFrame`)
  still believes the right letter is showing, so nothing notices.
- or changes the address, so the wrong module moves.

**Idea:** checksum every display frame. A corrupted frame is then dropped and counted in the
module's `crcErrors` (read by `Q`), not shown. Keep **plain frames for typing by hand**: the Bus
Monitor "Send Frame" box and `/api/rs485/send` stay as they are.

**Cost:**
- **Bytes:** `m05-A\n` is 6 bytes and `~C500m05-A\n` is 11 (5 and 10 for IDs 0–9). A full
  45-module page is about 260 bytes plain and 485 checksummed, ~0.27 s versus ~0.5 s on the
  wire at 9600. That's still well under the time the motors spend moving (up to ~4 s).
- **With today's pacing it's nearly free.** The batch is paced start-to-start at `step_ms`
  (default 15 ms). An 11-byte frame is ~11.5 ms on the wire, so it still fits inside each 15 ms
  step, and a full page still takes ~45 × 15 = 675 ms. Check that the gap left between frames
  (~3.5 ms) is still enough for the receivers. If not, 17–20 ms pacing costs ~0.1–0.2 s per page.
- **At 115200 (#2)** the cost disappears: an 11-byte frame is ~1 ms.

#### Implementation sketch

- **One helper** that turns a plain frame into a checksummed one in a caller-supplied buffer
  (strip the trailing `\n`, CRC the rest, write `~%04X` + frame + `\n`). `rs485SendChecked()`
  already does exactly this, but sends at once. The paced paths need the bytes so they can be
  queued with `rs485SendScheduled()`.
- **`handleApiSendBatch()`:** for each frame that starts with `m` (not already `~`) and is
  addressed to a module where `sfModuleChecksums(id)` is true (v33+), wrap it before scheduling.
  For a broadcast `m*…`, wrap it only if every known module is v33+. Frames that are already
  checksummed or not module commands go through unchanged. This makes it transparent to the
  Companion: it keeps sending plain frames, and the gateway adds the checksum.
- **`handleApiDisplayCells()`** and **`sfSendCharRaw()`:** same rule. `sfSendCharRaw` can just
  call `sfSendToModule()` for a single address.
- **`TX_MAX_BYTES` and the schedule queue:** check that a frame plus 5 bytes still fits
  everywhere a frame is buffered.
- **Leave `/api/rs485/send` plain.** It's the hand-typing and debugging path.

#### Things to watch out for

- **A lost `~` degrades to a plain frame, not a lost frame.** The module's parser skips
  everything before the `m` and runs the command unchecked. That's no worse than today, and the
  message itself is intact (only one error, and it hit the `~`). Display frames have no reply,
  so the "plain reply means a failed exchange" rule doesn't apply.
- **One command per checksummed frame.** Display frames are already one per frame. Don't
  batch several `m…` commands into one checksummed frame.
- **Watch `crcErrors`.** It becomes a real health metric for the bus. A module or branch whose
  count climbs has a wiring, termination or noise problem that was invisible before.
- **Gateway changes come after Phase 1** (CLAUDE.md: the gateway stays stock for the first
  bring-up). This is wire-level only: the Companion and HA package don't change and
  CONTRACT.md's interface is the same. Still re-run §10 afterwards, as CLAUDE.md requires after
  any gateway change. `mock_gateway.py` needs no change unless it starts emulating the wire.
- **Upstream merges:** the change lives in the batch handler, so re-apply it if upstream
  rewrites that function.

---

## Companion / Pi side

_(nothing yet)_
