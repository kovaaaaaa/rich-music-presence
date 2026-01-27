#core/discord_rpc.py
import time
from pypresence import Presence
from pypresence.types import ActivityType
from .models import NowPlaying
from .itunes_lookup import lookup_artwork_and_urls
import urllib.parse



# APP ID
APP_CLIENT_ID = "1465803809761792193"

def apple_music_search_url(title: str, artist: str) -> str:
    q = urllib.parse.quote(f"{title} {artist}".strip())
    return f"https://music.apple.com/us/search?term={q}"

def connect_to_discord() -> Presence:
    rpc = Presence(APP_CLIENT_ID)
    rpc.connect()

    # Give Discord time to send READY payload
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
    artwork_url, track_url, album_url = lookup_artwork_and_urls(np.title, np.artist)

    payload = {
        "details": np.title[:128],
        "state": (f"{np.artist} • {np.album}" if np.album else np.artist)[:128],

        # If we have album art, use it; otherwise fallback to your app asset
        "large_image": artwork_url or "am_logo",
        "large_text": f"Apple Music • {'Playing' if np.playing else 'Paused'}"[:128],

        "small_image": "play" if np.playing else "pause",
        "small_text": (np.album)[:128],

        "activity_type": ActivityType.LISTENING,
    }

    buttons = []
    if track_url:
        buttons.append({"label": "Open Song", "url": track_url})
    if album_url:
        buttons.append({"label": "Open Album", "url": album_url})
    if not track_url:
        buttons.append({"label": "Search Apple Music", "url": apple_music_search_url(np.title, np.artist)})


    if buttons:
        payload["buttons"] = buttons[:2]

    # Progress bar only while playing
    if np.playing and np.duration > 0:
        start = int(time.time() - np.position)
        payload["start"] = start
        payload["end"] = start + int(np.duration)

    rpc.update(**payload)
