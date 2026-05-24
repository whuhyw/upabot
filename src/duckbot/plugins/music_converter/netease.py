from typing import Optional, Tuple

import httpx

NETEASE_SEARCH_URL = "https://music.163.com/api/cloudsearch/pc"


async def search_netease(query: str) -> Optional[Tuple[str, int]]:
    params = {
        "csrf_token": "",
        "type": 1,
        "s": query,
        "offset": 0,
        "limit": 5,
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Referer": "https://music.163.com/",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(NETEASE_SEARCH_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError, KeyError):
        return None

    songs = (data.get("result") or {}).get("songs") or []
    if not songs:
        return None

    best = songs[0]
    song_name = best.get("name", "")
    song_id = best.get("id", 0)
    artists = ", ".join(a.get("name", "") for a in (best.get("artists") or []))
    full_name = f"{song_name} - {artists}" if artists else song_name

    return (full_name, song_id)
