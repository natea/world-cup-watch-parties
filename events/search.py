"""
Typeahead search over venues and teams.

Matching and ranking run in Python over the full (small) venue/team sets, which
(a) keeps results identical on SQLite and PostgreSQL — case-insensitive `in`
has no backend-specific collation surprises — and (b) is trivially fast at the
current scale (~150 venues, 48 teams). A PostgreSQL trigram / full-text index
is the documented upgrade path if the dataset grows; it is not needed here.

Ranking tiers (lower = better, surfaced first):
  0  name / FIFA-code prefix
  1  whole-word (or word-prefix) name match, city, FIFA-code substring, or a
     supporter-hub match (club / affiliated team / affiliation note)
  2  name substring (not a prefix or word match)
  3  description-only match (venue notes)
"""
from __future__ import annotations

import re

from .models import Team, Venue, VenueType

MIN_QUERY_LEN = 2
DEFAULT_LIMIT = 10
MAX_LIMIT = 25

_VENUE_TYPE_LABELS = dict(VenueType.choices)


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _name_tier(text: str, ql: str) -> int | None:
    """Best tier for a name-like field (None if no match)."""
    low = text.lower()
    if low.startswith(ql):
        return 0
    words = _words(text)
    if any(w == ql for w in words) or any(w.startswith(ql) for w in words):
        return 1
    if ql in low:
        return 2
    return None


def _score_venue(v: Venue, ql: str) -> int | None:
    best: int | None = None

    def consider(t: int | None):
        nonlocal best
        if t is not None and (best is None or t < best):
            best = t

    consider(_name_tier(v.name, ql))
    if v.city and ql in v.city.lower():
        consider(1)
    # Supporter-hub signal: club name or affiliated team name/code — a strong,
    # intentful match. (Affiliation free-text notes are intentionally NOT matched
    # here: substrings like "England crowd" would spuriously hit "cro". Named
    # supporters groups like "Tartan Army" are caught via the venue's own notes.)
    for a in v.affiliations.all():
        if a.club and ql in a.club.lower():
            consider(1)
        if a.team and (ql in a.team.name.lower() or ql == a.team.fifa_code.lower()):
            consider(1)
    if v.notes and ql in v.notes.lower():
        consider(3)
    return best


def _score_team(t: Team, ql: str) -> int | None:
    best: int | None = None

    def consider(tier: int | None):
        nonlocal best
        if tier is not None and (best is None or tier < best):
            best = tier

    code = t.fifa_code.lower()
    if code == ql or code.startswith(ql):
        consider(0)
    elif ql in code:
        consider(1)
    consider(_name_tier(t.name, ql))
    return best


def _venue_sublabel(v: Venue) -> str:
    type_label = _VENUE_TYPE_LABELS.get(v.venue_type, v.venue_type)
    return f"{type_label} · {v.city}" if v.city else type_label


def _team_sublabel(t: Team) -> str:
    bits = [b for b in (t.confederation, t.fifa_code) if b]
    return " · ".join(bits) if bits else "National team"


def build_suggestions(query: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """Ranked, typed, length-capped suggestions for an autocomplete query."""
    q = (query or "").strip()
    if len(q) < MIN_QUERY_LEN:
        return []
    ql = q.lower()
    limit = max(1, min(limit, MAX_LIMIT))

    scored: list[tuple] = []  # (tier, kind_order, label_len, label_lower, suggestion)

    venues = Venue.objects.prefetch_related("affiliations", "affiliations__team")
    for v in venues:
        tier = _score_venue(v, ql)
        if tier is None:
            continue
        suggestion = {
            "type": "venue",
            "label": v.name,
            "sublabel": _venue_sublabel(v),
            "target": {"kind": "venue", "slug": v.slug},
        }
        scored.append((tier, 1, len(v.name), v.name.lower(), suggestion))

    for t in Team.objects.all():
        tier = _score_team(t, ql)
        if tier is None:
            continue
        label = f"{t.flag_emoji} {t.name}".strip()
        suggestion = {
            "type": "team",
            "label": label,
            "sublabel": _team_sublabel(t),
            "target": {"kind": "team", "code": t.fifa_code},
        }
        # Teams sort just ahead of venues at the same tier (kind_order 0).
        scored.append((tier, 0, len(t.name), t.name.lower(), suggestion))

    scored.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    return [row[4] for row in scored[:limit]]
