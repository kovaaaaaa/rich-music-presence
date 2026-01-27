# core/models.py
from dataclasses import dataclass

@dataclass(frozen=True)
class NowPlaying:
    title: str
    artist: str
    album: str
    duration: float
    position: float
    playing: bool
