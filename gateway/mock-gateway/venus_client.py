#!/usr/bin/env python3
"""Reference client for the Pi side -- the CONTRACT.md rules as runnable code, for testing
without Home Assistant. (In production the same logic lives in the HA package,
ha/splitflap_venus.yaml.)

  * Everything DISPLAYED goes through the Companion (the only writer to the flaps).
  * Only LED states go straight to the gateway, and only if the gateway advertises "led".
  * Every answer passes through sanitize() just before it is sent.

    python venus_client.py mode time            # run the Companion's Time app
    python venus_client.py mode weather
    python venus_client.py say "It's 72°F and sunny"
    python venus_client.py stop                 # stop the app and blank the wall
    python venus_client.py led thinking         # no-op unless the gateway has "led"
    python venus_client.py demo "Dinner is at 7"  # a fake voice turn: listen, think, speak, show
    python venus_client.py watch                # re-send the last answer whenever the Companion restarts
    python venus_client.py sanitize "It’s 72°F ☀️ café"   # just show what sanitize() does

Options: --companion http://<pi>:8000  --gateway http://<gateway-ip>  --display default
Standard library only.
"""
import argparse
import json
import os
import threading
import time
import unicodedata
import urllib.error
import urllib.request

DEFAULT_COMPANION = os.environ.get("COMPANION_URL", "http://localhost:8000")
DEFAULT_GATEWAY = os.environ.get("GATEWAY_URL", "http://localhost:8080")
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venus_last_answer.json")

# The firmware's default reel as charset.common reports it (colour codes removed, q -> ").
# Used only when the gateway cannot be reached; normally the live charset.common is used.
FALLBACK_CHARSET = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$&()-+=;\":%'.,/?*"

# Lookalike folding: characters LLMs and pasted text produce that have an obvious on-reel cousin.
LOOKALIKES = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'", "`": "'", "´": "'",
    "“": '"', "”": '"', "„": '"', "″": '"', "«": '"', "»": '"',
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "―": "-",
    "−": "-", "…": "...", "×": "*", "ß": "SS", "æ": "AE", "Æ": "AE",
    "œ": "OE", "Œ": "OE", "ø": "O", "Ø": "O", "ł": "L", "Ł": "L",
    " ": " ", "\t": " ",
}


def sanitize(text, charset=FALLBACK_CHARSET, cols=15, rows=3):
    """The guarantee behind the contract's character rule: whatever produced `text` (an LLM, a
    template, a pasted string), the result contains ONLY characters in `charset` and fits in
    rows x cols. Steps: lookalike folding -> strip accents -> uppercase -> anything still off the
    reel becomes a space -> word-wrap to `cols` -> keep `rows` lines (marked with "..." when cut).
    Returns the lines joined with "\\n", which the Companion treats as forced line breaks."""
    s = "".join(LOOKALIKES.get(ch, ch) for ch in str(text))
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch) and unicodedata.category(ch) != "Mn")
    s = s.upper()
    allowed = set(charset) | {"\n"}
    s = "".join(ch if ch in allowed else " " for ch in s)

    lines = []
    for para in s.split("\n"):
        words = para.split()
        if not words:
            if lines:                        # keep a deliberate blank line, but not leading ones
                lines.append("")
            continue
        cur = ""
        for w in words:
            while len(w) > cols:             # a word longer than the wall: hard split
                if cur:
                    lines.append(cur)
                    cur = ""
                lines.append(w[:cols])
                w = w[cols:]
            if not cur:
                cur = w
            elif len(cur) + 1 + len(w) <= cols:
                cur += " " + w
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    while lines and lines[-1] == "":
        lines.pop()

    if len(lines) > rows:                    # too long: cut deliberately, not the Companion's crop
        lines = lines[:rows]
        last = lines[-1]
        if len(last) + 3 > cols:
            cut = last[:cols - 3].rstrip()
            sp = cut.rfind(" ")
            last = cut[:sp] if sp > 0 else cut
        lines[-1] = (last.rstrip(" ,;:-.") + "...")[:cols]
    return "\n".join(lines)


class Venus:
    def __init__(self, companion, gateway, display="default", timeout=5.0):
        self.companion = companion.rstrip("/")
        self.gateway = gateway.rstrip("/")
        self.display = display
        self.timeout = timeout
        self.charset, self.cols, self.rows, self.led_enabled = FALLBACK_CHARSET, 15, 3, False
        self.refresh_capabilities()

    # --- plumbing ---------------------------------------------------------------------------------
    def _req(self, method, url, body=None, timeout=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Content-Type": "application/json"} if data else {})
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}

    def _companion(self, method, path, body=None):
        sep = "&" if "?" in path else "?"
        return self._req(method, f"{self.companion}{path}{sep}display={self.display}", body)

    def refresh_capabilities(self):
        """Read the gateway's self-description once: which characters, what grid, and whether it
        has LEDs. Like reading a chip's ID register before configuring it."""
        try:
            cap = self._req("GET", f"{self.gateway}/api/capabilities")
        except (urllib.error.URLError, OSError, ValueError) as e:
            print(f"[venus] gateway capabilities unavailable ({e}); using defaults, LEDs off")
            return
        self.charset = (cap.get("charset") or {}).get("common") or FALLBACK_CHARSET
        grid = cap.get("grid") or {}
        self.rows, self.cols = int(grid.get("rows", 3)), int(grid.get("cols", 15))
        self.led_enabled = "led" in (cap.get("features") or [])
        print(f"[venus] gateway {cap.get('product')} fw {cap.get('fw')}: {self.rows}x{self.cols}, "
              f"LEDs {'on' if self.led_enabled else 'off (no \"led\" feature)'}")

    # --- the three display functions (all through the Companion) ------------------------------------
    def start_mode(self, app):
        """Run a Companion app ("time", "weather"). It keeps itself updated."""
        r = self._companion("POST", "/api/apps/run", {"app": app})
        self._save_last(None)                 # the wall now shows an app, not an answer
        return r

    def show_answer(self, text):
        """sanitize() then send as a Companion message with NO seconds: it replaces whatever app
        is running and stays up until something else is shown."""
        clean = sanitize(text, self.charset, self.cols, self.rows)
        r = self._companion("POST", "/api/message", {"text": clean})
        self._save_last(clean)
        return clean, r

    def stop(self):
        """Stop the app and BLANK the wall. Not needed before show_answer()."""
        self._save_last(None)
        return self._companion("POST", "/api/apps/stop")

    # --- LEDs (straight to the gateway, gated on capabilities) ----------------------------------------
    def led(self, state):
        """Fire-and-forget: never blocks the voice pipeline, sends nothing if the gateway has no LEDs."""
        if not self.led_enabled:
            return

        def go():
            try:
                self._req("POST", f"{self.gateway}/api/led", {"state": state}, timeout=1.0)
            except (urllib.error.URLError, OSError) as e:
                print(f"[venus] led {state} failed: {e}")
        threading.Thread(target=go, daemon=True).start()

    # --- last answer, so it can be re-sent after a Companion restart ----------------------------------
    def _save_last(self, text):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({"answer": text}, f)
        except OSError:
            pass

    def last_answer(self):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("answer")
        except (OSError, ValueError):
            return None

    def answer_lost(self):
        """True when an answer should be on the wall but the Companion has lost it:
          * after a Companion restart it resumes apps, not messages, and believes the wall is
            blank -- however short the restart was;
          * after a send the gateway refused with 503 during maintenance, the Companion does not
            retry, and its link stays 'disconnected' until its next successful send."""
        if not self.last_answer():
            return False
        try:
            st = self._companion("GET", "/api/current_state")
        except (urllib.error.URLError, OSError, ValueError):
            return False                      # Companion down: nothing to do until it is back
        if st.get("active_app") or st.get("active_playlist"):
            return False                      # something else was deliberately put up
        believed_blank = not (st.get("string") or "").strip()
        linked = bool((st.get("transport") or {}).get("connected"))
        return believed_blank or not linked

    def gateway_accepting(self):
        """Read-only: is the gateway up and NOT holding the bus for maintenance?"""
        try:
            return not self._req("GET", f"{self.gateway}/api/status", timeout=2.0).get("maint", False)
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def watch(self, interval=5.0):
        """Keep the last answer on the wall. Two things lose a message:
          * a Companion restart (it resumes apps, not messages), and
          * a send the gateway refused with 503 during maintenance (the Companion does not retry).
        So re-send the last answer whenever answer_lost() and the gateway is accepting content.
        Apps need nothing: the Companion resumes and repaints them itself."""
        print(f"[venus] watching {self.companion}")
        while True:
            time.sleep(interval)
            if self.answer_lost() and self.gateway_accepting():
                ans = self.last_answer()
                try:
                    self._companion("POST", "/api/message", {"text": ans})
                    print(f"[venus] answer was lost -- re-sent: {ans!r}")
                except (urllib.error.URLError, OSError) as e:
                    print(f"[venus] re-send failed ({e}); will retry")

    def demo(self, answer):
        """What one voice turn looks like from the Pi: the satellite's states drive the LEDs."""
        self.led("listening")
        time.sleep(2)
        self.led("thinking")
        time.sleep(3)
        self.led("speaking")
        clean, _ = self.show_answer(answer)
        time.sleep(2)
        self.led("idle")
        return clean


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--companion", default=DEFAULT_COMPANION)
    ap.add_argument("--gateway", default=DEFAULT_GATEWAY)
    ap.add_argument("--display", default="default")
    ap.add_argument("cmd", choices=["mode", "say", "stop", "led", "demo", "watch", "sanitize"])
    ap.add_argument("arg", nargs="?", default="")
    a = ap.parse_args()

    if a.cmd == "sanitize":
        print(sanitize(a.arg))
        return
    v = Venus(a.companion, a.gateway, a.display)
    if a.cmd == "mode":
        print(v.start_mode(a.arg or "time"))
    elif a.cmd == "say":
        clean, r = v.show_answer(a.arg)
        print(f"sent:\n{clean}\n{r}")
    elif a.cmd == "stop":
        print(v.stop())
    elif a.cmd == "led":
        v.led(a.arg or "idle")
        time.sleep(1.2)                       # give the fire-and-forget thread time to finish
    elif a.cmd == "demo":
        print("shown:\n" + v.demo(a.arg or "Hello from Venus"))
        time.sleep(1.2)
    elif a.cmd == "watch":
        v.watch()


if __name__ == "__main__":
    main()
