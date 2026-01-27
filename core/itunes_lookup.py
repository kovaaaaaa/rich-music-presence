import requests
import urllib.parse
from functools import lru_cache
from typing import Optional, Tuple

# returns (artwork_url, track_url, album_url)
@lru_cache(maxsize=512)
def lookup_artwork_and_urls(title: str, artist: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    title = (title or "").strip()
    artist = (artist or "").strip()
    if not title:
        return None, None, None

    term = f"{title} {artist}".strip()
    q = urllib.parse.quote(term)
    url = f"https://itunes.apple.com/search?term={q}&entity=song&limit=1"

    try:
        r = requests.get(url, timeout=4)
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        if not results:
            return None, None, None

        item = results[0]
        artwork = item.get("artworkUrl600") or item.get("artworkUrl100")
        track_url = item.get("trackViewUrl")
        album_url = item.get("collectionViewUrl")  # album link

        if artwork and "100x100" in artwork:
            artwork = artwork.replace("100x100", "512x512")

        return artwork, track_url, album_url
    except Exception:
        return None, None, None
