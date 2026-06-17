"""
Typeahead search over venues and teams.

Matching and ranking run in Python over the full (small) venue/team sets, which
(a) keeps results identical on SQLite and PostgreSQL — case-insensitive `in`
has no backend-specific collation surprises — and (b) is trivially fast at the
current scale (~150 venues, 48 teams). A PostgreSQL trigram / full-text index
is the documented upgrade path if the dataset grows; it is not needed here.

Two matching aids on top of plain substring matching:
  * Aliases — FIFA uses official short names ("USA", "Türkiye", "Côte d'Ivoire",
    "Korea Republic"). A small synonym map lets the common names people type
    ("united states", "turkey", "ivory coast", "south korea") resolve. Fuzzy
    matching can't bridge these — "united states" and "USA" share no characters.
  * Fuzzy fallback — a difflib similarity pass (no extra dependency) tolerates
    typos ("croatica" → Croatia, "banshe" → Banshee), ranked below exact matches.

Ranking tiers (lower = better, surfaced first):
  0  name / FIFA-code / alias prefix
  1  whole-word (or word-prefix) name match, city, FIFA-code substring,
     alias substring, or a supporter-hub match (club / affiliated team)
  2  name substring (not a prefix or word match)
  3  description-only match (venue notes)
  4  fuzzy (typo-tolerant) match
"""
from __future__ import annotations

import difflib
import re

from .models import Team, Venue, VenueType

MIN_QUERY_LEN = 2
DEFAULT_LIMIT = 10
MAX_LIMIT = 25

# Fuzzy matching kicks in only as a fallback, for queries long enough that a
# similarity score is meaningful.
FUZZY_TIER = 4
FUZZY_THRESHOLD = 0.8
FUZZY_MIN_LEN = 4

# Common names people type -> FIFA code, for teams whose official FIFA name
# differs from the everyday name. Keyed by fifa_code; values are lowercase.
TEAM_ALIASES = {
    "USA": ["united states", "america", "usmnt", "stars and stripes"],
    "KOR": ["south korea", "korea"],
    "TUR": ["turkey", "turkiye"],
    "CIV": ["ivory coast", "cote d'ivoire", "cote divoire"],
    "CPV": ["cape verde"],
    "COD": ["dr congo", "democratic republic of congo", "congo"],
    "NED": ["holland"],
    "IRN": ["iran"],
    "KSA": ["saudi arabia", "saudi"],
}

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


def _alias_tier(aliases: list[str], ql: str) -> int | None:
    best: int | None = None
    for a in aliases:
        if a == ql or a.startswith(ql):
            return 0
        if ql in a:
            best = 1
    return best


def _fuzzy_match(ql: str, targets: list[str]) -> bool:
    """True if the query is similar enough to any target (or one of its words)."""
    if len(ql) < FUZZY_MIN_LEN:
        return False
    for t in targets:
        if not t:
            continue
        tl = t.lower()
        if difflib.SequenceMatcher(None, ql, tl).ratio() >= FUZZY_THRESHOLD:
            return True
        for w in _words(tl):
            if len(w) >= 3 and difflib.SequenceMatcher(None, ql, w).ratio() >= FUZZY_THRESHOLD:
                return True
    return False


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
    hub_names: list[str] = []
    for a in v.affiliations.all():
        if a.club:
            hub_names.append(a.club)
            if ql in a.club.lower():
                consider(1)
        if a.team:
            hub_names.append(a.team.name)
            if ql in a.team.name.lower() or ql == a.team.fifa_code.lower():
                consider(1)
    if v.notes and ql in v.notes.lower():
        consider(3)
    # Fuzzy fallback over the venue name and its supporter-hub names (so a typo'd
    # club like "liverpol" still surfaces the Liverpool bars).
    if best is None and _fuzzy_match(ql, [v.name, *hub_names]):
        consider(FUZZY_TIER)
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
    aliases = TEAM_ALIASES.get(t.fifa_code, [])
    consider(_alias_tier(aliases, ql))
    if best is None and _fuzzy_match(ql, [t.name, *aliases]):
        consider(FUZZY_TIER)
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
