import json
import time
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple

from pypresence import Presence

# Client ID
APP_CLIENT_ID = "1465803809761792193"

POLL_SECONDS = 5


@dataclass(frozen=True)
class NowPlaying:
    title: str
    artist: str
    album: str
    duration: float  # seconds
    position: float  # seconds
    playing: bool


def get_now_playing_music_app() -> Optional[NowPlaying]:
    """
    Reliable AppleScript: returns pipe-delimited values.
    """
    script = r'''
    tell application "Music"
        if it is not running then
            return "OK=0"
        end if

        set ps to (player state as string)
        if ps is "stopped" then
            return "OK=0"
        end if

        set tName to (name of current track as string)
        set tArtist to (artist of current track as string)
        set tAlbum to (album of current track as string)
        set tDur to (duration of current track) -- seconds
        set tPos to (player position) -- seconds
        set isPlaying to (ps is "playing")

        return "OK=1|" & tName & "|" & tArtist & "|" & tAlbum & "|" & (tDur as string) & "|" & (tPos as string) & "|" & (isPlaying as string)
    end tell
    '''

    try:
        out = subprocess.check_output(["osascript", "-e", script], text=True).strip()
        if not out.startswith("OK=1|"):
            return None

        parts = out.split("|")
        # OK=1|title|artist|album|duration|position|playing
        title = parts[1] if len(parts) > 1 else ""
        artist = parts[2] if len(parts) > 2 else ""
        album = parts[3] if len(parts) > 3 else ""

        def to_float(x: str) -> float:
            try:
                return float(x)
            except Exception:
                return 0.0

        duration = to_float(parts[4]) if len(parts) > 4 else 0.0
        position = to_float(parts[5]) if len(parts) > 5 else 0.0
        playing = (parts[6].strip().lower() == "true") if len(parts) > 6 else False

        return NowPlaying(
            title=title,
            artist=artist,
            album=album,
            duration=duration,
            position=position,
            playing=playing,
        )
    except Exception:
        return None



def sig(np: NowPlaying) -> Tuple:
    return (np.title, np.artist, np.album, np.playing, int(np.position))


def connect_to_discord() -> Presence:
    rpc = Presence(APP_CLIENT_ID)
    rpc.connect()

    # give Discord a moment to send READY
    time.sleep(0.3)

    try:
        user = getattr(rpc, "user", None) or {}
        name = user.get("username", "Unknown")
        disc = user.get("discriminator", "")
        display = f"{name}#{disc}" if disc and disc != "0" else name

        user_id = user.get("id", "")
        avatar = user.get("avatar", "")

        avatar_url = ""
        if user_id and avatar:
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png?size=128"

        print(f"[RPC] Connected as {display}")
        if avatar_url:
            print(f"[RPC] Avatar: {avatar_url}")
    except Exception:
        print("[RPC] Connected (user info unavailable)")

    return rpc



def main():
    rpc = connect_to_discord()

    last = None
    had_presence = False

    print("[Music] Watching Music.app… (Ctrl+C to stop)")

    while True:
        np = get_now_playing_music_app()

        if np is None:
            if had_presence:
                try:
                    rpc.clear()
                    print("[RPC] Cleared (stopped / not running)")
                except Exception:
                    pass
                had_presence = False
                last = None

            time.sleep(POLL_SECONDS)
            continue

        s = sig(np)
        if s != last:
            payload = {
                "details": (np.title or "Listening")[:128],
                "state": (np.artist or "")[:128],
            }

            # Only show timestamps while playing (progress bar)
            if np.playing and np.duration > 0:
                start = int(time.time() - np.position)
                end = int(start + np.duration)
                payload["start"] = start
                payload["end"] = end

            try:
                rpc.update(**payload)
                had_presence = True
                print(f"[RPC] Updated: {np.title} — {np.artist} ({'playing' if np.playing else 'paused'})")
            except Exception as e:
                print("[RPC] Update failed:", e)

            last = s

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
