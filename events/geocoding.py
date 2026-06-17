"""
Resolve a user's ZIP, street address, or device location to coordinates that
drive the map's existing distance sort.

Two paths, by design:
  * ZIP     -> a bundled Massachusetts ZIP-centroid table (data/ma_zip_centroids
              .json). Offline, no key, no network. Distances are to the ZIP
              centroid, so the result is marked precision="zip" (approximate).
  * address -> the US Census Bureau geocoder (no key, US-only). Exact point,
              precision="address". Degrades to None on any failure so callers
              can fall back to a ZIP or no anchor.

User coordinates are returned for the request only; nothing here writes them
anywhere.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path

from django.conf import settings

CENSUS_URL = (
    "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
    "?address={addr}&benchmark=Public_AR_Current&format=json"
)
_ZIP_RE = re.compile(r"^\d{5}$")


@lru_cache(maxsize=1)
def _zip_table() -> dict[str, list[float]]:
    path = Path(settings.BASE_DIR) / "data" / "ma_zip_centroids.json"
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("zips", {})
    except (OSError, json.JSONDecodeError):
        return {}


def resolve_zip(zip_code: str) -> dict | None:
    """Bundled offline lookup. Returns a result dict or None (unknown/invalid)."""
    z = (zip_code or "").strip()
    if not _ZIP_RE.match(z):
        return None
    coords = _zip_table().get(z)
    if not coords:
        return None
    return {"lat": coords[0], "lng": coords[1], "label": f"ZIP {z}", "precision": "zip"}


def resolve_address(address: str, *, timeout: float = 6.0) -> dict | None:
    """US Census geocoder. Returns a result dict or None (no match / unavailable)."""
    addr = (address or "").strip()
    if len(addr) < 4:
        return None
    url = CENSUS_URL.format(addr=urllib.parse.quote(addr))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "worldcup-watcher/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        matches = data.get("result", {}).get("addressMatches", [])
        if not matches:
            return None
        m = matches[0]
        c = m["coordinates"]  # {x: lng, y: lat}
        return {
            "lat": float(c["y"]),
            "lng": float(c["x"]),
            "label": m.get("matchedAddress", addr),
            "precision": "address",
        }
    except Exception:
        # Network/HTTP/parse failure — caller falls back to ZIP or no anchor.
        return None


def resolve(*, zip_code: str | None = None, address: str | None = None) -> dict | None:
    """Resolve by whichever input is provided (address preferred when both)."""
    if address:
        return resolve_address(address)
    if zip_code:
        return resolve_zip(zip_code)
    return None
