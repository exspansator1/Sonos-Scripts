"""
sonos_toggle_house_or_gym.py
────────────────────────────────────────────────────────────
• Prefers House AMX Sonos as coordinator; falls back to Gym if House is offline.
• Toggle behaviour:
      PLAYING  → PAUSE
      PAUSED   → PLAY  (resume)
      STOPPED / empty queue → start Eclectic Rock Radio (hard-coded URI).
• Handles:
      – Gym offline
      – Stale groups
      – ‘Paused but empty queue’ oddity
• Prints JSON summary.
"""

# ── HARDCODED STATION URI ───────────────────────────────
STATION_URI = (
    "x-sonosapi-hls:Api%3atune%3aliveAudio%3a9416"
    "%3a77852d23-b342-3388-b95d-23e28b3f640c?sid=37&flags=288&sn=31"
)

# ── SPEAKER IPs ─────────────────────────────────────────
ROOM_IP = {
    "Sonos-Gym"      : "192.168.1.193",
    "House AMX Sonos": "192.168.1.102",
}
GYM_IP   = ROOM_IP["Sonos-Gym"]
HOUSE_IP = ROOM_IP["House AMX Sonos"]

# ── IMPORTS ─────────────────────────────────────────────
from soco import SoCo, config
from soco.exceptions import SoCoException
import json, datetime, time

config.REQUEST_TIMEOUT = 4     # keep iOS/Pythonista snappy

# ── HELPERS ─────────────────────────────────────────────
def connect(ip):
    try:
        return SoCo(ip)
    except SoCoException:
        return None


def queue_empty(spk):
    """True only when Sonos reports 0 tracks (never raises)."""
    try:
        return spk.get_queue_size() == 0
    except AttributeError:
        try:
            return spk.get_queue_length() == 0
        except Exception:
            return False


def play_station(spk):
    """
    Clear queue → add Eclectic Rock stream → play().
    No Seek ⇒ no UPnP 402 / 711 errors on old firmware.
    """
    spk.clear_queue()
    spk.add_uri_to_queue(STATION_URI)   # always idx 0 in empty queue
    spk.play()                          # start playback


def safe_unjoin(spk):
    try:
        spk.unjoin()
    except SoCoException:
        pass


# ── STEP 1: CONNECT ─────────────────────────────────────
gym   = connect(GYM_IP)
house = connect(HOUSE_IP)

if not house and not gym:
    raise SystemExit("No reachable Sonos speakers.")


# ── STEP 2: DETERMINE COORDINATOR & GROUPING ────────────
coord = None

if house:
    coord = house                           # House preferred
    if gym:
        if gym.group.coordinator.ip_address != HOUSE_IP:
            if len(gym.group.members) > 1:
                safe_unjoin(gym)
            try:
                gym.join(house)
            except SoCoException:
                pass
else:                                       # House offline
    coord = gym
    if gym and len(gym.group.members) > 1:
        safe_unjoin(gym)

if not coord:
    raise SystemExit("Coordinator could not be determined.")


# ── STEP 3: TOGGLE LOGIC ────────────────────────────────
try:
    state = coord.get_current_transport_info()['current_transport_state']
except SoCoException:
    raise SystemExit("Unable to read transport state.")

def ensure_station_if_needed():
    if queue_empty(coord):
        play_station(coord)

try:
    if state == "PLAYING":
        coord.pause();  action = "pause"

    elif state == "PAUSED_PLAYBACK":
        ensure_station_if_needed()
        coord.play();   action = "play"

    else:                               # STOPPED / NO_MEDIA_PRESENT etc.
        ensure_station_if_needed()
        coord.play();   action = "play"

except SoCoException as e:
    raise SystemExit(f"Playback error: {e}")


# ── STEP 4: SUMMARY OUTPUT ──────────────────────────────
try:
    group_list = [m.player_name for m in coord.group.members]
except SoCoException:
    group_list = [coord.player_name]

print(json.dumps({
    "timestamp"   : datetime.datetime.now().isoformat(timespec="seconds"),
    "action"      : action.upper(),
    "coordinator" : coord.player_name,
    "group"       : group_list,
}, indent=2))
