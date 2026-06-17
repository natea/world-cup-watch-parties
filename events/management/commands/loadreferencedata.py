"""
Load reference data: teams and the canonical FIFA fixture list.

Reference data is small, fixed, and correctness-critical — a wrong kickoff time
poisons every screening derived from it. It therefore comes from a structured
source and is NEVER LLM-extracted. This command upserts teams by `fifa_code`
and matches by `fifa_match_number`, so re-running is idempotent.

    python manage.py loadreferencedata                      # built-in v1 seed
    python manage.py loadreferencedata --path fixtures.json  # authoritative list

The JSON shape is `{"teams": [...], "matches": [...]}` matching the `teams`
and `matches` arrays of the import contract. To load the full ~104-match FIFA
schedule, supply it via --path; the upsert-by-number contract means it is a
no-migration data step. Knockout fixtures whose opponents are unknown carry
null teams, placeholder labels, and a stable bracket_slot.
"""
from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from events.import_contract import MatchIn, TeamIn
from events.models import Match, Team

# --- Built-in v1 seed (Foxborough sample + two unresolved knockout fixtures) ---
# Reference data, hand-entered from an authoritative source. The two knockout
# fixtures exercise the "fixture exists before its teams do" path (PRD §8.5).
#
# Teams beyond the eight playing at Gillette (USA, Brazil, Croatia) are loaded
# because Boston venues are supporter hubs for them; affiliations need the team
# to resolve even when that team has no Foxborough fixture.
#
# NOTE: the five group-stage Gillette fixtures carry PROVISIONAL fifa_match_
# numbers — the research guide gives matchups + kickoff times but not the
# canonical FIFA numbers. Replace with the authoritative list via --path; the
# upsert-by-number contract makes that a no-migration data step.
SEED_TEAMS = [
    {"name": "Scotland", "fifa_code": "SCO", "flag_emoji": "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F", "group": "C", "confederation": "UEFA"},
    {"name": "Haiti", "fifa_code": "HAI", "flag_emoji": "\U0001F1ED\U0001F1F9", "group": "C", "confederation": "CONCACAF"},
    {"name": "Morocco", "fifa_code": "MAR", "flag_emoji": "\U0001F1F2\U0001F1E6", "fifa_rank": 7, "group": "C", "confederation": "CAF"},
    {"name": "France", "fifa_code": "FRA", "flag_emoji": "\U0001F1EB\U0001F1F7", "fifa_rank": 3, "group": "I", "confederation": "UEFA"},
    {"name": "Norway", "fifa_code": "NOR", "flag_emoji": "\U0001F1F3\U0001F1F4", "group": "I", "confederation": "UEFA"},
    {"name": "Iraq", "fifa_code": "IRQ", "flag_emoji": "\U0001F1EE\U0001F1F6", "group": "I", "confederation": "AFC"},
    {"name": "England", "fifa_code": "ENG", "flag_emoji": "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F", "fifa_rank": 4, "group": "L", "confederation": "UEFA"},
    {"name": "Ghana", "fifa_code": "GHA", "flag_emoji": "\U0001F1EC\U0001F1ED", "group": "L", "confederation": "CAF"},
    {"name": "United States", "fifa_code": "USA", "flag_emoji": "\U0001F1FA\U0001F1F8", "confederation": "CONCACAF"},
    {"name": "Brazil", "fifa_code": "BRA", "flag_emoji": "\U0001F1E7\U0001F1F7", "confederation": "CONMEBOL"},
    {"name": "Croatia", "fifa_code": "CRO", "flag_emoji": "\U0001F1ED\U0001F1F7", "confederation": "UEFA"},
]

# The seven Gillette Stadium ("Boston Stadium") matches, per the research guide.
SEED_MATCHES = [
    {
        "fifa_match_number": 22, "stage": "group", "group": "C", "kickoff": "2026-06-14T01:00:00Z",
        "host_city": "Foxborough", "host_stadium": "Gillette Stadium",
        "home_team_code": "HAI", "away_team_code": "SCO",
    },
    {
        "fifa_match_number": 40, "stage": "group", "group": "I", "kickoff": "2026-06-16T22:00:00Z",
        "host_city": "Foxborough", "host_stadium": "Gillette Stadium",
        "home_team_code": "IRQ", "away_team_code": "NOR",
    },
    {
        "fifa_match_number": 54, "stage": "group", "group": "C", "kickoff": "2026-06-19T22:00:00Z",
        "host_city": "Foxborough", "host_stadium": "Gillette Stadium",
        "home_team_code": "SCO", "away_team_code": "MAR",
    },
    {
        "fifa_match_number": 63, "stage": "group", "group": "L", "kickoff": "2026-06-23T20:00:00Z",
        "host_city": "Foxborough", "host_stadium": "Gillette Stadium",
        "home_team_code": "ENG", "away_team_code": "GHA",
    },
    {
        "fifa_match_number": 71, "stage": "group", "group": "I", "kickoff": "2026-06-26T19:00:00Z",
        "host_city": "Foxborough", "host_stadium": "Gillette Stadium",
        "home_team_code": "NOR", "away_team_code": "FRA",
    },
    # Gillette knockout fixtures — opponents TBD during the group stage.
    {
        "fifa_match_number": 88, "stage": "r32", "kickoff": "2026-06-29T20:30:00Z",
        "host_city": "Foxborough", "host_stadium": "Gillette Stadium",
        "home_placeholder": "Winner Group C", "away_placeholder": "Runner-up Group I",
        "bracket_slot": "R32-3",
    },
    {
        "fifa_match_number": 99, "stage": "qf", "kickoff": "2026-07-09T20:00:00Z",
        "host_city": "Foxborough", "host_stadium": "Gillette Stadium",
        "home_placeholder": "Winner R32-3", "away_placeholder": "Winner R32-7",
        "bracket_slot": "QF-2",
    },
]


class Command(BaseCommand):
    help = "Load teams and the canonical FIFA fixture list from a structured source (no LLM)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            help="Optional JSON file with {teams: [...], matches: [...]}. "
            "Omit to load the built-in v1 seed.",
        )

    def handle(self, *args, **opts):
        if opts.get("path"):
            try:
                with open(opts["path"], encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, json.JSONDecodeError) as exc:
                raise CommandError(f"Could not read reference data: {exc}")
            teams_raw = data.get("teams", [])
            matches_raw = data.get("matches", [])
        else:
            teams_raw = SEED_TEAMS
            matches_raw = SEED_MATCHES

        # Validate against the contract (no LLM involved — pure structured load).
        teams = [TeamIn.model_validate(t) for t in teams_raw]
        matches = [MatchIn.model_validate(m) for m in matches_raw]

        with transaction.atomic():
            team_by_code = self._load_teams(teams)
            n_matches = self._load_matches(matches, team_by_code)

        self.stdout.write(
            self.style.SUCCESS(
                f"OK: {len(team_by_code)} teams, {n_matches} matches loaded (idempotent)."
            )
        )

    def _load_teams(self, teams) -> dict[str, Team]:
        out = {}
        for t in teams:
            obj, _ = Team.objects.update_or_create(
                fifa_code=t.fifa_code,
                defaults=dict(
                    name=t.name,
                    flag_emoji=t.flag_emoji,
                    fifa_rank=t.fifa_rank,
                    group=t.group,
                    confederation=t.confederation,
                ),
            )
            out[t.fifa_code] = obj
        for team in Team.objects.all():
            out.setdefault(team.fifa_code, team)
        return out

    def _load_matches(self, matches, team_by_code) -> int:
        for m in matches:
            Match.objects.update_or_create(
                fifa_match_number=m.fifa_match_number,
                defaults=dict(
                    stage=m.stage.value,
                    group=m.group,
                    kickoff=m.kickoff,
                    host_city=m.host_city,
                    host_stadium=m.host_stadium,
                    home_team=team_by_code.get(m.home_team_code) if m.home_team_code else None,
                    away_team=team_by_code.get(m.away_team_code) if m.away_team_code else None,
                    home_placeholder=m.home_placeholder,
                    away_placeholder=m.away_placeholder,
                    bracket_slot=m.bracket_slot,
                ),
            )
        return len(matches)
