"""Thin, fully isolated Wikimedia Commons client.

ALL Wikimedia network access lives here. One responsibility:

  * `find_image(name, city, lat, lng)` — resolve a public place to a
    CC-licensed Wikimedia Commons image (a stable file URL + the required
    attribution string), via the MediaWiki ``action=query`` API.

Design notes
------------
* Mirrors `events.places` for style/isolation: the exact HTTP transport is
  confined to the private `_get` seam so tests monkeypatch one place and never
  hit the network.
* Commons needs no API key, so the client is always-on — but it MUST fail
  closed: any error (or no confident result) returns ``None`` and the venue
  drops to the next image tier (the SVG category illustration). We NEVER raise.
* We persist only a stable file URL + attribution; we never rehost bytes.

Query strategy
--------------
We use the Commons API with ``generator=search`` over the file namespace
(``srnamespace=6``) for ``"<name> <city>"``, pulling ``imageinfo`` with the
``url`` and ``extmetadata`` props in one round trip. We accept a result only
when it carries a recognized free license (``LicenseShortName`` /
``UsageTerms``) — public-domain or any Creative Commons license — so we never
surface an unlicensed or non-free file. Attribution is built from the file's
artist + license: ``"Photo: <author>, <license> via Wikimedia Commons"``.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional

_COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"

# Longest edge for the thumbnail URL we store; bounds bandwidth on the client.
_THUMB_MAX_PX = 1200

# Markers that indicate a free (CC / public-domain) license. We require one of
# these in the file's license metadata before trusting the image.
_FREE_LICENSE_MARKERS = ("cc", "public domain", "pd", "creative commons")


@dataclass(frozen=True)
class WikiImage:
    url: str
    attribution: str


def is_enabled() -> bool:
    """Commons needs no key, so the client is always available."""
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def find_image(
    name: str,
    city: str = "",
    lat: Optional[float] = None,
    lng: Optional[float] = None,
) -> Optional[WikiImage]:
    """Resolve a public place to a CC-licensed Commons image.

    Returns ``None`` when the query is empty, nothing is found, or the only
    results are not under a recognized free license / any error occurs. The
    ``lat``/``lng`` args are accepted for a future geosearch refinement but the
    primary strategy is a name+city file search.
    """
    query = " ".join(p for p in (name, city) if p).strip()
    if not query:
        return None

    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",  # File: namespace
        "gsrlimit": "5",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": str(_THUMB_MAX_PX),
    }
    data = _get(_COMMONS_API_URL, params)
    if not data:
        return None

    pages = ((data.get("query") or {}).get("pages")) or {}
    if not pages:
        return None

    # Prefer the lowest search index (best match) among free-licensed results.
    candidates = sorted(
        pages.values(),
        key=lambda p: p.get("index", 1_000_000),
    )
    for page in candidates:
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        meta = info.get("extmetadata") or {}
        license_name = _meta_value(meta, "LicenseShortName") or _meta_value(
            meta, "UsageTerms"
        )
        if not _is_free_license(license_name):
            continue
        author = _strip_html(_meta_value(meta, "Artist"))
        return WikiImage(url=url, attribution=_build_attribution(author, license_name))
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _meta_value(meta: dict, key: str) -> str:
    entry = meta.get(key)
    if isinstance(entry, dict):
        return (entry.get("value") or "").strip()
    return ""


def _is_free_license(license_name: str) -> bool:
    if not license_name:
        return False
    low = license_name.lower()
    return any(marker in low for marker in _FREE_LICENSE_MARKERS)


def _strip_html(value: str) -> str:
    """Commons ``Artist`` metadata is often HTML (links). Reduce to plain text."""
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", "", value)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _build_attribution(author: str, license_name: str) -> str:
    license_name = (license_name or "").strip()
    parts = []
    if author:
        parts.append(author)
    if license_name:
        parts.append(license_name)
    if parts:
        return "Photo: " + ", ".join(parts) + " via Wikimedia Commons"
    return "Photo via Wikimedia Commons"


# ---------------------------------------------------------------------------
# Transport seam — the only place that touches the network. Tests monkeypatch
# `_get` (or the public `find_image`) so no live call is ever made.
# ---------------------------------------------------------------------------
def _get(url: str, params: dict) -> Optional[dict]:
    full = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        full,
        headers={
            # Commons asks for a descriptive User-Agent.
            "User-Agent": "WorldCupWatchParties/1.0 (venue images; contact via site)",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        # Fail closed: any transport/parse error degrades to the next tier.
        return None
