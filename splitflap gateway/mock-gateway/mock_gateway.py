#!/usr/bin/env python3
"""Mock SplitFlapGateway -- a stand-in for the ESP32 so the Pi side can be built with no hardware.

It answers the same REST API as the real gateway firmware (v3.17.0, SplitFlapGateway/src/web.cpp),
closely enough that an UNMODIFIED SplitFlapGatewayCompanion drives it exactly as it would drive the
real wall: registration heartbeat, capabilities, config sync, the settings blob store, and pages
sent as /api/rs485/batch frames. It also implements the LED perimeter strip API defined in
CONTRACT.md, which the real firmware does not have yet.

Open http://localhost:8080/ for the viewer (flap grid + LED strip + maintenance/quiet switches).

    python mock_gateway.py                          # 3x15 wall, LEDs on, port 8080
    python mock_gateway.py --no-led                 # behave like today's real firmware (no LEDs)
    python mock_gateway.py --leds 150 --start-corner tr --direction ccw
    python mock_gateway.py --mqtt localhost:1883    # also speak MQTT (needs: pip install paho-mqtt)
    python mock_gateway.py --state-file mock.json   # keep the settings blob across restarts

Standard library only (MQTT optional). Python 3.9+.
"""
import argparse
import base64
import heapq
import json
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# --- Constants mirrored from the firmware (SplitFlapGateway/src/common.h) -------------------------
FW_VERSION = "3.17.0"
API_VERSION = "3.1.0"
PRODUCT_NAME = "Split-Flap Gateway"          # no "matrix" in it: the Companion would treat it as one
FLAPSET_DEFAULT = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$&()-+=;q:%'.,/?*roygbpw"
FLAP_COLOUR_CODES = "roygbpw"
CAP_COLOUR_NAMES = ["red", "orange", "yellow", "green", "blue", "purple", "white"]
STEP_MS_MAX = 100
DEFAULT_STEP_MS = 15
BATCH_MAX_FRAMES = 512
COMPANION_MAX_BYTES = 64 * 1024
SF_MAX_FLAPS = 64
GW_TABS = [("modules", "Modules"), ("display", "Display"), ("calibration", "Calibration"),
           ("monitor", "Monitor"), ("settings", "Settings"), ("status", "Status")]
BUS_FREE, BUS_BUSY = 0, 1

# --- LED strip (CONTRACT.md: defined by the contract, not yet in the real firmware) ---------------
LED_STATES = ("idle", "listening", "thinking", "speaking")
LED_EXPIRY_S = {"listening": 10, "thinking": 30, "speaking": 30}
LED_DEFAULT_COLOR = {"idle": "#000000", "listening": "#3B82F6", "thinking": "#A855F7",
                     "speaking": "#22C55E"}
LED_QUIET_BRIGHTNESS_CAP = 40
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def log(tag, msg):
    print(f"{time.strftime('%H:%M:%S')} [{tag}] {msg}", flush=True)


def resolve_flap_byte(ch, reel):
    """sfResolveFlapByte (modules.cpp:387): fold a-z to upper except the colour codes, '"' -> 'q'.
    Returns the reel byte, or None when the module has no such flap."""
    if "a" <= ch <= "z" and ch not in FLAP_COLOUR_CODES:
        ch = ch.upper()
    if ch == '"':
        ch = "q"
    return ch if ch in reel else None


def range_list(ids):
    """capRangeList: [0,1,2,3,7] -> "0-3,7"."""
    out, i = [], 0
    while i < len(ids):
        j = i
        while j + 1 < len(ids) and ids[j + 1] == ids[j] + 1:
            j += 1
        out.append(str(ids[i]) if i == j else f"{ids[i]}-{ids[j]}")
        i = j + 1
    return ",".join(out)


class Wall:
    """Everything the gateway knows: the modules' displayed flaps, quiet/maintenance, the
    companion registration, the settings blob and the LED strip. One lock guards it all."""

    def __init__(self, args):
        self.args = args
        self.rows, self.cols = args.rows, args.cols
        self.n = self.rows * self.cols
        self.reel = args.charset
        self.lock = threading.RLock()
        self.shown = [" "] * self.n            # reel byte each module currently shows
        self.pending = [None] * self.n         # quiet time: what each module was last asked for
        self.queue = []                        # heap of (due_monotonic, seq, id, byte)
        self.seq = 0
        self.quiet = False
        self.maint = False
        self.quiet_sched = {"enabled": False, "start": "22:00", "end": "07:00", "days": 127,
                            "offset": 0}
        self.companion = {"url": "", "status": "", "tabs": [], "seen": 0.0}
        self.settings_blob = b""
        self.warnings = []                     # off-reel characters received (newest last)
        self.rx = self.tx = 0
        self.boot = time.monotonic()
        self.led = {"state": "idle", "color": LED_DEFAULT_COLOR["idle"], "brightness": 128,
                    "expires": 0.0, "seq": 0}
        self.on_display_change = None          # MQTT hook
        self.on_led_change = None
        self._load_state()

    # --- persistence (stands in for the gateway's NVS + FATFS) ---------------------------------
    def _load_state(self):
        p = self.args.state_file
        if not p or not os.path.exists(p):
            return
        try:
            with open(p, "r", encoding="utf-8") as f:
                st = json.load(f)
            self.settings_blob = base64.b64decode(st.get("settings_blob", ""))
            self.companion["url"] = st.get("companion_url", "")
            self.quiet_sched.update(st.get("quiet_schedule", {}))
            log("state", f"loaded {p} (settings blob {len(self.settings_blob)} bytes)")
        except (OSError, ValueError) as e:
            log("state", f"could not load {p}: {e}")

    def save_state(self):
        p = self.args.state_file
        if not p:
            return
        st = {"settings_blob": base64.b64encode(self.settings_blob).decode("ascii"),
              "companion_url": self.companion["url"], "quiet_schedule": self.quiet_sched}
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(st, f)
        os.replace(tmp, p)

    # --- bus ---------------------------------------------------------------------------------
    def bus_level(self):
        return BUS_BUSY if self.maint else BUS_FREE

    def warn_off_reel(self, ch, where):
        msg = f"off-reel character {ch!r} (U+{ord(ch):04X}) via {where} -- nothing moved"
        log("WARN", msg)
        with self.lock:
            self.warnings.append({"t": time.time(), "msg": msg})
            del self.warnings[:-50]

    def schedule(self, mod_id, byte, due):
        """Queue one module move. due is a monotonic time; the flap lands flip_ms later."""
        with self.lock:
            self.seq += 1
            heapq.heappush(self.queue, (due + self.args.flip_ms / 1000.0, self.seq, mod_id, byte))

    def send_frame(self, frame, due, where):
        """Apply one wire frame the way the module bus would: m<id|*><cmd><arg>.
        Handles display motion ('-' char, '+' index, 'h' home); other commands are accepted
        and ignored, as they do not change what is shown."""
        f = frame.rstrip("\r\n")
        m = re.match(r"^m(\*|\d{1,3})(.)(.*)$", f, re.S)
        if not m:
            return False
        addr, cmd, arg = m.groups()
        ids = list(range(self.n)) if addr == "*" else [int(addr)]
        ids = [i for i in ids if 0 <= i < self.n]
        if cmd == "-":
            if not arg:
                return False
            byte = resolve_flap_byte(arg[0], self.reel)
            if byte is None:
                self.warn_off_reel(arg[0], where)
                return True
        elif cmd == "+":
            try:
                idx = int(arg)
            except ValueError:
                return False
            if not 0 <= idx < len(self.reel):
                return True
            byte = self.reel[idx]
        elif cmd == "h":
            byte = " "                          # homing lands on the blank flap
        else:
            return True                         # v, d, o, ... : not display motion
        with self.lock:
            self.tx += 1
            if self.quiet:                      # rs485Send swallows motion; remember it (sfQuietCapturePending)
                for i in ids:
                    self.pending[i] = byte
                return True
        for i in ids:
            self.schedule(i, byte, due)
        return True

    def tick(self):
        """Land every queued flap move that is due. Runs on its own thread."""
        changed = False
        now = time.monotonic()
        with self.lock:
            while self.queue and self.queue[0][0] <= now:
                _, _, i, byte = heapq.heappop(self.queue)
                if self.shown[i] != byte:
                    self.shown[i] = byte
                    changed = True
            led_expired = (self.led["state"] != "idle" and self.led["expires"]
                           and now >= self.led["expires"])
        if led_expired:
            log("led", f"{self.led['state']} expired -> idle")
            self.set_led("idle", None, None, source="expiry")
        if changed and self.on_display_change:
            self.on_display_change()

    def set_quiet(self, on):
        """sfSetQuietTime (modules.cpp:1292): rising edge snapshots and blanks the wall,
        falling edge replays what each module was last asked to show."""
        with self.lock:
            was = self.quiet
            if not was and on:
                for i in range(self.n):
                    self.pending[i] = self.shown[i]
                self.queue.clear()
                now = time.monotonic()
                for i in range(self.n):
                    self.schedule(i, " ", now)
                self.quiet = True
                log("quiet", "on -- wall blanked")
            elif was and not on:
                self.quiet = False
                now = time.monotonic()
                n = 0
                for i in range(self.n):
                    if self.pending[i] is not None:
                        self.schedule(i, self.pending[i], now + n * DEFAULT_STEP_MS / 1000.0)
                        self.pending[i] = None
                        n += 1
                log("quiet", f"off -- resynced {n} module(s)")

    def display_cells(self):
        """GET /api/display/state cells: the tracked char, '"' for the q flap."""
        with self.lock:
            return ['"' if c == "q" else c for c in self.shown]

    def display_string(self):
        return "".join(self.display_cells())

    # --- capabilities ------------------------------------------------------------------------
    def common_charset(self):
        """charset.common: the reel without colour codes, 'q' reported as '"' (capPutMap)."""
        out = []
        for c in self.reel:
            if c in FLAP_COLOUR_CODES:
                continue
            c = '"' if c == "q" else c
            if c not in out:
                out.append(c)
        return "".join(out)

    def capabilities(self):
        colors = [CAP_COLOUR_NAMES[k] for k, c in enumerate(FLAP_COLOUR_CODES) if c in self.reel]
        common = self.common_charset()
        features = ["colors", "index", "batch", "quiet", "maintenance", "ha", "ota", "flapconfig"]
        doc = {
            "product": PRODUCT_NAME, "fw": FW_VERSION, "api": API_VERSION,
            "grid": {"rows": self.rows, "cols": self.cols},
            "modules": self.n, "maxFlaps": SF_MAX_FLAPS,
            "colors": colors,
            "charset": {"uniform": True, "union": common, "common": common,
                        "assumed": [], "unknown": []},
            "sets": [{"flaps": len(self.reel), "source": "reported", "chars": self.reel,
                      "modules": range_list(list(range(self.n)))}],
            "motion": {"kind": "mechanical", "settleMs": 4000},
            "features": features,
        }
        if not self.args.no_led:
            features.append("led")
            doc["led"] = self.led_geometry()
        return doc

    # --- LED strip -----------------------------------------------------------------------------
    def led_geometry(self):
        return {"count": self.args.leds, "startCorner": self.args.start_corner,
                "direction": self.args.direction}

    def set_led(self, state, color, brightness, source="api"):
        with self.lock:
            self.led["state"] = state
            self.led["color"] = color or LED_DEFAULT_COLOR[state]
            if brightness is not None:
                self.led["brightness"] = brightness
            exp = LED_EXPIRY_S.get(state)
            self.led["expires"] = time.monotonic() + exp if exp else 0.0
            self.led["seq"] += 1
        if source != "expiry":
            log("led", f"{state} ({source})")
        if self.on_led_change:
            self.on_led_change()

    def led_doc(self):
        with self.lock:
            rem = max(0.0, self.led["expires"] - time.monotonic()) if self.led["expires"] else 0.0
            bright = self.led["brightness"]
            if self.quiet:
                bright = min(bright, LED_QUIET_BRIGHTNESS_CAP)
            doc = {"ok": True, "state": self.led["state"], "color": self.led["color"],
                   "brightness": self.led["brightness"], "effectiveBrightness": bright,
                   "expiresIn": round(rem, 1), "seq": self.led["seq"]}
        doc.update(self.led_geometry())
        return doc


# --- HTTP -----------------------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "SplitFlapGatewayMock/" + FW_VERSION
    wall: Wall = None

    # quiet the default per-request stderr logging; we log what matters ourselves
    def log_message(self, fmt, *a):
        pass

    def _send(self, code, body, ctype="application/json", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _err(self, code, msg):
        self._send(code, {"error": msg})

    def _body_bytes(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n > 0 else b""

    def _json(self, raw):
        """Parse a JSON body. The Companion sends batches as windows-1252, so honour the charset."""
        if not raw:
            self._err(400, "No body")
            return None
        ctype = (self.headers.get("Content-Type") or "").lower()
        enc = "cp1252" if ("1252" in ctype or "latin" in ctype) else "utf-8"
        try:
            return json.loads(raw.decode(enc, errors="replace"))
        except ValueError:
            self._err(400, "Bad JSON")
            return None

    def _is_operator(self):
        return self.headers.get("X-SF-Client") == "dashboard"

    def _content_gate(self):
        """contentGate (web.cpp:121): while maintenance holds the bus, display content from
        anyone but the dashboard gets 503 with sendBusyError's body."""
        w = self.wall
        if w.maint and not self._is_operator():
            self._send(503, {"error": "maintenance in progress -- display content is paused",
                             "reason": "maintenance", "level": BUS_BUSY, "remaining": 0})
            return True
        return False

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-SF-Client")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        self._route("GET")

    def do_HEAD(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")

    def do_PUT(self):
        self._route("PUT")

    def do_DELETE(self):
        self._route("DELETE")

    def _route(self, method):
        path = urlparse(self.path).path.rstrip("/") or "/"
        fn = ROUTES.get((method, path))
        if fn is None:
            # drain any body so a keep-alive connection stays in sync
            if method in ("POST", "PUT"):
                self._body_bytes()
            self._err(404, "Not found")
            return
        if path not in ("/api/mock/state", "/api/display/state", "/api/led") or method != "GET":
            log("http", f"{self.client_address[0]} {method} {path}")
        try:
            fn(self)
        except (BrokenPipeError, ConnectionResetError):
            pass

    # --- read-only ------------------------------------------------------------------------------
    def h_status(self):
        w = self.wall
        age = int(time.monotonic() - w.companion["seen"]) if w.companion["seen"] else -1
        self._send(200, {
            "uptime": int(time.monotonic() - w.boot), "rx": w.rx, "tx": w.tx, "baud": 9600,
            "wifi": True, "ip": "127.0.0.1", "apip": "0.0.0.0",
            "heap": 180000, "minheap": 150000, "psram": {"size": 8388608, "free": 8000000},
            "flash": {"sketch": 1500000, "free": 1600000}, "mqtt": bool(MQTT.client),
            "modules": w.n, "reset": "poweron",
            "stk": {"rs485": 2000, "web": 3000, "net": 2000, "ota": 1500, "rtc": 900,
                    "soak": 0, "probe": 0},
            "time": time.strftime("%Y-%m-%d %H:%M:%S"), "ntpSynced": True,
            "maint": w.maint, "quiet": w.quiet,
            "companion": {"status": w.companion["status"], "age": age},
            "restore": {"state": "idle", "done": 0, "total": 0, "startsIn": 0},
            "bus": {"rejects": 0, "dropped": 0, "dropBytes": 0, "maxLen": 0,
                    "lock": {"level": w.bus_level(), "reason": "maintenance" if w.maint else "",
                             "remaining": 0}},
            "mock": True,
        })

    def h_config(self):
        w = self.wall
        self._send(200, {
            "version": FW_VERSION, "wSSID": "mock", "mqHost": w.args.mqtt or "", "mqPort": 1883,
            "mqUser": "", "mqPfx": w.args.mqtt_prefix, "baud": 9600, "dataBits": 8, "parity": 0,
            "stopBits": 1, "posixTZ": "UTC0", "ntpServer": "pool.ntp.org",
            "gridRows": w.rows, "gridCols": w.cols, "serialDebug": False, "haEnabled": False,
            "otaPasswordSet": False, "restoreOnBoot": False, "restoreDelay": 20,
            "stepMs": DEFAULT_STEP_MS,
        })

    def h_capabilities(self):
        self._send(200, self.wall.capabilities())

    def h_display_state(self):
        w = self.wall
        self._send(200, {"rows": w.rows, "cols": w.cols, "cells": w.display_cells()})

    def h_bus(self):
        w = self.wall
        holds = [{"reason": "maintenance", "level": BUS_BUSY, "remaining": 0}] if w.maint else []
        self._send(200, {"level": w.bus_level(), "holds": holds})

    # --- display content (gated) ------------------------------------------------------------------
    def h_batch(self):
        """POST /api/rs485/batch (web.cpp:286): the Companion's page path."""
        raw = self._body_bytes()
        if self._content_gate():
            return
        doc = self._json(raw)
        if doc is None:
            return
        frames = doc.get("frames") if isinstance(doc, dict) else None
        if not isinstance(frames, list):
            self._err(400, "'frames' array required")
            return
        step = doc.get("step_ms", 0)
        step = max(0, min(STEP_MS_MAX, step if isinstance(step, int) else 0))
        due, sent = time.monotonic(), 0
        for f in frames:
            if sent >= BATCH_MAX_FRAMES:
                break
            if not isinstance(f, str) or not f:
                continue
            self.wall.send_frame(f, due, "rs485/batch")
            due += step / 1000.0
            sent += 1
        self._send(200, {"ok": True, "sent": sent})

    def h_send(self):
        raw = self._body_bytes()
        if self._content_gate():
            return
        doc = self._json(raw)
        if doc is None:
            return
        d = doc.get("data", "") if isinstance(doc, dict) else ""
        if not isinstance(d, str) or not d:
            self._err(400, "'data' required")
            return
        self.wall.send_frame(d, time.monotonic(), "rs485/send")
        self._send(200, {"ok": True, "bytes": len(d), "raw": bool(doc.get("raw", False))})

    def h_cells(self):
        """POST /api/display/cells (web.cpp:1228). Reference only -- the Companion does not use it
        on a split-flap wall, and the Pi must not call it (CONTRACT.md)."""
        raw = self._body_bytes()
        if self._content_gate():
            return
        doc = self._json(raw)
        if doc is None:
            return
        cells = doc.get("cells") if isinstance(doc, dict) else None
        if not isinstance(cells, list):
            self._err(400, "'cells' array required")
            return
        start = doc.get("start", 0)
        if not isinstance(start, int) or not 0 <= start <= 254:
            self._err(400, "'start' must be 0..254")
            return
        step = doc.get("step_ms", 0)
        step = max(0, min(STEP_MS_MAX, step if isinstance(step, int) else 0))
        n = sent = skipped = 0
        due = time.monotonic()
        for c in cells:
            mod = start + n
            if mod > 254:
                break
            n += 1
            c = c if isinstance(c, dict) else {}
            if c.get("skip") is True:
                skipped += 1
                continue
            if c.get("blank") is True:
                frame = f"m{mod}h"
            elif isinstance(c.get("color"), str):
                name = c["color"].lower()
                if name not in CAP_COLOUR_NAMES:
                    skipped += 1
                    continue
                frame = f"m{mod}-{FLAP_COLOUR_CODES[CAP_COLOUR_NAMES.index(name)]}"
            elif isinstance(c.get("ch"), str) and c["ch"]:
                b = resolve_flap_byte(c["ch"][0], self.wall.reel)
                if b is None:
                    self.wall.warn_off_reel(c["ch"][0], "display/cells")
                    skipped += 1
                    continue
                frame = f"m{mod}-{b}"
            else:
                skipped += 1
                continue
            self.wall.send_frame(frame, due, "display/cells")
            due += step / 1000.0
            sent += 1
        self._send(200, {"ok": True, "cells": n, "sent": sent, "skipped": skipped})

    def _text_frames(self, start, text, where):
        due = time.monotonic()
        for i, ch in enumerate(text):
            b = resolve_flap_byte(ch, self.wall.reel)
            if b is None:
                self.wall.warn_off_reel(ch, where)
                continue
            self.wall.send_frame(f"m{start + i}-{b}", due, where)
            due += 0.010                      # sfSendText: 10 ms between characters

    def h_text(self):
        raw = self._body_bytes()
        if self._content_gate():
            return
        doc = self._json(raw)
        if doc is None:
            return
        text = doc.get("text", "")
        if not isinstance(text, str) or not text:
            self._err(400, "Empty text")
            return
        self._text_frames(int(doc.get("start", 0) or 0), text, "flap/text")
        self._send(200, {"ok": True, "chars": len(text)})

    def h_char(self):
        raw = self._body_bytes()
        if self._content_gate():
            return
        doc = self._json(raw)
        if doc is None:
            return
        mod, ch = doc.get("id"), doc.get("char")
        if not isinstance(mod, int) or not isinstance(ch, str) or not ch:
            self._err(400, "Missing id or char")
            return
        b = resolve_flap_byte(ch[0], self.wall.reel)
        if b is None:
            self.wall.warn_off_reel(ch[0], "flap/char")
            self._err(400, "Character not representable")
            return
        self.wall.send_frame(f"m{'*' if mod < 0 else mod}-{b}", time.monotonic(), "flap/char")
        self._send(200, {"ok": True})

    def h_index(self):
        raw = self._body_bytes()
        if self._content_gate():
            return
        doc = self._json(raw)
        if doc is None:
            return
        mod, idx = doc.get("id", -1), doc.get("index", -1)
        if not isinstance(idx, int) or not 0 <= idx < 64:
            self._err(400, "Invalid index (0-63)")
            return
        self.wall.send_frame(f"m{'*' if mod < 0 else mod}+{idx}", time.monotonic(), "flap/index")
        self._send(200, {"ok": True})

    def h_home(self):
        """POST /api/flap/home: MAINTGATED, so homing still works during maintenance."""
        doc = self._json(self._body_bytes())
        if doc is None:
            return
        mod = doc.get("id", -1)
        self.wall.send_frame(f"m{'*' if not isinstance(mod, int) or mod < 0 else mod}h",
                             time.monotonic(), "flap/home")
        self._send(200, {"ok": True})

    # --- quiet / maintenance ------------------------------------------------------------------------
    def h_maintenance(self):
        w = self.wall
        if self.command == "POST":
            doc = self._json(self._body_bytes())
            if doc is None:
                return
            if not isinstance(doc.get("on"), bool):
                self._err(400, "'on' (bool) required")
                return
            w.maint = doc["on"]
            log("maint", "ENABLED" if w.maint else "disabled")
            MQTT.publish_state()
        self._send(200, {"ok": True, "on": w.maint})

    def h_quiet(self):
        w = self.wall
        if self.command == "POST":
            raw = self._body_bytes()
            if self._content_gate():
                return
            doc = self._json(raw)
            if doc is None:
                return
            if not isinstance(doc.get("on"), bool):
                self._err(400, "'on' (bool) required")
                return
            w.set_quiet(doc["on"])
            MQTT.publish_state()
        self._send(200, {"ok": True, "on": w.quiet})

    def h_quiet_schedule(self):
        w = self.wall
        if self.command == "POST":
            doc = self._json(self._body_bytes())
            if doc is None:
                return
            for k, typ in (("enabled", bool), ("start", str), ("end", str), ("days", int),
                           ("offset", int)):
                if isinstance(doc.get(k), typ):
                    w.quiet_sched[k] = doc[k]
            w.save_state()
        self._send(200, w.quiet_sched)

    # --- companion ------------------------------------------------------------------------------------
    def h_companion(self):
        """GET/POST /api/companion (web.cpp:2558)."""
        c = self.wall.companion
        if self.command == "POST":
            doc = self._json(self._body_bytes())
            if doc is None:
                return
            if isinstance(doc.get("url"), str):
                if doc["url"] != c["url"]:
                    c["url"] = doc["url"]
                    log("companion", f"registered: {c['url'] or '(deregistered)'}")
                    self.wall.save_state()
                if not doc["url"]:
                    c.update(status="", tabs=[], seen=0.0)
                else:
                    c["seen"] = time.monotonic()
            if isinstance(doc.get("tabs"), list):
                c["tabs"] = [t for t in doc["tabs"] if isinstance(t, dict)][:12]
            if isinstance(doc.get("status"), str):
                c["status"] = "".join(" " if ord(ch) < 0x20 else ("'" if ch in '"\\' else ch)
                                      for ch in doc["status"])[:79]
                c["seen"] = time.monotonic()
        self._send(200, {"url": c["url"], "status": c["status"], "tabs": c["tabs"],
                         "gwTabs": [{"id": i, "label": l} for i, l in GW_TABS]})

    def h_companion_settings(self):
        """GET/PUT /api/companion/settings (web.cpp:2653-2740): an opaque gzip blob."""
        w = self.wall
        if self.command == "PUT":
            raw = self._body_bytes()
            if not raw:
                self._err(400, "Empty or truncated body")
                return
            if len(raw) > COMPANION_MAX_BYTES:
                self._err(413, "Settings blob too large")
                return
            w.settings_blob = raw
            w.save_state()
            log("companion", f"settings blob stored ({len(raw)} bytes)")
            self._send(200, {"ok": True, "bytes": len(raw)})
            return
        if not w.settings_blob:
            self._err(404, "No settings stored")
            return
        self._send(200, w.settings_blob, ctype="application/gzip",
                   extra={"Cache-Control": "no-store"})

    # --- LED strip (CONTRACT.md) -----------------------------------------------------------------
    def h_led(self):
        w = self.wall
        if w.args.no_led:
            if self.command == "POST":
                self._body_bytes()
            self._err(404, "Not found")
            return
        if self.command == "POST":
            doc = self._json(self._body_bytes())
            if doc is None:
                return
            state = doc.get("state")
            if state not in LED_STATES:
                self._err(400, "'state' must be one of: " + ", ".join(LED_STATES))
                return
            color = doc.get("color")
            if color is not None and (not isinstance(color, str) or not HEX_COLOR.match(color)):
                self._err(400, "'color' must be #RRGGBB")
                return
            bright = doc.get("brightness")
            if bright is not None and (not isinstance(bright, int) or not 0 <= bright <= 255):
                self._err(400, "'brightness' must be 0..255")
                return
            w.set_led(state, color, bright, source=self.client_address[0])
        self._send(200, w.led_doc())

    # --- viewer -------------------------------------------------------------------------------------
    def h_root(self):
        self._send(200, VIEWER_HTML, ctype="text/html; charset=utf-8")

    def h_mock_state(self):
        w = self.wall
        with w.lock:
            warns = list(w.warnings[-10:])
        self._send(200, {
            "rows": w.rows, "cols": w.cols, "cells": w.display_cells(), "quiet": w.quiet,
            "maint": w.maint, "companion": {k: v for k, v in w.companion.items() if k != "seen"},
            "companionAge": int(time.monotonic() - w.companion["seen"]) if w.companion["seen"] else -1,
            "led": None if w.args.no_led else w.led_doc(), "warnings": warns,
            "settingsBytes": len(w.settings_blob),
        })

    def h_mock_clear_warnings(self):
        self._body_bytes()
        with self.wall.lock:
            self.wall.warnings.clear()
        self._send(200, {"ok": True})


ROUTES = {
    ("GET", "/"): Handler.h_root,
    ("GET", "/api/status"): Handler.h_status,
    ("GET", "/api/config"): Handler.h_config,
    ("GET", "/api/capabilities"): Handler.h_capabilities,
    ("GET", "/api/display/state"): Handler.h_display_state,
    ("GET", "/api/bus"): Handler.h_bus,
    ("POST", "/api/rs485/batch"): Handler.h_batch,
    ("POST", "/api/rs485/send"): Handler.h_send,
    ("POST", "/api/display/cells"): Handler.h_cells,
    ("POST", "/api/flap/text"): Handler.h_text,
    ("POST", "/api/flap/char"): Handler.h_char,
    ("POST", "/api/flap/index"): Handler.h_index,
    ("POST", "/api/flap/home"): Handler.h_home,
    ("GET", "/api/maintenance"): Handler.h_maintenance,
    ("POST", "/api/maintenance"): Handler.h_maintenance,
    ("GET", "/api/quiet"): Handler.h_quiet,
    ("POST", "/api/quiet"): Handler.h_quiet,
    ("GET", "/api/quiet/schedule"): Handler.h_quiet_schedule,
    ("POST", "/api/quiet/schedule"): Handler.h_quiet_schedule,
    ("GET", "/api/companion"): Handler.h_companion,
    ("POST", "/api/companion"): Handler.h_companion,
    ("GET", "/api/companion/settings"): Handler.h_companion_settings,
    ("PUT", "/api/companion/settings"): Handler.h_companion_settings,
    ("GET", "/api/led"): Handler.h_led,
    ("POST", "/api/led"): Handler.h_led,
    ("GET", "/api/mock/state"): Handler.h_mock_state,
    ("POST", "/api/mock/clear-warnings"): Handler.h_mock_clear_warnings,
}


# --- MQTT (optional; src/mqtt.cpp) -----------------------------------------------------------------
class _Mqtt:
    client = None

    def start(self, wall, hostport, prefix):
        try:
            import paho.mqtt.client as paho
        except ImportError:
            log("mqtt", "paho-mqtt is not installed (pip install paho-mqtt) -- MQTT disabled")
            return
        self.wall, self.pfx = wall, prefix
        host, _, port = hostport.partition(":")
        try:
            c = paho.Client(paho.CallbackAPIVersion.VERSION2, client_id="splitflap-mock")
        except AttributeError:                      # paho-mqtt 1.x
            c = paho.Client(client_id="splitflap-mock")
        c.will_set(f"{prefix}/availability", "offline", retain=True)
        c.on_connect = self._on_connect
        c.on_message = self._on_message
        c.connect_async(host, int(port or 1883))
        c.loop_start()
        self.client = c
        wall.on_display_change = self.publish_display
        wall.on_led_change = self.publish_led

    def _on_connect(self, c, *a):
        for t in ("send", "flap/set", "flap/home", "display/set", "maintenance/set", "quiet/set",
                  "led/set"):
            c.subscribe(f"{self.pfx}/{t}")
        c.publish(f"{self.pfx}/availability", "online", retain=True)
        log("mqtt", "connected")
        self.publish_state()
        self.publish_display()
        self.publish_led()

    def _on_message(self, c, userdata, msg):
        w = self.wall
        topic = msg.topic[len(self.pfx) + 1:]
        text = msg.payload.decode("utf-8", errors="replace")
        log("mqtt", f"<- {msg.topic}: {text[:60]}")
        if topic == "maintenance/set":
            w.maint = text.strip().upper() == "ON"
            self.publish_state()
            return
        if topic == "led/set":
            if w.args.no_led:
                return
            state, color, bright = text.strip(), None, None
            if state.startswith("{"):
                try:
                    d = json.loads(state)
                    state, color, bright = d.get("state"), d.get("color"), d.get("brightness")
                except ValueError:
                    return
            if state in LED_STATES:
                w.set_led(state, color if isinstance(color, str) and HEX_COLOR.match(color or "")
                          else None, bright if isinstance(bright, int) else None, source="mqtt")
            return
        if w.maint:                                 # mqttCallback drops content while the bus is held
            log("mqtt", f"ignored (bus held by 'maintenance'): {msg.topic}")
            return
        now = time.monotonic()
        if topic == "quiet/set":
            w.set_quiet(text.strip().upper() == "ON")
            self.publish_state()
        elif topic == "display/set":
            due = now
            for i, ch in enumerate(text.rstrip("\r\n")):
                b = resolve_flap_byte(ch, w.reel)
                if b is None:
                    w.warn_off_reel(ch, "mqtt display/set")
                    continue
                w.send_frame(f"m{i}-{b}", due, "mqtt display/set")
                due += 0.010
        elif topic == "send":
            d = text
            if text.startswith("{"):
                try:
                    d = json.loads(text).get("data", "")
                except ValueError:
                    return
            w.send_frame(d, now, "mqtt send")
        elif topic in ("flap/set", "flap/home"):
            try:
                d = json.loads(text)
            except ValueError:
                return
            mod = d.get("id", -1 if topic == "flap/home" else -99)
            if topic == "flap/home":
                w.send_frame(f"m{'*' if mod < 0 else mod}h", now, "mqtt flap/home")
            elif d.get("text"):
                start, due = d.get("start", mod), now
                for i, ch in enumerate(d["text"]):
                    b = resolve_flap_byte(ch, w.reel)
                    if b is None:
                        w.warn_off_reel(ch, "mqtt flap/set")
                        continue
                    w.send_frame(f"m{start + i}-{b}", due, "mqtt flap/set")
                    due += 0.010
            elif d.get("char"):
                b = resolve_flap_byte(d["char"][0], w.reel)
                if b is None:
                    w.warn_off_reel(d["char"][0], "mqtt flap/set")
                else:
                    w.send_frame(f"m{'*' if mod < 0 else mod}-{b}", now, "mqtt flap/set")
            elif isinstance(d.get("index"), int):
                w.send_frame(f"m{'*' if mod < 0 else mod}+{d['index']}", now, "mqtt flap/set")

    def publish_state(self):
        if not self.client:
            return
        self.client.publish(f"{self.pfx}/maintenance/state", "ON" if self.wall.maint else "OFF")
        self.client.publish(f"{self.pfx}/quiet/state", "ON" if self.wall.quiet else "OFF")

    def publish_display(self):
        if self.client:
            self.client.publish(f"{self.pfx}/display/state", self.wall.display_string())

    def publish_led(self):
        if self.client and not self.wall.args.no_led:
            d = self.wall.led_doc()
            self.client.publish(f"{self.pfx}/led/state", json.dumps(
                {"state": d["state"], "color": d["color"], "brightness": d["brightness"]}))


MQTT = _Mqtt()


VIEWER_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mock Split-Flap Gateway</title>
<style>
:root{--bg:#14161a;--panel:#1d2026;--ink:#e9e6df;--mute:#8b909a;--flap:#262a31;--flapb:#1a1d22;--seam:#0b0c0e;--warn:#f5b942;--bad:#ef4444;--ok:#22c55e}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.4 system-ui,sans-serif;padding:16px}
h1{font-size:16px;margin:0 0 4px}.sub{color:var(--mute);margin:0 0 16px;font-size:12px}
#stage{position:relative;display:inline-block;padding:22px;border-radius:10px;background:#0d0e11;max-width:100%}
#ring{position:absolute;inset:0;pointer-events:none}
#grid{display:grid;gap:4px;position:relative}
.cell{width:clamp(18px,5.2vw,44px);aspect-ratio:3/4;background:linear-gradient(var(--flap) 50%,var(--flapb) 50%);border-radius:4px;display:flex;align-items:center;justify-content:center;font:700 clamp(12px,3.4vw,28px)/1 "Arial Narrow",Arial,sans-serif;position:relative;transition:background .15s}
.cell::after{content:"";position:absolute;left:0;right:0;top:calc(50% - 1px);height:2px;background:var(--seam)}
.sw{width:70%;height:70%;border-radius:3px}
.bar{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}
button{background:var(--panel);color:var(--ink);border:1px solid #333944;border-radius:6px;padding:7px 12px;cursor:pointer;font:inherit}
button.on{border-color:var(--warn);color:var(--warn)}
.kv{display:grid;grid-template-columns:max-content 1fr;gap:4px 12px;font-size:13px;max-width:720px}
.kv b{color:var(--mute);font-weight:500}
#warn{margin-top:12px;font-size:12px;color:var(--warn);white-space:pre-wrap;max-width:720px}
.ok{color:var(--ok)}.bad{color:var(--bad)}
</style></head><body>
<h1>Mock Split-Flap Gateway</h1>
<p class="sub">Stand-in for the ESP32 gateway (firmware v3.17.0 API) + the contract-defined LED strip. Not real hardware.</p>
<div id="stage"><canvas id="ring"></canvas><div id="grid"></div></div>
<div class="bar">
  <button id="bMaint">Maintenance</button><button id="bQuiet">Quiet time</button>
  <button id="bHome">Home all</button><button id="bClr">Clear warnings</button>
</div>
<div class="kv">
  <b>Companion</b><span id="comp">-</span>
  <b>Settings blob</b><span id="blob">-</span>
  <b>LED</b><span id="ledtxt">-</span>
</div>
<div id="warn"></div>
<script>
const COLORS={r:"#e23b3b",o:"#f08a24",y:"#f2cf2e",g:"#32b04a",b:"#2f6fe0",p:"#8b4fd1",w:"#f3f3f3"};
const H={"Content-Type":"application/json","X-SF-Client":"dashboard"};
let S=null,cellsEl=[],ledPhase=0,lastT=performance.now();
function post(u,b){return fetch(u,{method:"POST",headers:H,body:JSON.stringify(b||{})});}
function build(s){const g=document.getElementById("grid");g.style.gridTemplateColumns=`repeat(${s.cols},auto)`;g.innerHTML="";cellsEl=[];
 for(let i=0;i<s.rows*s.cols;i++){const d=document.createElement("div");d.className="cell";g.appendChild(d);cellsEl.push(d);}}
function paint(s){if(!cellsEl.length||cellsEl.length!==s.rows*s.cols)build(s);
 s.cells.forEach((c,i)=>{const el=cellsEl[i];const k=c in COLORS?"c"+c:c;if(el.dataset.v===k)return;el.dataset.v=k;
  if(c in COLORS){el.innerHTML=`<span class="sw" style="background:${COLORS[c]}"></span>`;}else{el.textContent=c===" "?"":c;}});
 bMaint.classList.toggle("on",s.maint);bQuiet.classList.toggle("on",s.quiet);
 const c=s.companion;comp.innerHTML=c.url?`<span class="ok">${c.url}</span> - ${c.status||"(no status)"} - seen ${s.companionAge}s ago`:'<span class="bad">not registered</span>';
 blob.textContent=s.settingsBytes?`${s.settingsBytes} bytes stored`:"none";
 ledtxt.textContent=s.led?`${s.led.state} ${s.led.color} brightness ${s.led.effectiveBrightness}${s.led.expiresIn?` (expires in ${s.led.expiresIn}s)`:""} - ${s.led.count} LEDs from ${s.led.startCorner} ${s.led.direction}`:"disabled (--no-led)";
 warn.textContent=s.warnings.length?"Off-reel characters received (the contract says these must never be sent):\n"+s.warnings.map(w=>"- "+w.msg).join("\n"):"";}
async function poll(){try{const r=await fetch("/api/mock/state");S=await r.json();paint(S);}catch(e){}setTimeout(poll,250);}
// LED positions: N points evenly around the stage perimeter, starting at a corner, cw or ccw.
function ledPoints(n,w,h,corner,dir){const m=8,W=w-2*m,Hh=h-2*m,P=2*(W+Hh);const pts=[];
 const start={tl:0,tr:W,br:W+Hh,bl:2*W+Hh}[corner]||0;
 for(let i=0;i<n;i++){let d=(dir==="ccw"?start-i*P/n:start+i*P/n);d=((d%P)+P)%P;let x,y;
  if(d<W){x=d;y=0}else if(d<W+Hh){x=W;y=d-W}else if(d<2*W+Hh){x=W-(d-W-Hh);y=Hh}else{x=0;y=Hh-(d-2*W-Hh)}
  pts.push([x+m,y+m]);}return pts;}
function hex(c){return[parseInt(c.slice(1,3),16),parseInt(c.slice(3,5),16),parseInt(c.slice(5,7),16)];}
function frame(t){const cv=document.getElementById("ring"),st=document.getElementById("stage");
 const w=st.clientWidth,h=st.clientHeight,dpr=devicePixelRatio||1;if(cv.width!==w*dpr||cv.height!==h*dpr){cv.width=w*dpr;cv.height=h*dpr;cv.style.width=w+"px";cv.style.height=h+"px";}
 const x=cv.getContext("2d");x.setTransform(dpr,0,0,dpr,0,0);x.clearRect(0,0,w,h);
 const dt=(t-lastT)/1000;lastT=t;const L=S&&S.led;if(!L){requestAnimationFrame(frame);return;}
 const pts=ledPoints(L.count,w,h,L.startCorner,L.direction),[R,G,B]=hex(L.color),bri=L.effectiveBrightness/255;
 ledPhase+=dt;const r=Math.max(1.2,Math.min(3,(2*(w+h))/L.count/2.4));
 for(let i=0;i<pts.length;i++){let a=0;
  if(L.state==="listening")a=0.85;
  else if(L.state==="thinking"){const head=(ledPhase*0.9*pts.length)%pts.length;let d=(head-i+pts.length)%pts.length;const tail=Math.max(6,pts.length*0.18);a=d<tail?Math.pow(1-d/tail,2):0;}
  else if(L.state==="speaking")a=0.35+0.55*(0.5+0.5*Math.sin(ledPhase*6));
  const k=a*bri;x.fillStyle=k>0.01?`rgba(${R},${G},${B},${Math.min(1,k*1.6)})`:"#22252b";x.beginPath();x.arc(pts[i][0],pts[i][1],r,0,7);x.fill();}
 requestAnimationFrame(frame);}
bMaint.onclick=()=>post("/api/maintenance",{on:!S.maint});
bQuiet.onclick=()=>post("/api/quiet",{on:!S.quiet});
bHome.onclick=()=>post("/api/flap/home",{id:-1});
bClr.onclick=()=>post("/api/mock/clear-warnings");
poll();requestAnimationFrame(frame);
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description="Mock SplitFlapGateway (firmware v3.17.0 API + LED strip)")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--rows", type=int, default=3)
    ap.add_argument("--cols", type=int, default=15)
    ap.add_argument("--charset", default=FLAPSET_DEFAULT,
                    help="the modules' reel in flap order (default: the firmware's built-in reel)")
    ap.add_argument("--flip-ms", type=int, default=150,
                    help="simulated time for a flap to land after its frame is sent")
    ap.add_argument("--leds", type=int, default=300,
                    help="LEDs in the perimeter strip (placeholder until the real strip is cut)")
    ap.add_argument("--start-corner", choices=["tl", "tr", "bl", "br"], default="bl",
                    help="corner where LED 0 (the data input) sits")
    ap.add_argument("--direction", choices=["cw", "ccw"], default="cw")
    ap.add_argument("--no-led", action="store_true",
                    help="no LED support, like today's real firmware: no 'led' feature, /api/led 404s")
    ap.add_argument("--mqtt", default="", help="broker host[:port] (needs paho-mqtt)")
    ap.add_argument("--mqtt-prefix", default="splitflap")
    ap.add_argument("--state-file", default="",
                    help="JSON file that keeps the settings blob and companion URL across restarts")
    args = ap.parse_args()
    if args.rows < 1 or args.cols < 1 or args.rows * args.cols > 255:
        sys.exit("rows x cols must be 1..255 modules")
    if args.leds < 1:
        sys.exit("--leds must be >= 1")
    if len(args.charset) > SF_MAX_FLAPS:
        sys.exit(f"--charset can hold at most {SF_MAX_FLAPS} flaps")

    wall = Wall(args)
    Handler.wall = wall

    def ticker():
        while True:
            wall.tick()
            time.sleep(0.02)
    threading.Thread(target=ticker, daemon=True).start()

    if args.mqtt:
        MQTT.start(wall, args.mqtt, args.mqtt_prefix)

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.daemon_threads = True
    led = "off (--no-led)" if args.no_led else f"{args.leds} LEDs from {args.start_corner} {args.direction}"
    log("boot", f"mock gateway v{FW_VERSION}: {args.rows}x{args.cols} wall, LED strip {led}")
    log("boot", f"viewer  http://localhost:{args.port}/   (point the Companion's GATEWAY_URL here)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
