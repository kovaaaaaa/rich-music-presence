import re
import requests
import urllib.parse
from functools import lru_cache
from typing import Optional, Tuple

_HTTP = requests.Session()


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    # remove some punctuation-ish stuff that causes mismatches
    s = re.sub(r"[’'\"“”()\[\]{}.,:;!?]", "", s)
    return s

def _score_result(item: dict, title: str, artist: str, album: Optional[str]) -> int:
    want_title = _norm(title)
    want_artist = _norm(artist)
    want_album = _norm(album) if album else ""

    got_title = _norm(item.get("trackName", ""))
    got_artist = _norm(item.get("artistName", ""))
    got_album = _norm(item.get("collectionName", ""))

    score = 0

    # Title matching
    if got_title == want_title:
        score += 120
    elif want_title and got_title.startswith(want_title):
        score += 90
    elif want_title and want_title in got_title:
        score += 60

    # Artist matching
    if want_artist:
        if got_artist == want_artist:
            score += 120
        elif want_artist in got_artist or got_artist in want_artist:
            score += 70

    # Album matching (if provided)
    if want_album:
        if got_album == want_album:
            score += 140
        elif want_album in got_album or got_album in want_album:
            score += 80

    # Prefer “track” over other weirdness if present
    if item.get("kind") == "song":
        score += 10

    return score

def _upgrade_artwork(url: Optional[str], size: int = 512) -> Optional[str]:
    if not url:
        return None
    # common iTunes pattern: .../100x100bb.jpg or 600x600bb.jpg
    url = re.sub(r"/\d+x\d+bb\.(jpg|png)$", f"/{size}x{size}bb.\\1", url)
    url = re.sub(r"/\d+x\d+bb\.(jpg|png)\?", f"/{size}x{size}bb.\\1?", url)
    url = url.replace("100x100", f"{size}x{size}")
    url = url.replace("600x600", f"{size}x{size}")
    return url

# returns (artwork_url, track_url, album_url)
@lru_cache(maxsize=512)
def lookup_artwork_and_urls(
    title: str, artist: str, album: Optional[str] = None
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    title = (title or "").strip()
    artist = (artist or "").strip()
    album = (album or "").strip() or None

    if not title:
        return None, None, None

    # Use album in the term if available (helps ranking)
    term = " ".join(x for x in [title, artist, album] if x).strip()
    q = urllib.parse.quote(term)
    url = f"https://itunes.apple.com/search?term={q}&entity=song&limit=25"

    try:
        r = _HTTP.get(url, timeout=4)
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        if not results:
            return None, None, None

        best = None
        best_score = -10**9

        # If album is provided, prefer only results that match the album.
        filtered = results
        if album:
            want_album = _norm(album)
            filtered = [
                item for item in results
                if want_album and want_album in _norm(item.get("collectionName", ""))
            ]
            if filtered:
                results = filtered

        for item in results:
            s = _score_result(item, title, artist, album)
            if s > best_score:
                best_score = s
                best = item

        if not best or best_score < 40:
            # Score too low = search was probably garbage; fail gracefully
            return None, None, None

        artwork = (
            best.get("artworkUrl600")
            or best.get("artworkUrl100")
            or best.get("artworkUrl60")
        )
        artwork = _upgrade_artwork(artwork, 512)

        track_url = best.get("trackViewUrl")
        album_url = best.get("collectionViewUrl")

        return artwork, track_url, album_url
    except Exception:
        return None, None, None
