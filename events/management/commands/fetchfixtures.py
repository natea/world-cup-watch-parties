"""
Fetch the authoritative FIFA 2026 fixture list and write a reference-data bundle.

The schedule lives behind FIFA.com's undocumented internal API. The endpoint
and parameters below were obtained by reverse-engineering the fixtures page's
network traffic (capture-the-XHR, the technique libretto packages; here done via
the Playwright MCP server):

    GET https://api.fifa.com/api/v3/calendar/matches?language=en&count=500&idSeason=285023
        idCompetition=17 (men's World Cup), idSeason=285023 (2026)

Usage:
    python manage.py fetchfixtures                       # live fetch -> data/fifa_reference.json
    python manage.py fetchfixtures --season 285023 --out data/fifa_reference.json
    python manage.py fetchfixtures --source raw.json     # map a saved raw payload (offline)

This command only maps FIFA-JSON -> the existing reference-data contract
({teams, matches}). Loading is the separate, idempotent
`loadreferencedata --path <out>` step. Commit the produced file as the canonical
offline seed so routine seeding never depends on the live endpoint.
"""
from __future__ import annotations

import json
import urllib.request

from django.core.management.base import BaseCommand, CommandError

from events.import_contract import MatchIn, TeamIn

FIFA_URL = "https://api.fifa.com/api/v3/calendar/matches?language=en&count=500&idSeason={season}"
DEFAULT_SEASON = "285023"  # FIFA World Cup 2026

# FIFA "StageName" (English) -> our Stage enum value.
STAGE_MAP = {
    "First Stage": "group",
    "Round of 32": "r32",
    "Round of 16": "r16",
    "Quarter-final": "qf",
    "Semi-final": "sf",
    "Play-off for third place": "third",
    "Final": "final",
}

# FIFA 3-letter code -> (ISO 3166-1 alpha-2 for the flag emoji, confederation).
# England/Scotland use subdivision tag-sequence flags (handled in _flag).
TEAM_META = {
    "ALG": ("DZ", "CAF"), "ARG": ("AR", "CONMEBOL"), "AUS": ("AU", "AFC"),
    "AUT": ("AT", "UEFA"), "BEL": ("BE", "UEFA"), "BIH": ("BA", "UEFA"),
    "BRA": ("BR", "CONMEBOL"), "CAN": ("CA", "CONCACAF"), "CIV": ("CI", "CAF"),
    "COD": ("CD", "CAF"), "COL": ("CO", "CONMEBOL"), "CPV": ("CV", "CAF"),
    "CRO": ("HR", "UEFA"), "CUW": ("CW", "CONCACAF"), "CZE": ("CZ", "UEFA"),
    "ECU": ("EC", "CONMEBOL"), "EGY": ("EG", "CAF"), "ENG": ("_ENG", "UEFA"),
    "ESP": ("ES", "UEFA"), "FRA": ("FR", "UEFA"), "GER": ("DE", "UEFA"),
    "GHA": ("GH", "CAF"), "HAI": ("HT", "CONCACAF"), "IRN": ("IR", "AFC"),
    "IRQ": ("IQ", "AFC"), "JOR": ("JO", "AFC"), "JPN": ("JP", "AFC"),
    "KOR": ("KR", "AFC"), "KSA": ("SA", "AFC"), "MAR": ("MA", "CAF"),
    "MEX": ("MX", "CONCACAF"), "NED": ("NL", "UEFA"), "NOR": ("NO", "UEFA"),
    "NZL": ("NZ", "OFC"), "PAN": ("PA", "CONCACAF"), "PAR": ("PY", "CONMEBOL"),
    "POR": ("PT", "UEFA"), "QAT": ("QA", "AFC"), "RSA": ("ZA", "CAF"),
    "SCO": ("_SCO", "UEFA"), "SEN": ("SN", "CAF"), "SUI": ("CH", "UEFA"),
    "SWE": ("SE", "UEFA"), "TUN": ("TN", "CAF"), "TUR": ("TR", "UEFA"),
    "URU": ("UY", "CONMEBOL"), "USA": ("US", "CONCACAF"), "UZB": ("UZ", "AFC"),
}

_SUBDIVISION_FLAGS = {
    "_ENG": "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F",
    "_SCO": "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F",
}


def _flag(iso2: str) -> str:
    """Regional-indicator emoji from an ISO2 code (or a subdivision tag flag)."""
    if iso2 in _SUBDIVISION_FLAGS:
        return _SUBDIVISION_FLAGS[iso2]
    if len(iso2) != 2:
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in iso2.upper())


def _first_desc(value) -> str:
    """FIFA localized fields are lists of {Locale, Description}; take the first."""
    if isinstance(value, list) and value:
        return value[0].get("Description", "") or ""
    return ""


class Command(BaseCommand):
    help = "Fetch the FIFA 2026 fixtures and write a {teams, matches} reference bundle."

    def add_arguments(self, parser):
        parser.add_argument("--season", default=DEFAULT_SEASON, help="FIFA idSeason (default: 2026).")
        parser.add_argument("--out", default="data/fifa_reference.json")
        parser.add_argument(
            "--source",
            help="Map a saved raw FIFA payload (JSON with a Results array) instead of fetching.",
        )

    def handle(self, *args, **opts):
        raw = self._load_raw(opts)
        results = raw.get("Results") or raw.get("results") or []
        if not results:
            raise CommandError("No matches found in the FIFA payload.")

        matches = [self._map_match(m) for m in results]
        teams = self._collect_teams(results, matches)

        # Validate against the import contract before writing (no LLM involved).
        bundle = {
            "teams": [TeamIn.model_validate(t).model_dump(mode="json") for t in teams],
            "matches": [MatchIn.model_validate(m).model_dump(mode="json") for m in matches],
        }

        with open(opts["out"], "w", encoding="utf-8") as fh:
            json.dump(bundle, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {len(bundle['teams'])} teams, {len(bundle['matches'])} matches "
                f"-> {opts['out']}"
            )
        )

    # --- io ---
    def _load_raw(self, opts) -> dict:
        if opts.get("source"):
            try:
                with open(opts["source"], encoding="utf-8") as fh:
                    return json.load(fh)
            except (OSError, json.JSONDecodeError) as exc:
                raise CommandError(f"Could not read --source: {exc}")
        url = FIFA_URL.format(season=opts["season"])
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # network/HTTP/JSON — surface as a command error
            raise CommandError(f"FIFA fetch failed ({url}): {exc}")

    # --- mapping ---
    def _map_match(self, m: dict) -> dict:
        stage_name = _first_desc(m.get("StageName"))
        stage = STAGE_MAP.get(stage_name)
        if stage is None:
            raise CommandError(f"Unknown FIFA stage name: {stage_name!r}")

        group_desc = _first_desc(m.get("GroupName"))  # e.g. "Group A" or ""
        group = group_desc.replace("Group", "").strip() if group_desc else ""

        stadium = m.get("Stadium") or {}
        home, away = m.get("Home"), m.get("Away")
        number = int(m["MatchNumber"])

        return {
            "fifa_match_number": number,
            "stage": stage,
            "group": group,
            "kickoff": m["Date"],  # already UTC ISO8601
            "host_city": _first_desc(stadium.get("CityName")),
            "host_stadium": _first_desc(stadium.get("Name")),
            "home_team_code": (home or {}).get("IdCountry") if home else None,
            "away_team_code": (away or {}).get("IdCountry") if away else None,
            "home_placeholder": "" if home else (m.get("PlaceHolderA") or ""),
            "away_placeholder": "" if away else (m.get("PlaceHolderB") or ""),
            # Stable knockout slot so a later re-fetch re-resolves the same fixture.
            "bracket_slot": "" if stage == "group" else f"{stage}-{number}",
        }

    def _collect_teams(self, results: list, matches: list) -> list:
        names: dict[str, str] = {}
        for m in results:
            for side in ("Home", "Away"):
                t = m.get(side)
                if t and t.get("IdCountry"):
                    names[t["IdCountry"]] = _first_desc(t.get("TeamName")) or t["IdCountry"]

        # Each team's group letter, from its group-stage fixture.
        group_of: dict[str, str] = {}
        for mm in matches:
            if mm["stage"] == "group" and mm["group"]:
                for code in (mm["home_team_code"], mm["away_team_code"]):
                    if code:
                        group_of.setdefault(code, mm["group"])

        teams = []
        for code in sorted(names):
            iso2, confed = TEAM_META.get(code, ("", ""))
            teams.append(
                {
                    "name": names[code],
                    "fifa_code": code,
                    "flag_emoji": _flag(iso2),
                    "group": group_of.get(code, ""),
                    "confederation": confed,
                }
            )
        return teams
