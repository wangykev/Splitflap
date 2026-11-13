/*
  Split-flap single module bench test  (Arduino Uno)
  ===================================================
  Checks one module (28BYJ-48 stepper, hall effect home sensor, flap drum)
  before the custom driver PCB is used.

  It moves the drum the same way SplitFlapUniversalFirmware v36 does, so what
  you measure here carries straight over to the real module:
    - same half-step table and the same FORWARD direction (the firmware walks
      the table backwards; the drum only ever turns one way)
    - same speed: a constant 1 ms per half-step, no ramp
    - same default 64-flap reel, 4096 steps/rev and home offset 2832
    - same homing: step until the sensor reads "magnet", then step the home
      offset to land on flap 0
    - same flap positions: flap i is at i * stepsPerRev / NUM_FLAPS steps past
      flap 0 (rounded down)
    - same sensor polarity auto-detection (p, and the first part of c)
    - a character that isn't on the reel homes to flap 0, like the firmware
  The values c and z print are the ones the module stores: stepsPerRev is its
  "total steps" and homeOffset is its "home offset" (module command o<n>, or the
  gateway dashboard's calibration page).

  WIRING
  ------
  The Uno pins cannot drive the motor coils directly: they need about 200 mA,
  and a pin gives about 20 mA. Use a ULN2003 driver board (the small red/green
  board that usually ships with the 28BYJ-48).

    ULN2003 IN1  -> D8      (the PCB drives ULN_IN1..IN4 from PB0..PB3 in this
    ULN2003 IN2  -> D9       same order, so keep it: swapping coils changes the
    ULN2003 IN3  -> D10      direction and the bench result stops matching the
    ULN2003 IN4  -> D11      real module)
    ULN2003 +    -> motor supply (5 V or 12 V, check the label on the motor!)
    ULN2003 -    -> GND (common with the Arduino GND)
    Motor plug   -> ULN2003 white socket (it only fits one way)

    Hall sensor VCC -> 5V
    Hall sensor GND -> GND
    Hall sensor OUT -> D2   (internal pull-up is on, so a bare A3144/AH3364
                             style open-collector sensor works without a resistor)

  A 5 V motor runs from the Uno 5V pin on USB power, but a separate 5 V supply
  is steadier. A 12 V motor needs a 12 V supply on the ULN2003 board.
  Always connect the grounds together.

  The onboard LED (D13) lights while the sensor sees the magnet.

  USE
  ---
  Open the Serial Monitor at 115200 baud, line ending "Newline", and type ?
  for the command list.

  Suggested order:
    1. s      sensor check: turn the drum by hand, watch for MAGNET DETECTED
    2. f 500  motor check: the drum should turn the way the flaps fall
              (if it turns backwards, the coil wiring differs from the PCB)
    3. c      detect sensor polarity and measure steps per revolution
    4. h      home: should land on flap 0 (the blank)
    5. Step with f until flap 0 lines up exactly, then z to save that as flap 0
    6. a      cycle through every flap
    7. x 50   stress test: 50 random flaps, reports missed steps
*/

#include <ctype.h>

// ----------------------------------------------------------------- pins ---
const uint8_t COIL_PINS[4] = {8, 9, 10, 11};   // ULN2003 IN1..IN4
const uint8_t HALL_PIN = 2;

// ------------------------------------------------------- module config ---
// The firmware's default reel (FLAP_CHARS), in drum order starting at flap 0.
// Lowercase r o y g b p w are the colour flaps and q is the double-quote flap.
// If your drum is printed differently, change this AND set the same set on the
// module (the gateway's flap-set setting), or the two will disagree.
const char FLAPS[] = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$&()-+=;q:%'.,/?*roygbpw";
const uint8_t NUM_FLAPS = sizeof(FLAPS) - 1;
static_assert(NUM_FLAPS >= 1 && NUM_FLAPS <= 64, "the firmware supports 1 to 64 flaps");

// Firmware defaults. c measures the real stepsPerRev (a 28BYJ-48 is about 4076);
// z or o sets homeOffset. Copy the measured values here to keep them.
long stepsPerRev = 4096;
long homeOffset  = 2832;            // half-steps from the sensor trigger to flap 0

// -------------------------------------------------------------- motion ---
unsigned int stepUs = 1000;        // per half-step; the firmware uses 1 ms (v command)
bool autoRelease = true;           // coils off after each move, like the firmware

// Half-step table, identical to the firmware's halfStepSequence; bit 0 = IN1 ... bit 3 = IN4.
// FORWARD walks it from the end to the start, exactly as the firmware's advance() does.
const uint8_t HALF_STEP[8] = {0b0001, 0b0011, 0b0010, 0b0110,
                              0b0100, 0b1100, 0b1000, 0b1001};

// --------------------------------------------------------------- state ---
uint8_t hallActiveLevel = LOW;     // the level that means "magnet"; p / c detect it
int8_t phase = 0;
long pos = 0;                      // half-steps past flap 0, 0..stepsPerRev-1 (firmware currentStepPos)
bool homed = false;
bool lastSensor = false;
int currentFlap = -1;

bool reportEdges = true;
bool edgeSeen = false;
long lastRevSteps = 0;             // steps between the last two sensor triggers
long stepsSinceEdge = -1;          // -1 until the first trigger of a move
long edgeCount = 0;
long maxDev = 0;

// ============================================================= helpers ===
bool sensorActive() {
  return digitalRead(HALL_PIN) == hallActiveLevel;
}

long modPos(long a, long m) {
  long r = a % m;
  return r < 0 ? r + m : r;
}

void writeCoils(uint8_t pattern) {
  for (uint8_t i = 0; i < 4; i++) {
    digitalWrite(COIL_PINS[i], (pattern >> i) & 1);
  }
}

void releaseCoils() {
  writeCoils(0);
}

void printFlap(int idx) {
  static const char COLOUR_CODES[] = "roygbpw";
  static const char *const COLOUR_NAMES[] = {"red", "orange", "yellow", "green",
                                             "blue", "purple", "white"};
  char c = FLAPS[idx];
  const char *colour = strchr(COLOUR_CODES, c);
  if (c == 'q') {
    Serial.print(F("'\"'"));
  } else if (colour && c) {
    Serial.print(COLOUR_NAMES[colour - COLOUR_CODES]);
  } else {
    Serial.print('\'');
    Serial.print(c);
    Serial.print('\'');
  }
}

// Like the firmware, snap the position to the trigger point, which silently
// corrects missed steps. Report the drift first: that is what this test looks for.
void onSensorEdge() {
  long expected = modPos(stepsPerRev - homeOffset, stepsPerRev);
  if (homed) {
    long dev = modPos(pos - expected + stepsPerRev / 2, stepsPerRev) - stepsPerRev / 2;
    edgeCount++;
    if (labs(dev) > labs(maxDev)) maxDev = dev;
    if (reportEdges) {
      Serial.print(F("  [sensor] trigger, position off by "));
      Serial.print(dev);
      Serial.println(F(" steps"));
    }
  }
  if (stepsSinceEdge >= 0) lastRevSteps = stepsSinceEdge;
  stepsSinceEdge = 0;
  edgeSeen = true;
  pos = expected;
}

// firmware advance(), same order: read the sensor before stepping.
void stepForward() {
  bool s = sensorActive();
  if (s && !lastSensor) onSensorEdge();
  lastSensor = s;
  digitalWrite(LED_BUILTIN, s);

  if (--phase < 0) phase = 7;
  writeCoils(HALF_STEP[phase]);
  delayMicroseconds(stepUs);

  if (++pos >= stepsPerRev) pos = 0;
  if (stepsSinceEdge >= 0) stepsSinceEdge++;
}

// Bench only: the firmware never turns backwards, so this loses the position.
void stepBackward() {
  if (++phase > 7) phase = 0;
  writeCoils(HALF_STEP[phase]);
  delayMicroseconds(stepUs);
  digitalWrite(LED_BUILTIN, sensorActive());
}

void beginMove() {
  lastSensor = sensorActive();   // the drum may have been turned by hand
  stepsSinceEdge = -1;
  writeCoils(HALF_STEP[phase]);  // re-engage the same phase it was released on
  delay(5);
}

void endMove() {
  if (autoRelease) releaseCoils();
}

// ============================================================== motion ===
void moveSteps(long n) {
  beginMove();
  if (n >= 0) {
    for (long i = 0; i < n; i++) stepForward();
  } else {
    for (long i = 0; i < -n; i++) stepBackward();
    homed = false;
    currentFlap = -1;
  }
  endMove();
}

// firmware homeModule(). It stops on the magnet LEVEL, not a fresh edge, so a
// drum parked on the magnet homes at once.
bool home() {
  Serial.println(F("Homing..."));
  beginMove();
  long limit = stepsPerRev + 500;
  long n = 0;
  while (!sensorActive() && n < limit) {
    stepForward();
    n++;
  }
  if (!sensorActive()) {
    endMove();
    homed = false;
    currentFlap = -1;
    Serial.println(F("  FAILED: the sensor never saw the magnet in one revolution."));
    Serial.println(F("  Check: sensor wiring/power, polarity (run p), magnet-to-sensor gap,"));
    Serial.println(F("  and that the drum actually turned (motor wiring / supply)."));
    return false;
  }
  lastSensor = false;            // so the first step below counts as the trigger
  for (long i = 0; i < homeOffset; i++) stepForward();
  endMove();
  pos = 0;
  homed = true;
  currentFlap = 0;
  Serial.print(F("  Magnet found after "));
  Serial.print(n);
  Serial.println(F(" steps, now on flap 0."));
  return true;
}

// firmware moveToIndex()
void goToFlap(int idx) {
  if (!homed && !home()) return;
  long target = (long)idx * stepsPerRev / NUM_FLAPS;
  long steps = modPos(target - pos, stepsPerRev);
  beginMove();
  for (long i = 0; i < steps; i++) stepForward();
  endMove();
  currentFlap = idx;
  Serial.print(F("  flap "));
  Serial.print(idx);
  Serial.print(F(" "));
  printFlap(idx);
  Serial.println();
}

// Exact match, like the firmware: lowercase letters are colours (and q), not letters.
int flapIndexOf(char c) {
  for (int i = 0; i < NUM_FLAPS; i++) {
    if (FLAPS[i] == c) return i;
  }
  return -1;
}

// firmware moveToChar()
void goToChar(char c) {
  int idx = flapIndexOf(c);
  if (idx >= 0) {
    goToFlap(idx);
    return;
  }
  Serial.print(F("  no flap for '"));
  Serial.print(c);
  Serial.println(F("': homing to flap 0, as the firmware does"));
  home();
}

// ================================================================ tests ===
// firmware detectHallPolarity(): the magnet covers a small part of a revolution,
// so the MINORITY level over one turn is the magnet level.
bool detectPolarity() {
  Serial.println(F("Detecting sensor polarity over one revolution..."));
  long low = 0, high = 0;
  bool oldReport = reportEdges;
  reportEdges = false;
  beginMove();
  for (long i = 0; i < stepsPerRev; i++) {
    if (digitalRead(HALL_PIN) == LOW) low++; else high++;
    stepForward();
  }
  endMove();
  reportEdges = oldReport;
  homed = false;                 // the old polarity may have mis-tracked the position
  currentFlap = -1;
  long minority = min(low, high);
  Serial.print(F("  LOW "));
  Serial.print(low);
  Serial.print(F(" steps, HIGH "));
  Serial.print(high);
  Serial.println(F(" steps"));
  if (minority == 0) {
    Serial.println(F("  FAILED: the pin never changed. Magnet missing/flipped to the wrong pole,"));
    Serial.println(F("  or the sensor is dead/disconnected. Polarity left unchanged."));
    return false;
  }
  if (minority > stepsPerRev / 4) {
    Serial.println(F("  FAILED: the 'magnet' region is too wide to be the magnet (noisy sensor?)."));
    Serial.println(F("  Polarity left unchanged."));
    return false;
  }
  hallActiveLevel = (low < high) ? LOW : HIGH;
  Serial.print(F("  magnet = "));
  Serial.print(hallActiveLevel == LOW ? F("LOW") : F("HIGH"));
  Serial.print(F(", "));
  Serial.print(minority);
  Serial.println(F(" steps wide"));
  return true;
}

// firmware calibrateModule(), but averaged over 3 revolutions.
void calibrate() {
  detectPolarity();
  Serial.println(F("Measuring steps per revolution over 3 revolutions..."));
  bool oldReport = reportEdges;
  reportEdges = false;
  beginMove();
  long n = 0;
  long limit = stepsPerRev * 2 + 1000;
  edgeSeen = false;
  while (!edgeSeen && n < limit) { stepForward(); n++; }     // the first trigger
  long sum = 0;
  for (int r = 0; r < 3 && edgeSeen; r++) {
    edgeSeen = false;
    n = 0;
    while (!edgeSeen && n < limit) { stepForward(); n++; }
    if (!edgeSeen) break;
    Serial.print(F("  rev "));
    Serial.print(r + 1);
    Serial.print(F(": "));
    Serial.println(lastRevSteps);
    sum += lastRevSteps;
  }
  endMove();
  reportEdges = oldReport;
  if (!edgeSeen) {
    Serial.println(F("  FAILED: lost the sensor during calibration."));
    homed = false;
    currentFlap = -1;
    return;
  }
  long measured = (sum + 1) / 3;
  if (measured <= 500 || measured >= 8000) {       // the firmware's sanity window
    Serial.print(F("  REJECTED: "));
    Serial.print(measured);
    Serial.println(F(" steps is outside 500..8000, which the firmware refuses too."));
    homed = false;
    currentFlap = -1;
    return;
  }
  stepsPerRev = measured;
  Serial.print(F("  stepsPerRev = "));
  Serial.println(stepsPerRev);
  if (stepsPerRev < 3950 || stepsPerRev > 4200) {
    Serial.println(F("  WARNING: a 28BYJ-48 is about 4076. Revolutions that vary a lot mean"));
    Serial.println(F("  missed steps (try a slower v) or a weak/noisy sensor signal."));
  }
  Serial.println(F("  Put this value in stepsPerRev at the top of the sketch to keep it."));
  homed = false;
  home();
}

void sensorMonitor() {
  releaseCoils();
  Serial.println(F("Sensor monitor: turn the drum by hand. Send any key to stop."));
  bool last = !sensorActive();
  while (!Serial.available()) {
    bool s = sensorActive();
    if (s != last) {
      Serial.println(s ? F("  MAGNET DETECTED") : F("  no magnet"));
      last = s;
    }
    digitalWrite(LED_BUILTIN, s);
  }
  while (Serial.available()) Serial.read();
  homed = false;  // the drum was moved by hand
  currentFlap = -1;
  Serial.println(F("  Done (position lost, home again with h)."));
}

bool abortRequested() {
  if (Serial.available()) {
    while (Serial.available()) Serial.read();
    Serial.println(F("  Stopped."));
    return true;
  }
  return false;
}

void cycleAll() {
  Serial.println(F("Cycling all flaps. Send any key to stop."));
  for (int i = 0; i < NUM_FLAPS; i++) {
    goToFlap(i);
    delay(700);
    if (abortRequested()) return;
  }
}

void stressTest(long n) {
  if (!homed && !home()) return;
  Serial.print(F("Stress test: "));
  Serial.print(n);
  Serial.println(F(" random flaps. Send any key to stop."));
  edgeCount = 0;
  maxDev = 0;
  for (long i = 0; i < n; i++) {
    goToFlap(random(NUM_FLAPS));
    delay(250);
    if (abortRequested()) break;
  }
  Serial.println(F("Stress test result:"));
  Serial.print(F("  sensor passes checked: "));
  Serial.println(edgeCount);
  Serial.print(F("  worst deviation:       "));
  Serial.print(maxDev);
  Serial.println(F(" steps"));
  if (edgeCount == 0) {
    Serial.println(F("  No sensor passes happened. Run more moves."));
  } else if (labs(maxDev) <= 8) {
    Serial.println(F("  PASS: no missed steps (a few steps is normal sensor jitter)."));
  } else {
    Serial.println(F("  FAIL: steps are being lost. Positive = the motor skipped steps (check the"));
    Serial.println(F("  supply, check for drum binding, try a slower v). Recalibrate with c if it"));
    Serial.println(F("  is the same every time. The firmware re-syncs at the magnet, so a small"));
    Serial.println(F("  loss shows as a wrong flap only until the next pass."));
  }
}

void showText(const String &text) {
  for (unsigned int i = 0; i < text.length(); i++) {
    goToChar(text[i]);
    delay(1000);
    if (abortRequested()) return;
  }
}

void printStatus() {
  Serial.println(F("Status:"));
  Serial.print(F("  homed:        "));  Serial.println(homed ? F("yes") : F("no"));
  Serial.print(F("  current flap: "));  Serial.println(currentFlap);
  Serial.print(F("  pos:          "));  Serial.print(pos);  Serial.println(F(" steps past flap 0"));
  Serial.print(F("  flaps:        "));  Serial.println(NUM_FLAPS);
  Serial.print(F("  stepsPerRev:  "));  Serial.println(stepsPerRev);
  Serial.print(F("  homeOffset:   "));  Serial.println(homeOffset);
  Serial.print(F("  magnet level: "));  Serial.println(hallActiveLevel == LOW ? F("LOW") : F("HIGH"));
  Serial.print(F("  step period:  "));  Serial.print(stepUs);  Serial.println(F(" us"));
  Serial.print(F("  auto release: "));  Serial.println(autoRelease ? F("on") : F("off"));
  Serial.print(F("  sensor now:   "));  Serial.println(sensorActive() ? F("MAGNET") : F("no magnet"));
}

void printHelp() {
  Serial.println(F("Commands:"));
  Serial.println(F("  ?          this help"));
  Serial.println(F("  i          status"));
  Serial.println(F("  s          sensor monitor (motor off, turn the drum by hand)"));
  Serial.println(F("  p          detect the sensor polarity (one revolution)"));
  Serial.println(F("  f <n>      step forward n half-steps (default 100)"));
  Serial.println(F("  b <n>      step backward n half-steps (bench only, loses the position)"));
  Serial.println(F("  h          home: find the magnet, then step the home offset to flap 0"));
  Serial.println(F("  c          detect polarity, measure steps per revolution, home"));
  Serial.println(F("  z          save the current position as flap 0 (sets the home offset)"));
  Serial.println(F("  o <n>      set the home offset directly, in half-steps, and home"));
  Serial.println(F("  g <n>      go to flap number n (0 to NUM_FLAPS-1)"));
  Serial.println(F("  l <c>      go to the flap for character c (l alone = blank)"));
  Serial.println(F("  t <text>   show text one character at a time (use capitals)"));
  Serial.println(F("  a          cycle through all flaps"));
  Serial.println(F("  x <n>      stress test with n random flaps (default 50)"));
  Serial.println(F("  v <us>     step period in microseconds (default 1000, the firmware's)"));
  Serial.println(F("  r          release coils now"));
  Serial.println(F("  k          toggle auto release after each move"));
}

// ============================================================ commands ===
void handleCommand(String line) {
  line.trim();
  if (line.length() == 0) return;
  char cmd = tolower(line[0]);
  String argStr = line.substring(1);
  argStr.trim();
  long arg = argStr.toInt();
  bool hasArg = argStr.length() > 0;

  switch (cmd) {
    case '?': printHelp(); break;
    case 'i': printStatus(); break;
    case 's': sensorMonitor(); break;
    case 'p': detectPolarity(); break;
    case 'f': moveSteps(hasArg ? arg : 100); Serial.print(F("  pos ")); Serial.println(pos); break;
    case 'b':
      moveSteps(-(hasArg ? labs(arg) : 100));
      Serial.println(F("  Position lost (the firmware never turns backwards); home with h."));
      break;
    case 'h': home(); break;
    case 'c': calibrate(); break;
    case 'z':
      // Like the firmware's nudge(): fold the steps taken since flap 0 into the offset.
      if (!homed) { Serial.println(F("  Home first with h.")); break; }
      homeOffset = modPos(homeOffset + pos, stepsPerRev);
      pos = 0;
      currentFlap = 0;
      Serial.print(F("  homeOffset = "));
      Serial.println(homeOffset);
      Serial.println(F("  Put this value in homeOffset at the top of the sketch to keep it,"));
      Serial.println(F("  and give the module the same value (its home offset)."));
      break;
    case 'o':
      homeOffset = modPos(arg, stepsPerRev);
      Serial.print(F("  homeOffset = "));
      Serial.println(homeOffset);
      homed = false;
      home();
      break;
    case 'g':
      if (!hasArg || arg < 0 || arg >= NUM_FLAPS) { Serial.println(F("  Flap number out of range.")); break; }
      goToFlap(arg);
      break;
    case 'l':
      // Use the raw line so "l" alone means the blank (space) flap.
      goToChar(line.length() > 2 ? line[2] : ' ');
      break;
    case 't': showText(line.length() > 2 ? line.substring(2) : String("")); break;
    case 'a': cycleAll(); break;
    case 'x': stressTest(hasArg ? arg : 50); break;
    case 'v':
      if (arg < 300 || arg > 16000) { Serial.println(F("  Use 300 to 16000 us.")); break; }
      stepUs = arg;
      Serial.print(F("  step period = "));
      Serial.print(stepUs);
      Serial.println(F(" us"));
      break;
    case 'r': releaseCoils(); Serial.println(F("  Coils off.")); break;
    case 'k':
      autoRelease = !autoRelease;
      if (autoRelease) releaseCoils(); else writeCoils(HALF_STEP[phase]);
      Serial.print(F("  auto release "));
      Serial.println(autoRelease ? F("on") : F("off"));
      break;
    default: Serial.println(F("  Unknown command, type ? for help.")); break;
  }
}

// ======================================================== setup / loop ===
void setup() {
  for (uint8_t i = 0; i < 4; i++) pinMode(COIL_PINS[i], OUTPUT);
  releaseCoils();
  pinMode(HALL_PIN, INPUT_PULLUP);
  pinMode(LED_BUILTIN, OUTPUT);

  Serial.begin(115200);
  Serial.setTimeout(100);
  randomSeed(analogRead(A0));

  lastSensor = sensorActive();
  Serial.println();
  Serial.println(F("Split-flap module test (moves like SplitFlapUniversalFirmware v36)"));
  Serial.print(F("Sensor right now: "));
  Serial.println(lastSensor ? F("MAGNET") : F("no magnet"));
  printHelp();
}

void loop() {
  digitalWrite(LED_BUILTIN, sensorActive());
  if (Serial.available()) {
    handleCommand(Serial.readStringUntil('\n'));
  }
}
