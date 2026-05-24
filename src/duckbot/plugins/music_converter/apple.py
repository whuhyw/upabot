from typing import Tuple, Optional
from urllib.parse import urlparse, parse_qs

import httpx


def parse_apple_music_url(url: str) -> Optional[Tuple[str, str]]:
    parsed = urlparse(url)
    parts = parsed.path.rstrip("/").split("/")

    if len(parts) < 5:
        return None

    media_type = parts[2]
    slug = parts[3]
    storefront = parts[1]

    track_id = None
    if media_type == "album":
        qs = parse_qs(parsed.query)
        track_id = qs.get("i", [None])[0]

    term = slug.replace("-", " ").strip()
    if not term:
        return None
    return (term, track_id, storefront)


async def search_itunes(term: str, storefront: str = "us") -> Optional[Tuple[str, str]]:
    params = {
        "term": term,
        "entity": "song",
        "limit": 1,
        "country": storefront,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://itunes.apple.com/search",
                params=params,
                headers={"User-Agent": "duckbot/0.1"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError:
        return None

    results = data.get("results") or []
    if not results:
        return None

    r = results[0]
    title = r.get("trackName") or ""
    artist = r.get("artistName") or ""
    if title and artist:
        return (title.strip(), artist.strip())
    return None


async def extract_apple_music_metadata(url: str) -> Optional[Tuple[str, str]]:
    parsed = parse_apple_music_url(url)
    if not parsed:
        return None

    term, track_id, storefront = parsed

    result = await search_itunes(term, storefront)
    if result:
        return result

    title = term.title()
    return (title, "")
