#core/discord_rpc.py
import time
from pypresence import Presence
from pypresence.types import ActivityType

from .models import NowPlaying

APP_CLIENT_ID = "1465803809761792193"


def connect_to_discord() -> Presence:
    rpc = Presence(APP_CLIENT_ID)
    rpc.connect()
    time.sleep(0.3)

    try:
        user = rpc.user or {}
        name = user.get("username", "Unknown")
        disc = user.get("discriminator", "")
        display = f"{name}#{disc}" if disc and disc != "0" else name
        print(f"[RPC] Connected as {display}")
    except Exception:
        print("[RPC] Connected")

    return rpc


def update_presence(rpc: Presence, np: NowPlaying):
    payload = {
        "details": np.title[:128],
        "state": (f"{np.artist} • {np.album}" if np.album else np.artist)[:128],

        "large_image": "am_logo",
        "large_text": "Apple Music",
        "small_image": "play" if np.playing else "pause",
        "small_text": "Playing" if np.playing else "Paused",

        # Spotify-ish attempt
        "activity_type": ActivityType.LISTENING,
    }

    if np.playing and np.duration > 0:
        start = int(time.time() - np.position)
        payload["start"] = start
        payload["end"] = start + int(np.duration)

    rpc.update(**payload)

