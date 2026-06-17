"""Thin, fully isolated Google Places client.

ALL Google network access lives here. Two responsibilities:

  * `find_place(name, address)` — resolve a venue to a Google `place_id`
    (+ the photo resource name and the venue's display name, used to score
    match confidence) via the Places API (New) Text Search endpoint.
  * `photo_for_place(place_id)` — resolve a `place_id` to a current photo URL
    and the required attribution string via the Places API (New) Place Details
    + Photo media endpoints.

Design notes
------------
* The exact HTTP transport is confined to the private `_post`/`_get` helpers so
  tests monkeypatch one seam (or the public functions) and never hit the
  network.
* Everything no-ops (returns ``None``) when ``settings.GOOGLE_MAPS_API_KEY`` is
  empty, so the feature degrades to the category fallback with no key.
* We never download or persist photo bytes — `photo_for_place` returns a URL
  the proxy 302-redirects to, honoring Google's terms.
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Optional

from django.conf import settings

# Places API (New) endpoints.
_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"
# Photo media endpoint returns the bytes; with skipHttpRedirect=true it returns
# JSON containing a short-lived photoUri we redirect the client to.
_PHOTO_MEDIA_URL = "https://places.googleapis.com/v1/{name}/media"

# Default longest edge for fetched photos; bounds cost/bandwidth.
_PHOTO_MAX_PX = 1200


@dataclass(frozen=True)
class PlaceMatch:
    place_id: str
    display_name: str
    formatted_address: str
    photo_name: Optional[str]  # Places photo resource name, e.g. "places/X/photos/Y"


@dataclass(frozen=True)
class PlacePhoto:
    url: str
    attribution: str


def is_enabled() -> bool:
    """True when a Google Maps/Places API key is configured."""
    return bool(getattr(settings, "GOOGLE_MAPS_API_KEY", ""))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def find_place(name: str, address: str = "") -> Optional[PlaceMatch]:
    """Resolve a venue (by name + optional address) to a `PlaceMatch`.

    Returns ``None`` when the key is unset, the query is empty, or no place is
    found. Callers decide match confidence from the returned display name /
    address.
    """
    if not is_enabled():
        return None
    query = ", ".join(p for p in (name, address) if p).strip(", ")
    if not query:
        return None

    body = {"textQuery": query, "maxResultCount": 1}
    field_mask = "places.id,places.displayName,places.formattedAddress,places.photos"
    data = _post(_TEXT_SEARCH_URL, body, field_mask)
    if not data:
        return None
    places = data.get("places") or []
    if not places:
        return None
    top = places[0]
    photos = top.get("photos") or []
    return PlaceMatch(
        place_id=top.get("id", ""),
        display_name=(top.get("displayName") or {}).get("text", ""),
        formatted_address=top.get("formattedAddress", ""),
        photo_name=photos[0].get("name") if photos else None,
    )


def photo_for_place(place_id: str, max_px: int = _PHOTO_MAX_PX) -> Optional[PlacePhoto]:
    """Resolve a `place_id` to a current photo URL + attribution.

    Returns ``None`` when the key is unset, the place has no photo, or the
    lookup fails. Never persists bytes — the returned URL is short-lived and
    fetched on demand by the client via the proxy redirect.
    """
    if not is_enabled() or not place_id:
        return None

    details = _get(
        _PLACE_DETAILS_URL.format(place_id=place_id),
        field_mask="id,photos",
    )
    if not details:
        return None
    photos = details.get("photos") or []
    if not photos:
        return None

    photo = photos[0]
    photo_name = photo.get("name")
    if not photo_name:
        return None
    attribution = _attribution_from_photo(photo)

    media = _get(
        _PHOTO_MEDIA_URL.format(name=photo_name),
        params={"maxWidthPx": str(max_px), "skipHttpRedirect": "true"},
    )
    if not media:
        return None
    url = media.get("photoUri")
    if not url:
        return None
    return PlacePhoto(url=url, attribution=attribution)


def _attribution_from_photo(photo: dict) -> str:
    """Build the required attribution string from a photo's authorAttributions."""
    authors = photo.get("authorAttributions") or []
    names = [a.get("displayName", "").strip() for a in authors if a.get("displayName")]
    names = [n for n in names if n]
    if names:
        return "Photo by " + ", ".join(names) + " via Google"
    return "Photo via Google"


# ---------------------------------------------------------------------------
# Transport seam — the only place that touches the network. Tests monkeypatch
# `_post`/`_get` (or the public functions) so no live call is ever made.
# ---------------------------------------------------------------------------
def _headers(field_mask: Optional[str] = None) -> dict:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
    }
    if field_mask:
        headers["X-Goog-FieldMask"] = field_mask
    return headers


def _post(url: str, body: dict, field_mask: Optional[str] = None) -> Optional[dict]:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=_headers(field_mask),
        method="POST",
    )
    return _send(req)


def _get(
    url: str,
    field_mask: Optional[str] = None,
    params: Optional[dict] = None,
) -> Optional[dict]:
    if params:
        from urllib.parse import urlencode

        url = f"{url}?{urlencode(params)}"
    req = urllib.request.Request(url, headers=_headers(field_mask), method="GET")
    return _send(req)


def _send(req: "urllib.request.Request") -> Optional[dict]:
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        # Any transport/parse error degrades to the fallback rather than
        # surfacing an error to the user.
        return None
