# ui/worker.py
import time
from dataclasses import asdict

from PySide6.QtCore import QThread, Signal

from core.music_macos import get_now_playing
from core.discord_rpc import connect_to_discord, update_presence
from core.itunes_lookup import lookup_artwork_and_urls


class PresenceWorker(QThread):
    status = Signal(str)
    account = Signal(dict)       # {"name": str, "avatar_url": str}
    now_playing = Signal(dict)   # NowPlaying dict + {"artwork_url": str}

    def __init__(self, poll_seconds: int = 5, parent=None):
        super().__init__(parent)
        self.poll_seconds = poll_seconds
        self._running = True

        self._rpc = None
        self._last_sig = None
        self._has_presence = False

    def stop(self):
        self._running = False

    def _emit_account(self):
        """
        pypresence can delay user payload. Try a few times.
        """
        if not self._rpc:
            self.account.emit({"name": "Not connected", "avatar_url": ""})
            return

        for _ in range(10):
            try:
                user = getattr(self._rpc, "user", None) or {}
                username = user.get("username")
                if not username:
                    time.sleep(0.25)
                    continue

                disc = user.get("discriminator", "")
                display = f"{username}#{disc}" if disc and disc != "0" else username

                user_id = user.get("id", "")
                avatar = user.get("avatar")  # can be None
                disc = user.get("discriminator", "")
                avatar_url = ""

                # Custom avatar
                if user_id and avatar:
                    ext = "gif" if str(avatar).startswith("a_") else "png"
                    avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.{ext}?size=128"

                # Default avatar fallback
                elif user_id:
                    # discriminator can be "0" for newer usernames; fall back to 0 in that case
                    try:
                        disc_num = int(disc) if disc and disc.isdigit() else 0
                    except Exception:
                        disc_num = 0
                    default_index = disc_num % 5
                    avatar_url = f"https://cdn.discordapp.com/embed/avatars/{default_index}.png"

                self.account.emit({"name": display, "avatar_url": avatar_url})
                return
            except Exception:
                time.sleep(0.25)

        self.account.emit({"name": "Connected", "avatar_url": ""})

    def run(self):
        # 1) Connect to Discord
        try:
            self.status.emit("Connecting to Discord…")
            self._rpc = connect_to_discord()
            self.status.emit("Discord connected ✅")
            self._emit_account()
        except Exception as e:
            self.status.emit(f"Discord connect failed: {e}")
            return

        # 2) Main loop
        while self._running:
            try:
                np = get_now_playing()
            except Exception as e:
                self.status.emit(f"Apple Music read failed: {e}")
                time.sleep(self.poll_seconds)
                continue

            if np is None:
                # Clear RPC if previously set
                if self._has_presence and self._rpc:
                    try:
                        self._rpc.clear()
                    except Exception:
                        pass
                    self._has_presence = False
                    self._last_sig = None

                self.status.emit("Apple Music: nothing playing")
                # Also update UI to blanks so you see it change
                self.now_playing.emit({
                    "title": "",
                    "artist": "",
                    "album": "",
                    "duration": 0.0,
                    "position": 0.0,
                    "playing": False,
                    "artwork_url": "",
                })
                time.sleep(self.poll_seconds)
                continue

            # iTunes lookup (cached)
            artwork_url, _, _ = lookup_artwork_and_urls(np.title, np.artist)

            # Emit now playing for UI every tick
            d = asdict(np)
            d["artwork_url"] = artwork_url or ""
            self.now_playing.emit(d)

            # Only update Discord when something meaningfully changes
            sig = (np.title, np.artist, np.album, np.playing, int(np.position))
            if sig != self._last_sig:
                try:
                    update_presence(self._rpc, np)
                    self._has_presence = True
                    self.status.emit(f"{'Playing' if np.playing else 'Paused'}: {np.title} — {np.artist}")
                except Exception as e:
                    self.status.emit(f"Presence update failed: {e}")

                self._last_sig = sig

            time.sleep(self.poll_seconds)
