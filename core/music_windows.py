# core/music_windows.py
import asyncio
import time
from typing import Optional

from .models import NowPlaying
from .debug import debug_log

try:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
    )
except Exception:  # winsdk not installed or not on Windows
    MediaManager = None
    PlaybackStatus = None

_last_session_log = 0.0


def _timespan_seconds(value) -> float:
    if value is None:
        return 0.0
    try:
        return float(value.total_seconds())
    except Exception:
        pass
    try:
        # Some WinRT bindings expose a "duration" in 100ns ticks.
        return float(value.duration) / 10_000_000.0
    except Exception:
        return 0.0


def _is_apple_music_session(session) -> bool:
    try:
        app_id = session.source_app_user_model_id or ""
    except Exception:
        app_id = ""

    app_id = app_id.lower()
    if "applemusic" in app_id or "apple music" in app_id:
        return True

    try:
        name = session.get_app_user_model_id() or ""
    except Exception:
        name = ""

    return "applemusic" in name.lower() or "apple music" in name.lower()


async def _get_now_playing_async() -> Optional[NowPlaying]:
    if MediaManager is None:
        return None

    manager = await MediaManager.request_async()
    session = None
    try:
        current = manager.get_current_session()
        if current and _is_apple_music_session(current):
            session = current
    except Exception:
        session = None

    if not session:
        try:
            sessions = manager.get_sessions()
        except Exception:
            sessions = []

        fallback = None
        for candidate in sessions:
            if not _is_apple_music_session(candidate):
                continue

            try:
                playback = candidate.get_playback_info()
                status = playback.playback_status
            except Exception:
                status = None

            if status == PlaybackStatus.PLAYING:
                session = candidate
                break

            if fallback is None:
                fallback = candidate

        session = session or fallback

        if not session and sessions:
            global _last_session_log
            now = time.time()
            if now - _last_session_log > 5:
                _last_session_log = now
                names = []
                for candidate in sessions:
                    try:
                        app_id = candidate.source_app_user_model_id or ""
                    except Exception:
                        app_id = ""
                    try:
                        name = candidate.get_app_user_model_id() or ""
                    except Exception:
                        name = ""
                    try:
                        playback = candidate.get_playback_info()
                        status = playback.playback_status
                    except Exception:
                        status = None
                    names.append(f"app_id='{app_id}' name='{name}' status='{status}'")
                debug_log("No Apple Music session. Sessions: " + " | ".join(names))

    if not session:
        return None

    try:
        info = await session.try_get_media_properties_async()
    except Exception:
        return None

    try:
        playback = session.get_playback_info()
        status = playback.playback_status
    except Exception:
        status = None

    if status is None or status == PlaybackStatus.STOPPED:
        return None

    try:
        timeline = session.get_timeline_properties()
        duration = _timespan_seconds(timeline.end_time)
        position = _timespan_seconds(timeline.position)
    except Exception:
        duration = 0.0
        position = 0.0

    playing = status == PlaybackStatus.PLAYING

    return NowPlaying(
        title=getattr(info, "title", "") or "",
        artist=getattr(info, "artist", "") or "",
        album=getattr(info, "album_title", "") or "",
        duration=duration,
        position=position,
        playing=playing,
    )


def get_now_playing() -> Optional[NowPlaying]:
    if MediaManager is None:
        return None

    try:
        return asyncio.run(_get_now_playing_async())
    except RuntimeError:
        # If an event loop is already running (unlikely here), fall back.
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_get_now_playing_async())
        finally:
            loop.close()
