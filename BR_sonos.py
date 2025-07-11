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

# ── SPEAKER LIST ─────────────────────────────────────────
ROOM_IP = {
    "Yoga Room"              : "10.78.2.180",
    "Trampoline"             : "10.78.2.163",
    "Pool"                   : "10.78.2.108",
    "Play 5 – Pete's Office" : "10.78.2.159",
    "Pete's Office"          : "10.78.2.193",
    "Loft Room"              : "10.78.2.174",
    "Jillian's Office"       : "10.78.2.175",
    "First Floor"            : "10.78.2.191",
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
        getattr(c, action)()      # calls c.pause() or c.play()
    except SoCoException as e:
        print(f"# {c.player_name}: {e}")

# ── RETURN SUMMARY (useful in Shortcuts) ────────────────
result = {
    "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
    "action"   : action.upper(),
    "targets"  : [c.player_name for c in coordinators.values()],
}
print(json.dumps(result, indent=2))
