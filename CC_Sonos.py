"""
sonos_toggle_house.py  ·  resume-exactly fix
────────────────────────────────────────────────────────────
Pauses the current track/stream and later resumes from the exact position.
Loads “Eclectic Rock Radio” *only* when there is truly no current media.
"""

HOUSE_IP = "192.168.1.102"
GYM_IP   = "192.168.1.193"

from soco import SoCo, config
from soco.exceptions import SoCoException
import json, datetime, time, sys

try:
    from soco.music_library import MusicLibrary
except ImportError:                   # very old SoCo
    MusicLibrary = None

config.REQUEST_TIMEOUT = 4
config.EVENTS_MODULE   = None         # disable async listener thread


# ── helpers ─────────────────────────────────────────────
def connect(ip):
    try:  return SoCo(ip)
    except SoCoException: return None


def queue_empty(spk):
    try:  return spk.get_queue_size() == 0
    except AttributeError:
        try:  return spk.get_queue_length() == 0
        except Exception: return True
    except Exception: return True


def current_uri(spk):
    try:
        return spk.get_current_track_info().get("uri", "")
    except SoCoException:
        return ""


def play_station(spk, fav_name="Eclectic Rock Radio"):
    """Modern MusicLibrary → legacy → test tone fallback."""
    if MusicLibrary:
        try:
            fav = next(
                (f for f in MusicLibrary(spk).get_sonos_favorites()
                 if fav_name.lower() in f.title.lower()),
                None
            )
            if fav:
                spk.play_uri(fav.resources[0].uri)
                return
        except Exception:
            pass
    try:
        favs = spk.get_sonos_favorites()
        if isinstance(favs, dict):
            favs = favs.get("favorites", [])
        fav = next(
            (f for f in favs
             if fav_name.lower() in getattr(f, "title", "").lower()),
            None
        )
        if fav:
            spk.play_uri(getattr(fav, "uri", ""))
            return
    except Exception:
        pass
    try:
        spk.play_uri("x-rincon-mp3radio://tone@440")
    except SoCoException:
        pass


def safe_unjoin(spk):
    try: spk.unjoin()
    except SoCoException: pass


def resume_from_other(src, dest):
    try:
        info = src.get_current_track_info()
        uri  = info.get("uri")
        if not uri: return False
        pos  = info.get("position")
        dest.play_uri(uri)
        if pos and pos not in ("0:00:00", "NOT_IMPLEMENTED"):
            try: dest.seek(pos)
            except SoCoException: pass
        return True
    except SoCoException:
        return False


# ── connect ─────────────────────────────────────────────
house = connect(HOUSE_IP) or sys.exit("House unreachable.")
gym   = connect(GYM_IP)

# Kick Gym out if following House
if gym and gym.group.coordinator.ip_address == HOUSE_IP:
    safe_unjoin(gym)

# Is House following someone else?
try:
    external = house.group.coordinator.ip_address != HOUSE_IP
except SoCoException:
    external = False

if external:
    other = house.group.coordinator
    resumed = resume_from_other(other, house)
    safe_unjoin(house)
    if not resumed:
        time.sleep(0.5)
        play_station(house)
    action = "play"

else:
    state = house.get_current_transport_info()['current_transport_state']

    if state == "PLAYING":
        house.pause(); action = "pause"

    elif state == "PAUSED_PLAYBACK":
        # ▶️  Resume exactly where we paused
        if current_uri(house):
            house.play(); action = "play"
        else:                      # rare: URI vanished → start station
            play_station(house); action = "play"

    else:                          # STOPPED / NO_MEDIA
        if queue_empty(house) or not current_uri(house):
            play_station(house)
        house.play(); action = "play"

# ── summary ─────────────────────────────────────────────
print(json.dumps({
    "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
    "action"   : action.upper(),
}, indent=2))
