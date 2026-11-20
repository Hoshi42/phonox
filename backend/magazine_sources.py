"""Free public artist background for the magazine: Wikipedia, MusicBrainz and Discogs profiles.

Every lookup is best effort. A failing or empty source simply contributes nothing.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

import requests

from backend.agent.metadata import DISCOGS_API_BASE, MUSICBRAINZ_API_BASE, MUSICBRAINZ_HEADERS, _discogs_headers, musicbrainz_enabled
from backend.magazine_models import MagazineSource

logger = logging.getLogger(__name__)
TIMEOUT = 6
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_HEADERS = {"User-Agent": "Phonox/1.0 (https://github.com/hoshhie/phonox)"}
MUSIC_WORDS = ("band", "musician", "singer", "group", "duo", "rapper", "composer", "producer", "dj", "trio")
EXTRACT_LIMIT = 2500


@dataclass
class ArtistBackground:
    """Evidence about one artist; `summary` is a vetted Wikipedia text that is safe to print without AI."""
    evidence: list[tuple[MagazineSource, str]] = field(default_factory=list)
    summary: str = ""
    summary_source: MagazineSource | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _is_same_artist(title: str, name: str) -> bool:
    title, name = title.casefold().strip(), name.casefold().strip()
    if title == name:
        return True
    match = re.fullmatch(re.escape(name) + r" \((.+)\)", title)
    return bool(match and any(word in match.group(1).split() for word in MUSIC_WORDS))


def _wikipedia(name: str) -> tuple[MagazineSource, str] | None:
    """Page titled exactly like the artist, preferring the "(band)"/"(musician)" page of an ambiguous name."""
    qualified = [f"{name} ({kind})" for kind in MUSIC_WORDS[:5]]
    response = requests.get(WIKIPEDIA_API, headers=WIKIPEDIA_HEADERS, timeout=TIMEOUT, params={
        "action": "query", "format": "json", "redirects": 1, "titles": "|".join(qualified + [name]),
        "prop": "extracts|pageprops", "ppprop": "disambiguation", "exintro": 1, "explaintext": 1, "exlimit": "max",
    })
    response.raise_for_status()
    pages = {page.get("title", ""): page for page in (response.json().get("query") or {}).get("pages", {}).values()}
    for title in [*qualified, name]:
        page = next((item for key, item in pages.items() if key.casefold() == title.casefold()), None)
        extract = ((page or {}).get("extract") or "").strip()
        if not extract or "disambiguation" in (page.get("pageprops") or {}):
            continue
        if not _is_same_artist(page["title"], name):
            continue
        if page["title"].casefold() == name.casefold() and not re.search(r"\b(?:" + "|".join(MUSIC_WORDS) + r")s?\b", extract.lower()):
            continue  # an unqualified title can belong to something else entirely
        url = "https://en.wikipedia.org/wiki/" + page["title"].replace(" ", "_")
        return MagazineSource(title=f"Wikipedia: {page['title']}", url=url, accessed_at=_now()), extract[:EXTRACT_LIMIT]
    return None


def _musicbrainz(name: str) -> tuple[MagazineSource, str] | None:
    response = requests.get(f"{MUSICBRAINZ_API_BASE}/artist", headers=MUSICBRAINZ_HEADERS, timeout=TIMEOUT,
                            params={"query": f'artist:"{name}"', "fmt": "json", "limit": 1})
    response.raise_for_status()
    artists = response.json().get("artists") or []
    if not artists or artists[0].get("name", "").casefold() != name.casefold() or artists[0].get("score", 0) < 90:
        return None
    artist = artists[0]
    span = artist.get("life-span") or {}
    details = {
        "type": artist.get("type"), "country": artist.get("country"),
        "area": (artist.get("area") or {}).get("name"),
        "begin": span.get("begin"), "end": span.get("end"),
        "disambiguation": artist.get("disambiguation"),
        "tags": [tag["name"] for tag in sorted(artist.get("tags") or [], key=lambda t: -t.get("count", 0))[:6]],
    }
    text = ", ".join(f"{key}: {value}" for key, value in details.items() if value)
    if not text:
        return None
    source = MagazineSource(title="MusicBrainz artist record", url=f"https://musicbrainz.org/artist/{artist['id']}",
                            accessed_at=_now())
    return source, text


def _discogs_profile(name: str, pace: Callable[[int], None] | None = None) -> tuple[MagazineSource, str] | None:
    if not os.getenv("DISCOGS_TOKEN", "").strip():
        return None
    headers = _discogs_headers()
    if pace:
        pace(2)
    response = requests.get(f"{DISCOGS_API_BASE}/database/search", headers=headers, timeout=TIMEOUT,
                            params={"type": "artist", "q": name, "per_page": 5})
    response.raise_for_status()
    hit = next((item for item in response.json().get("results", [])
                if re.sub(r"\s*\(\d+\)$", "", item.get("title", "")).casefold() == name.casefold()), None)
    if hit is None:
        return None
    detail = requests.get(f"{DISCOGS_API_BASE}/artists/{hit['id']}", headers=headers, timeout=TIMEOUT)
    detail.raise_for_status()
    data = detail.json()
    profile = re.sub(r"\[[a-z]=?([^\]]*)\]|\[/[a-z]\]", r"\1", data.get("profile") or "").strip()
    if not profile:
        return None
    source = MagazineSource(title="Discogs artist profile", url=data.get("uri") or f"https://www.discogs.com/artist/{hit['id']}",
                            accessed_at=_now())
    return source, profile[:EXTRACT_LIMIT]


def artist_background(name: str, pace: Callable[[int], None] | None = None) -> ArtistBackground:
    """Wikipedia first; Discogs and MusicBrainz only fill in when Wikipedia has no matching page.

    `pace(requests)` is called before rate-limited Discogs requests.
    """
    background = ArtistBackground()
    lookups = [("Wikipedia", _wikipedia), ("Discogs", lambda value: _discogs_profile(value, pace))]
    if musicbrainz_enabled():
        lookups.append(("MusicBrainz", _musicbrainz))
    for label, lookup in lookups:
        if background.summary:
            break
        try:
            found = lookup(name)
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.info("%s artist lookup failed for %s: %s", label, name, exc)
            continue
        if found:
            source, text = found
            background.evidence.append((source, text))
            if label == "Wikipedia":
                background.summary, background.summary_source = text, source
    return background
