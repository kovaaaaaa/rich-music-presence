import re
import requests
import time
import urllib.parse
import os
from functools import lru_cache
from typing import Optional, Tuple


def _normalize(value: str) -> str:
    value = value.lower()
    value = value.replace("&", "and")
    value = re.sub(r"\b(feat|featuring|ft)\b\.?", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split()).strip()


def _normalize_album(value: str) -> str:
    value = value.lower()
    # Drop common edition/format markers in parentheses/brackets.
    value = re.sub(r"[\(\[].*?[\)\]]", " ", value)
    value = re.sub(r"\b(deluxe|expanded|remaster(ed)?|edition|version|clean|explicit)\b", " ", value)
    return _normalize(value)


def _art_debug_enabled() -> bool:
    return os.getenv("RMP_ART_DEBUG", "").strip() in {"1", "true", "yes", "on"}


def _debug(msg: str):
    if _art_debug_enabled():
        print(f"[artwork] {msg}")


def _slugify_title(value: str) -> str:
    value = value.lower()
    value = re.sub(r"&", "and", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    value = re.sub(r"-{2,}", "-", value)
    return value


def _url_path_slug(url: str) -> str:
    try:
        path = urllib.parse.urlparse(url).path or ""
        parts = [p for p in path.split("/") if p]
        if not parts:
            return ""
        return parts[-2] if parts[-1].isdigit() and len(parts) >= 2 else parts[-1]
    except Exception:
        return ""

# returns (artwork_url, track_url, album_url)
@lru_cache(maxsize=512)
def lookup_artwork_and_urls(
    title: str, artist: str, album: Optional[str] = None
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    title = (title or "").strip()
    artist = (artist or "").strip()
    album = (album or "").strip()
    if not title:
        return None, None, None

    def _score(item: dict, title_norm: str, artist_norm: str, album_norm: str) -> int:
        score = 0
        track_name = _normalize(item.get("trackName", "") or "")
        artist_name = _normalize(item.get("artistName", "") or "")
        album_name = _normalize_album(item.get("collectionName", "") or "")

        title_tokens = set(title_norm.split())
        track_tokens = set(track_name.split())
        title_overlap = len(title_tokens & track_tokens) if title_tokens and track_tokens else 0

        if track_name and title_norm:
            if track_name == title_norm:
                score += 6
            elif title_norm in track_name or track_name in title_norm:
                score += 3

            if title_overlap:
                score += min(2, title_overlap)
            elif title_tokens:
                # Hard filter: if title doesn't overlap at all, this is almost always wrong.
                return -1

        if artist_name and artist_norm:
            if artist_name == artist_norm:
                score += 4
            elif artist_norm in artist_name or artist_name in artist_norm:
                score += 2

            artist_tokens = set(artist_norm.split())
            artist_name_tokens = set(artist_name.split())
            if artist_tokens and artist_name_tokens:
                overlap = len(artist_tokens & artist_name_tokens)
                if overlap:
                    score += 1
                elif artist_norm:
                    score -= 5

        if album_name and album_norm:
            if album_name == album_norm:
                score += 6
            elif album_norm in album_name or album_name in album_norm:
                score += 2
            else:
                score -= 2

        if item.get("artworkUrl600") or item.get("artworkUrl100"):
            score += 1

        return score

    def _pick_best(results: list, title_norm: str, artist_norm: str, album_norm: str) -> Optional[dict]:
        # If we have an album name, prefer results whose album overlaps at all.
        filtered = []
        if album_norm:
            for item in results:
                album_name = _normalize_album(item.get("collectionName", "") or "")
                if not album_name:
                    continue
                if album_name == album_norm or album_norm in album_name or album_name in album_norm:
                    filtered.append(item)
        pool = filtered or results
        scored = [(item, _score(item, title_norm, artist_norm, album_norm)) for item in pool]
        scored.sort(key=lambda x: x[1], reverse=True)
        item, best_score = scored[0]
        min_score = 4 if artist_norm else 3
        if best_score < min_score:
            return None
        return item

    title_norm = _normalize(title)
    artist_norm = _normalize(artist)
    album_norm = _normalize_album(album)

    # 1) iTunes slug-priority pass (if possible)
    slug = _slugify_title(title)
    if slug:
        term = f"{title} {artist} {album}".strip()
        q = urllib.parse.quote(term)
        url = f"https://itunes.apple.com/search?term={q}&entity=song&limit=8"
        try:
            r = _HTTP.get(url, timeout=4)
            r.raise_for_status()
            data = r.json()
            results = data.get("results", [])
            if results:
                slug_matches = []
                for item in results:
                    track_url = item.get("trackViewUrl") or ""
                    if not track_url:
                        continue
                    url_slug = _url_path_slug(track_url)
                    if url_slug == slug:
                        slug_matches.append(item)
                if slug_matches:
                    item = _pick_best(slug_matches, title_norm, artist_norm, album_norm)
                    if item:
                        artwork = item.get("artworkUrl600") or item.get("artworkUrl100")
                        track_url = item.get("trackViewUrl")
                        album_url = item.get("collectionViewUrl")
                        if artwork:
                            artwork = re.sub(r"/\d+x\d+", "/512x512", artwork)
                        _debug(
                            f"itunes slug match: '{item.get('trackName')}' on '{item.get('collectionName')}'"
                        )
                        return artwork, track_url, album_url
        except Exception:
            pass

    # 2) MusicBrainz + Cover Art Archive
    mb_artwork, mb_track_url, mb_album_url = _lookup_musicbrainz(title, artist, album)
    if mb_artwork:
        return mb_artwork, mb_track_url, mb_album_url

    # 3) iTunes fallback
    if album_norm:
        album_term = f"{album} {artist}".strip()
        album_q = urllib.parse.quote(album_term)
        album_url = f"https://itunes.apple.com/search?term={album_q}&entity=album&limit=10"
        try:
            r = _HTTP.get(album_url, timeout=4)
            r.raise_for_status()
            data = r.json()
            results = data.get("results", [])
            if results:
                scored = []
                for item in results:
                    a_name = _normalize(item.get("artistName", "") or "")
                    c_name = _normalize_album(item.get("collectionName", "") or "")
                    score = 0
                    if c_name == album_norm:
                        score += 8
                    elif album_norm in c_name or c_name in album_norm:
                        score += 4
                    if a_name and artist_norm:
                        if a_name == artist_norm:
                            score += 4
                        elif artist_norm in a_name or a_name in artist_norm:
                            score += 2
                        else:
                            score -= 2
                    if item.get("artworkUrl100") or item.get("artworkUrl60"):
                        score += 1
                    scored.append((item, score))
                scored.sort(key=lambda x: x[1], reverse=True)
                best_album, best_score = scored[0]
                if best_score >= 5:
                    artwork = best_album.get("artworkUrl100") or best_album.get("artworkUrl60")
                    album_url = best_album.get("collectionViewUrl")
                    if artwork:
                        artwork = re.sub(r"/\d+x\d+", "/512x512", artwork)
                    _debug(
                        f"itunes album match: '{best_album.get('collectionName')}' by '{best_album.get('artistName')}'"
                    )
                    return artwork, None, album_url
        except Exception:
            pass

    try:
        term = f"{title} {artist} {album}".strip()
        q = urllib.parse.quote(term)
        url = f"https://itunes.apple.com/search?term={q}&entity=song&limit=8"
        r = _HTTP.get(url, timeout=4)
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        if not results:
            return None, None, None

        item = _pick_best(results, title_norm, artist_norm, album_norm)
        if not item:
            return None, None, None
        artwork = item.get("artworkUrl600") or item.get("artworkUrl100")
        track_url = item.get("trackViewUrl")
        album_url = item.get("collectionViewUrl")  # album link

        if artwork:
            artwork = re.sub(r"/\d+x\d+", "/512x512", artwork)
        _debug(
            f"itunes track match: '{item.get('trackName')}' on '{item.get('collectionName')}'"
        )

        return artwork, track_url, album_url
    except Exception:
        return None, None, None


MB_USER_AGENT = "RichMusicPresence/1.0 (https://github.com/)"
MB_SEARCH_URL = "https://musicbrainz.org/ws/2/recording"
CAA_RELEASE_URL = "https://coverartarchive.org/release/{mbid}"
_HTTP = requests.Session()


def _mb_headers() -> dict:
    return {"User-Agent": MB_USER_AGENT}




def _mb_query(title: str, artist: str, album: str) -> str:
    parts = []
    if title:
        parts.append(f'recording:"{title}"')
    if artist:
        parts.append(f'artist:"{artist}"')
    if album:
        parts.append(f'release:"{album}"')
    return " AND ".join(parts)


def _pick_best_recording(recordings: list, title_norm: str, artist_norm: str, album_norm: str) -> Optional[dict]:
    def score(rec: dict) -> int:
        s = 0
        rec_title = _normalize(rec.get("title", "") or "")
        if rec_title == title_norm:
            s += 6
        elif title_norm and (title_norm in rec_title or rec_title in title_norm):
            s += 3

        rec_artists = " ".join([a.get("name", "") for a in rec.get("artist-credit", []) if isinstance(a, dict)])
        rec_artists = _normalize(rec_artists)
        if rec_artists == artist_norm:
            s += 4
        elif artist_norm and (artist_norm in rec_artists or rec_artists in artist_norm):
            s += 2

        releases = rec.get("releases", []) or []
        if releases and album_norm:
            for rel in releases:
                rel_title = _normalize_album(rel.get("title", "") or "")
                if rel_title == album_norm:
                    s += 2
                    break
                if album_norm in rel_title or rel_title in album_norm:
                    s += 1
                    break

        if rec.get("score"):
            try:
                s += int(rec["score"]) // 25
            except Exception:
                pass
        return s

    if not recordings:
        return None
    scored = [(rec, score(rec)) for rec in recordings]
    scored.sort(key=lambda x: x[1], reverse=True)
    rec, best = scored[0]
    if best < 5:
        return None
    return rec


def _pick_release_with_art(releases: list, album_norm: str) -> Optional[dict]:
    if not releases:
        return None
    scored = []
    for rel in releases:
        s = 0
        rel_title = _normalize_album(rel.get("title", "") or "")
        if album_norm:
            if rel_title == album_norm:
                s += 3
            elif album_norm in rel_title or rel_title in album_norm:
                s += 1
        if rel.get("cover-art-archive", {}).get("front"):
            s += 2
        if rel.get("cover-art-archive", {}).get("artwork"):
            s += 1
        scored.append((rel, s))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0][0]


def _lookup_musicbrainz(title: str, artist: str, album: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    title = (title or "").strip()
    artist = (artist or "").strip()
    album = (album or "").strip()
    if not title:
        return None, None, None

    title_norm = _normalize(title)
    artist_norm = _normalize(artist)
    album_norm = _normalize_album(album)

    params = {
        "query": _mb_query(title, artist, album),
        "fmt": "json",
        "limit": 5,
        "inc": "releases",
    }

    try:
        r = _HTTP.get(MB_SEARCH_URL, params=params, headers=_mb_headers(), timeout=6)
        r.raise_for_status()
        data = r.json()
        recordings = data.get("recordings", []) or []
        rec = _pick_best_recording(recordings, title_norm, artist_norm, album_norm)
        if not rec:
            return None, None, None

        releases = rec.get("releases", []) or []
        rel = _pick_release_with_art(releases, album_norm)
        if not rel:
            return None, None, None

        rel_id = rel.get("id")
        if not rel_id:
            return None, None, None

        # Be polite to MusicBrainz when followed by CAA requests.
        time.sleep(0.25)

        caa_url = CAA_RELEASE_URL.format(mbid=rel_id)
        art = _HTTP.get(caa_url, headers=_mb_headers(), timeout=6)
        if art.status_code == 404:
            return None, None, None
        art.raise_for_status()
        art_data = art.json()
        images = art_data.get("images", []) or []
        if not images:
            return None, None, None

        front = None
        for img in images:
            if img.get("front"):
                front = img
                break
        if not front:
            front = images[0]

        artwork_url = front.get("image")
        album_url = f"https://musicbrainz.org/release/{rel_id}"
        track_url = None
        _debug(
            f"musicbrainz match: '{rec.get('title')}' -> release '{rel.get('title')}'"
        )
        return artwork_url, track_url, album_url
    except Exception:
        return None, None, None
