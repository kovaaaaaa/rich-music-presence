#main.py
import sys
import time

from core.discord_rpc import connect_to_discord, update_presence

if sys.platform == "win32":
    try:
        from core.music_windows import get_now_playing
    except Exception:
        get_now_playing = None
elif sys.platform == "darwin":
    from core.music_macos import get_now_playing
else:
    get_now_playing = None


POLL_SECONDS = 5


def signature(np):
    return (np.title, np.artist, np.album, np.playing, int(np.position))


def main():
    if not get_now_playing:
        print("[Music] Unsupported OS or missing Windows dependency (winsdk).")
        return

    rpc = connect_to_discord()

    last_sig = None
    has_presence = False

    print("[Music] Watching Apple Music… (Ctrl+C to stop)")

    while True:
        np = get_now_playing()

        if np is None:
            if has_presence:
                rpc.clear()
                has_presence = False
                last_sig = None
            time.sleep(POLL_SECONDS)
            continue

        sig = signature(np)
        if sig != last_sig:
            update_presence(rpc, np)
            has_presence = True
            print(f"[RPC] Updated: {np.title} — {np.artist}")
            last_sig = sig

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
