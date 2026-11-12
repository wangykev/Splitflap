/*
  Split-flap single module bench test  (Arduino Uno)
  ===================================================
  Checks one module (28BYJ-48 stepper, hall effect home sensor, flap drum)
  before the custom driver PCB is used.

  WIRING
  ------
  The Uno pins cannot drive the motor coils directly: they need about 200 mA,
  and a pin gives about 20 mA. Use a ULN2003 driver board (the small red/green
  board that usually ships with the 28BYJ-48).

    ULN2003 IN1  -> D8
    ULN2003 IN2  -> D9
    ULN2003 IN3  -> D10
    ULN2003 IN4  -> D11
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
    2. f 500  motor check: it should turn forward smoothly
    3. h      home (spin until the magnet is found)
    4. c      measure the real steps per revolution (expect about 4076)
    5. Step with f / b until flap 0 lines up, then z to save that as flap 0
    6. a      cycle through every flap
    7. x 50   stress test: 50 random flaps, reports missed steps
*/

#include <ctype.h>

// ----------------------------------------------------------------- pins ---
const uint8_t COIL_PINS[4] = {8, 9, 10, 11};   // ULN2003 IN1..IN4
const uint8_t HALL_PIN = 2;
const bool HALL_ACTIVE_LOW = true;              // most hall switches pull LOW at the magnet

// ------------------------------------------------------- module config ---
// Edit these to match your flap set. FLAPS must have exactly NUM_FLAPS characters,
// in the order they appear on the drum, starting at the home flap.
const uint8_t NUM_FLAPS = 40;
const char FLAPS[] = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,'";
static_assert(sizeof(FLAPS) - 1 == NUM_FLAPS, "FLAPS must contain NUM_FLAPS characters");

// 28BYJ-48: 64 half-steps per rotor turn x 63.684:1 gearbox = about 4076 half-steps.
long stepsPerRev = 4076;
long homeOffset = 0;               // half-steps from the sensor edge to flap 0 (set with z or o)

// -------------------------------------------------------------- motion ---
unsigned int minStepUs = 1200;     // fastest step period in microseconds (v command)
const unsigned int START_STEP_US = 2500;
const int RAMP_STEPS = 150;
bool autoRelease = true;           // turn coils off after each move so the motor stays cool

// Half-step sequence; bit 0 = IN1 ... bit 3 = IN4
const uint8_t HALF_STEP[8] = {0b0001, 0b0011, 0b0010, 0b0110,
                              0b0100, 0b1100, 0b1000, 0b1001};

// --------------------------------------------------------------- state ---
int8_t phase = 0;
long pos = 0;                      // half-steps since the last sensor edge
bool homed = false;
bool lastSensor = false;
bool edgeSeen = false;
long lastEdgePos = 0;
int currentFlap = -1;

bool reportEdges = true;
long edgeCount = 0;
long maxDev = 0;

// ============================================================= helpers ===
bool sensorActive() {
  bool v = digitalRead(HALL_PIN);
  return HALL_ACTIVE_LOW ? !v : v;
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

void onSensorEdge() {
  if (homed) {
    long dev = pos - stepsPerRev;
    edgeCount++;
    if (labs(dev) > labs(maxDev)) maxDev = dev;
    if (reportEdges) {
      Serial.print(F("  [sensor] one revolution = "));
      Serial.print(pos);
      Serial.print(F(" steps (deviation "));
      Serial.print(dev);
      Serial.println(F(")"));
    }
  }
  lastEdgePos = pos;
  edgeSeen = true;
  pos = 0;
  homed = true;
}

// One half-step. dir = +1 forward, -1 backward.
// Only forward motion counts sensor edges, since a split-flap only turns one way.
void stepOnce(int8_t dir) {
  phase = (phase + dir) & 7;
  writeCoils(HALF_STEP[phase]);
  pos += dir;
  bool s = sensorActive();
  if (dir > 0 && s && !lastSensor) onSensorEdge();
  lastSensor = s;
  digitalWrite(LED_BUILTIN, s);
}

// Linear speed ramp: slow at the start and end of a move, so the motor doesn't stall.
unsigned int rampDelay(long done, long remaining) {
  if (minStepUs >= START_STEP_US) return minStepUs;
  long r = min(done, remaining);
  if (r >= RAMP_STEPS) return minStepUs;
  return START_STEP_US - (long)(START_STEP_US - minStepUs) * r / RAMP_STEPS;
}

void beginMove() {
  lastSensor = sensorActive();   // the drum may have been turned by hand
  writeCoils(HALF_STEP[phase]);  // re-engage the same phase it was released on
  delay(5);
}

void endMove() {
  if (autoRelease) releaseCoils();
}

// ============================================================== motion ===
void moveSteps(long n) {
  int8_t dir = n >= 0 ? 1 : -1;
  long total = labs(n);
  beginMove();
  for (long i = 0; i < total; i++) {
    stepOnce(dir);
    delayMicroseconds(rampDelay(i, total - i - 1));
  }
  endMove();
}

bool home() {
  Serial.println(F("Homing..."));
  homed = false;
  edgeSeen = false;
  beginMove();
  long limit = stepsPerRev * 2 + 500;
  long n = 0;
  while (!homed && n < limit) {
    stepOnce(1);
    delayMicroseconds(rampDelay(n, RAMP_STEPS));
    n++;
  }
  endMove();
  if (!homed) {
    Serial.println(F("  FAILED: no sensor edge in 2 revolutions."));
    Serial.println(F("  Check: sensor wiring/power, magnet polarity (flip it), magnet-to-sensor gap,"));
    Serial.println(F("  and that the drum actually turned (motor wiring / supply)."));
    currentFlap = -1;
    return false;
  }
  Serial.print(F("  Sensor edge found after "));
  Serial.print(n);
  Serial.println(F(" steps."));
  currentFlap = -1;
  return true;
}

void goToFlap(int idx) {
  if (!homed && !home()) return;
  long target = modPos(homeOffset + (stepsPerRev * idx + NUM_FLAPS / 2) / NUM_FLAPS, stepsPerRev);
  long limit = stepsPerRev * 2;
  long done = 0;
  beginMove();
  while (done < limit) {
    long rem = modPos(target - pos, stepsPerRev);
    if (rem == 0) break;
    stepOnce(1);
    delayMicroseconds(rampDelay(done, rem - 1));
    done++;
  }
  endMove();
  if (done >= limit) {
    Serial.println(F("  ERROR: never reached the target position. Rehome with h."));
    return;
  }
  currentFlap = idx;
  Serial.print(F("  flap "));
  Serial.print(idx);
  Serial.print(F(" '"));
  Serial.print(FLAPS[idx]);
  Serial.println(F("'"));
}

int flapIndexOf(char c) {
  c = toupper(c);
  for (int i = 0; i < NUM_FLAPS; i++) {
    if (FLAPS[i] == c) return i;
  }
  return -1;
}

// ================================================================ tests ===
void calibrate() {
  if (!home()) return;
  Serial.println(F("Measuring steps per revolution over 3 revolutions..."));
  bool oldReport = reportEdges;
  reportEdges = false;
  long sum = 0;
  beginMove();
  for (int r = 0; r < 3; r++) {
    edgeSeen = false;
    long n = 0;
    long limit = stepsPerRev * 2 + 500;
    while (!edgeSeen && n < limit) {
      stepOnce(1);
      delayMicroseconds(rampDelay(n + (r > 0 ? RAMP_STEPS : 0), RAMP_STEPS));
      n++;
    }
    if (!edgeSeen) {
      endMove();
      reportEdges = oldReport;
      Serial.println(F("  FAILED: lost the sensor during calibration."));
      return;
    }
    Serial.print(F("  rev "));
    Serial.print(r + 1);
    Serial.print(F(": "));
    Serial.println(lastEdgePos);
    sum += lastEdgePos;
  }
  endMove();
  reportEdges = oldReport;
  stepsPerRev = (sum + 1) / 3;
  Serial.print(F("  stepsPerRev = "));
  Serial.println(stepsPerRev);
  if (stepsPerRev < 3950 || stepsPerRev > 4200) {
    Serial.println(F("  WARNING: expected about 4076. Revolutions that vary a lot mean"));
    Serial.println(F("  missed steps (try a slower v) or a weak/noisy sensor signal."));
  }
  Serial.println(F("  Put this value in stepsPerRev at the top of the sketch to keep it."));
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
    Serial.println(F("  No full revolutions happened. Run more moves."));
  } else if (labs(maxDev) <= 8) {
    Serial.println(F("  PASS: no missed steps (a few steps is normal sensor jitter)."));
  } else {
    Serial.println(F("  FAIL: steps are being lost. Positive = motor skipped steps (slow down with v,"));
    Serial.println(F("  check supply, check for drum binding). Recalibrate with c if it is constant."));
  }
}

void showText(const String &text) {
  for (unsigned int i = 0; i < text.length(); i++) {
    int idx = flapIndexOf(text[i]);
    if (idx < 0) {
      Serial.print(F("  no flap for '"));
      Serial.print(text[i]);
      Serial.println(F("', skipped"));
      continue;
    }
    goToFlap(idx);
    delay(1000);
    if (abortRequested()) return;
  }
}

void printStatus() {
  Serial.println(F("Status:"));
  Serial.print(F("  homed:        "));  Serial.println(homed ? F("yes") : F("no"));
  Serial.print(F("  current flap: "));  Serial.println(currentFlap);
  Serial.print(F("  pos:          "));  Serial.println(pos);
  Serial.print(F("  stepsPerRev:  "));  Serial.println(stepsPerRev);
  Serial.print(F("  homeOffset:   "));  Serial.println(homeOffset);
  Serial.print(F("  step period:  "));  Serial.print(minStepUs);  Serial.println(F(" us"));
  Serial.print(F("  auto release: "));  Serial.println(autoRelease ? F("on") : F("off"));
  Serial.print(F("  sensor now:   "));  Serial.println(sensorActive() ? F("MAGNET") : F("no magnet"));
}

void printHelp() {
  Serial.println(F("Commands:"));
  Serial.println(F("  ?          this help"));
  Serial.println(F("  i          status"));
  Serial.println(F("  s          sensor monitor (motor off, turn the drum by hand)"));
  Serial.println(F("  f <n>      step forward n half-steps (default 100)"));
  Serial.println(F("  b <n>      step backward n half-steps (default 100)"));
  Serial.println(F("  h          home on the sensor, then go to flap 0"));
  Serial.println(F("  c          calibrate steps per revolution"));
  Serial.println(F("  z          save the current position as flap 0 (sets the home offset)"));
  Serial.println(F("  o <n>      set the home offset directly, in half-steps"));
  Serial.println(F("  g <n>      go to flap number n (0 to NUM_FLAPS-1)"));
  Serial.println(F("  l <c>      go to the flap for character c (l alone = blank)"));
  Serial.println(F("  t <text>   show text one character at a time"));
  Serial.println(F("  a          cycle through all flaps"));
  Serial.println(F("  x <n>      stress test with n random flaps (default 50)"));
  Serial.println(F("  v <us>     step period in microseconds (default 1200, lower is faster)"));
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
    case 'f': moveSteps(hasArg ? arg : 100); Serial.print(F("  pos ")); Serial.println(pos); break;
    case 'b': moveSteps(-(hasArg ? arg : 100)); Serial.print(F("  pos ")); Serial.println(pos); break;
    case 'h': if (home()) goToFlap(0); break;
    case 'c': calibrate(); break;
    case 'z':
      if (!homed) { Serial.println(F("  Home first with h.")); break; }
      homeOffset = modPos(pos, stepsPerRev);
      currentFlap = 0;
      Serial.print(F("  homeOffset = "));
      Serial.println(homeOffset);
      Serial.println(F("  Put this value in homeOffset at the top of the sketch to keep it."));
      break;
    case 'o':
      homeOffset = modPos(arg, stepsPerRev);
      Serial.print(F("  homeOffset = "));
      Serial.println(homeOffset);
      goToFlap(0);
      break;
    case 'g':
      if (arg < 0 || arg >= NUM_FLAPS) { Serial.println(F("  Flap number out of range.")); break; }
      goToFlap(arg);
      break;
    case 'l': {
      // Use the raw line so "l" alone means the blank (space) flap.
      char c = line.length() > 2 ? line[2] : ' ';
      int idx = flapIndexOf(c);
      if (idx < 0) Serial.println(F("  No flap for that character."));
      else goToFlap(idx);
      break;
    }
    case 't': showText(line.length() > 2 ? line.substring(2) : String("")); break;
    case 'a': cycleAll(); break;
    case 'x': stressTest(hasArg ? arg : 50); break;
    case 'v':
      if (arg < 300 || arg > 16000) { Serial.println(F("  Use 300 to 16000 us.")); break; }
      minStepUs = arg;
      Serial.print(F("  step period = "));
      Serial.print(minStepUs);
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
  Serial.println(F("Split-flap module test"));
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
