"""
Idempotent importer.

Usage:
    python manage.py importwatchparties sample_data.json
    python manage.py importwatchparties sample_data.json --skip-materialize

Validates the JSON against ImportBundle, then upserts everything by natural key
inside a single transaction. Safe to re-run: each entity is update_or_create'd,
so a corrected export overwrites the prior load instead of duplicating it. The
import finishes by materializing ScreeningPolicy rules into concrete Screening
rows so every view (schedule / map / team) populates uniformly.

Reference data (teams + matches) is normally loaded first via
`loadreferencedata`; if the bundle also carries teams/matches they are upserted
here too, but venues/screenings/policies are the LLM-extractable layer this
command primarily exists for.
"""
from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from events.import_contract import ImportBundle
from events.models import (
    Match,
    Screening,
    ScreeningPolicy,
    Team,
    Venue,
    VenueAffiliation,
)


class Command(BaseCommand):
    help = "Import teams, matches, venues, affiliations, screenings, and policies from a JSON bundle."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument(
            "--skip-materialize",
            action="store_true",
            help="Do not expand ScreeningPolicy rules into Screening rows.",
        )

    def handle(self, *args, **opts):
        try:
            with open(opts["path"], encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Could not read JSON: {exc}")

        # Validate BEFORE opening a transaction: nothing reaches the DB unvalidated.
        bundle = ImportBundle.model_validate(raw)  # raises on invalid data

        with transaction.atomic():
            teams = self._load_teams(bundle)
            matches = self._load_matches(bundle, teams)
            venues = self._load_venues(bundle, teams)
            self._load_screenings(bundle, venues, matches)
            policies = self._load_policies(bundle, venues, teams, matches)

        generated = 0
        if not opts["skip_materialize"]:
            for p in policies:
                generated += p.materialize()

        self.stdout.write(
            self.style.SUCCESS(
                f"OK: {len(teams)} teams, {len(matches)} matches, {len(venues)} venues, "
                f"{len(policies)} policies ({generated} screenings generated)."
            )
        )

    # --- loaders, in dependency order ---
    def _load_teams(self, bundle) -> dict[str, Team]:
        out = {}
        for t in bundle.teams:
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
        # Include teams already in the DB so screenings/policies referencing
        # them resolve even when the bundle only carries the venue layer.
        for team in Team.objects.all():
            out.setdefault(team.fifa_code, team)
        return out

    def _load_matches(self, bundle, teams) -> dict[int, Match]:
        out = {}
        for m in bundle.matches:
            obj, _ = Match.objects.update_or_create(
                fifa_match_number=m.fifa_match_number,
                defaults=dict(
                    stage=m.stage.value,
                    group=m.group,
                    kickoff=m.kickoff,
                    host_city=m.host_city,
                    host_stadium=m.host_stadium,
                    home_team=teams.get(m.home_team_code) if m.home_team_code else None,
                    away_team=teams.get(m.away_team_code) if m.away_team_code else None,
                    home_placeholder=m.home_placeholder,
                    away_placeholder=m.away_placeholder,
                    bracket_slot=m.bracket_slot,
                ),
            )
            out[m.fifa_match_number] = obj
        for match in Match.objects.all():
            if match.fifa_match_number is not None:
                out.setdefault(match.fifa_match_number, match)
        return out

    def _load_venues(self, bundle, teams) -> dict[str, Venue]:
        out = {}
        for v in bundle.venues:
            obj, _ = Venue.objects.update_or_create(
                slug=v.slug,
                defaults=dict(
                    name=v.name,
                    venue_type=v.venue_type.value,
                    environment=v.environment.value,
                    address=v.address,
                    city=v.city,
                    region=v.region.value,
                    latitude=v.latitude,
                    longitude=v.longitude,
                    serves_alcohol=v.serves_alcohol,
                    default_min_age=v.default_min_age,
                    evening_min_age=v.evening_min_age,
                    evening_cutoff=v.evening_cutoff,
                    capacity=v.capacity,
                    has_food=v.has_food,
                    website=v.website,
                    source=v.source,
                    source_url=v.source_url,
                    needs_review=v.needs_review,
                    notes=v.notes,
                ),
            )
            # affiliations: clean-replace so re-imports stay consistent
            obj.affiliations.all().delete()
            for a in v.affiliations:
                VenueAffiliation.objects.create(
                    venue=obj,
                    affiliation_type=a.affiliation_type.value,
                    team=teams.get(a.team_code) if a.team_code else None,
                    club=a.club,
                    valid_from=a.valid_from,
                    valid_to=a.valid_to,
                    note=a.note,
                )
            out[v.slug] = obj
        return out

    def _load_screenings(self, bundle, venues, matches):
        for s in bundle.screenings:
            venue, match = venues.get(s.venue_slug), matches.get(s.match_number)
            if not venue or not match:
                self.stderr.write(
                    f"  skip screening: unknown venue/match "
                    f"({s.venue_slug} / {s.match_number})"
                )
                continue
            Screening.objects.update_or_create(
                venue=venue,
                match=match,
                starts_at=s.starts_at,
                defaults=dict(
                    ends_at=s.ends_at,
                    cost_type=s.cost_type.value,
                    registration_required=s.registration_required,
                    entry_guaranteed=s.entry_guaranteed,
                    price_note=s.price_note,
                    age_override=s.age_override,
                    is_generated=False,
                    source=s.source,
                    source_url=s.source_url,
                    needs_review=s.needs_review,
                    notes=s.notes,
                ),
            )

    def _load_policies(self, bundle, venues, teams, matches) -> list[ScreeningPolicy]:
        out = []
        for v in bundle.venues:
            venue = venues[v.slug]
            venue.policies.all().delete()  # clean-replace
            # Drop this venue's generated screenings so re-materialization is a
            # clean rebuild, not an accumulation. Without this, re-importing after
            # a policy/fixture change (e.g. remapped match numbers) leaves stale
            # generated rows behind on a non-flushed database (i.e. production).
            # Authored screenings (is_generated=False) are preserved.
            venue.screenings.filter(is_generated=True).delete()
            for p in v.policies:
                policy = ScreeningPolicy.objects.create(
                    venue=venue,
                    policy_type=p.policy_type.value,
                    default_cost_type=p.default_cost_type.value,
                    source=v.source,
                )
                if p.team_codes:
                    policy.teams.set([teams[c] for c in p.team_codes if c in teams])
                if p.match_numbers:
                    policy.matches.set([matches[n] for n in p.match_numbers if n in matches])
                out.append(policy)
        return out
