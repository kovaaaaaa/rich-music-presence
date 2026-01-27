#core/music_macos.py
import subprocess
from typing import Optional
from .models import NowPlaying


def get_now_playing() -> Optional[NowPlaying]:
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
        set tDur to (duration of current track)
        set tPos to (player position)
        set isPlaying to (ps is "playing")

        return "OK=1|" & tName & "|" & tArtist & "|" & tAlbum & "|" & (tDur as string) & "|" & (tPos as string) & "|" & (isPlaying as string)
    end tell
    '''

    try:
        out = subprocess.check_output(
            ["osascript", "-e", script],
            text=True
        ).strip()

        if not out.startswith("OK=1|"):
            return None

        parts = out.split("|")

        def to_float(v: str) -> float:
            try:
                return float(v)
            except Exception:
                return 0.0

        return NowPlaying(
            title=parts[1],
            artist=parts[2],
            album=parts[3],
            duration=to_float(parts[4]),
            position=to_float(parts[5]),
            playing=parts[6].lower() == "true",
        )
    except Exception:
        return None
