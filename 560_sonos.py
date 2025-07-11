"""
sonos_toggle_all.py
──────────────────────────────────────────────────────────
Global play/pause toggle for every Sonos device listed in ROOM_IP.

Logic
  • If ANY room/group is PLAYING → pauses ALL groups.
  • If NONE are playing         → plays ALL groups
    (only rooms that already have something queued will start).

Handles:
  • Stand-alone speakers
  • Multi-room groups (command sent once to each coordinator)

Run directly in Pythonista or via Shortcuts:
    pythonista://sonos_toggle_all.py?action=run
"""

# ── SPEAKER LIST (updated 2025-05-14) ───────────────────
ROOM_IP = {
    "Sonos-48A6B82F697A": "10.1.3.2",
    "Sonos-48A6B82FBFAAC": "10.1.3.144",
    "Sonos-48A6B82F6214": "10.1.3.136",
    "Sonos-48A6B82F9798": "10.1.3.141",
    "Sonos-48A6B82F9716": "10.1.3.199",
    "Sonos-48A6B82FAEC0": "10.1.3.168",
    "Sonos-48A6B82F6B94": "10.1.3.6",
    "Sonos-48A6B82F975C": "10.1.3.142",
    "Sonos-48A6B82F5FF2": "10.1.3.3",
    "Sonos-48A6B82F96F8": "10.1.3.139",
    "Sonos-48A6B82F94FA": "10.1.3.138",
    "Sonos-48A6B82F6BC4": "10.1.3.143",
    "Sonos-48A6B82F6B9A": "10.1.3.146",
}

# ── IMPORTS & GLOBALS ───────────────────────────────────
from soco import SoCo, config
from soco.exceptions import SoCoException
import json, datetime

config.REQUEST_TIMEOUT = 4        # keeps calls snappy on iOS

# ── BUILD UNIQUE COORDINATOR LIST ───────────────────────
coordinators = {}                 # ip → SoCo object

for ip in ROOM_IP.values():
    try:
        spk   = SoCo(ip)
        coord = spk.group.coordinator
        coordinators[coord.ip_address] = coord
    except SoCoException as e:
        print(f"# Skipping {ip}: {e}")

if not coordinators:
    raise SystemExit("No reachable Sonos speakers!")

# ── DETERMINE CURRENT GLOBAL STATE ──────────────────────
any_playing = any(
    c.get_current_transport_info()['current_transport_state'] == "PLAYING"
    for c in coordinators.values()
)

# ── ACT ON GROUP COORDINATORS ───────────────────────────
action = "pause" if any_playing else "play"

for c in coordinators.values():
    try:
        getattr(c, action)()      # c.pause() or c.play()
    except SoCoException as e:
        print(f"# {c.player_name}: {e}")

# ── RETURN SUMMARY (useful in Shortcuts) ────────────────
print(json.dumps({
    "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
    "action"   : action.upper(),
    "targets"  : [c.player_name for c in coordinators.values()],
}, indent=2))
