# core/music_windows.py
import asyncio
from typing import Optional

from .models import NowPlaying

try:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
    )
except Exception:  # winsdk not installed or not on Windows
    MediaManager = None
    PlaybackStatus = None


def _timespan_seconds(value) -> float:
    if value is None:
        return 0.0
    try:
        return float(value.total_seconds())
    except Exception:
        pass
    try:
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
    session = manager.get_current_session()
    if not session:
        return None

    if not _is_apple_music_session(session):
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
