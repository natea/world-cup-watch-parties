"""
Resolve venues to Google `place_id`s (the venue-image backfill).

Matches each venue by name + address/city via the Places client and writes
`place_id` + `image_source="google_places"`. Low-confidence/ambiguous matches
are flagged with `needs_review=True` rather than storing a guessed identifier.

    python manage.py resolvevenueplaces            # resolve unresolved venues
    python manage.py resolvevenueplaces --refresh   # re-resolve even resolved ones
    python manage.py resolvevenueplaces --dry-run    # report, write nothing

Idempotent: venues that already have a `place_id` are skipped unless
`--refresh`. No-ops with no console error when `GOOGLE_MAPS_API_KEY` is unset
(the feature degrades to the category fallback). All Google access goes through
`events.places`, which tests monkeypatch — this command makes NO live network
call under test.
"""
from __future__ import annotations

from difflib import SequenceMatcher

from django.core.management.base import BaseCommand

from events import places
from events.models import Venue

# Below this name-similarity score a match is treated as ambiguous/low
# confidence and flagged for human review instead of being trusted.
CONFIDENCE_THRESHOLD = 0.6


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


class Command(BaseCommand):
    help = "Resolve venues to Google place_ids for venue images (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Re-resolve venues that already have a place_id.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing.",
        )

    def handle(self, *args, **options):
        if not places.is_enabled():
            self.stdout.write(
                "GOOGLE_MAPS_API_KEY not configured — nothing to resolve "
                "(venues use the category fallback)."
            )
            return

        refresh = options["refresh"]
        dry_run = options["dry_run"]

        resolved = flagged = skipped = 0
        for venue in Venue.objects.all().order_by("name"):
            if venue.place_id and not refresh:
                skipped += 1
                continue

            match = places.find_place(venue.name, _venue_address(venue))
            if match is None or not match.place_id:
                flagged += 1
                self.stdout.write(f"  ? no match: {venue.name}")
                if not dry_run:
                    venue.needs_review = True
                    venue.save(update_fields=["needs_review"])
                continue

            score = _similarity(venue.name, match.display_name)
            confident = score >= CONFIDENCE_THRESHOLD
            if confident:
                resolved += 1
                self.stdout.write(
                    f"  ✓ {venue.name} → {match.display_name} ({score:.2f})"
                )
                if not dry_run:
                    venue.place_id = match.place_id
                    venue.image_source = "google_places"
                    venue.save(update_fields=["place_id", "image_source"])
            else:
                flagged += 1
                self.stdout.write(
                    f"  ? ambiguous: {venue.name} ~ {match.display_name} ({score:.2f})"
                )
                if not dry_run:
                    # Still record the candidate place_id so a reviewer can
                    # verify it, but mark it for review and do NOT treat it as
                    # a confident source.
                    venue.place_id = match.place_id
                    venue.needs_review = True
                    venue.save(update_fields=["place_id", "needs_review"])

        verb = "Would resolve" if dry_run else "Resolved"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {resolved}, flagged {flagged} for review, skipped {skipped}."
            )
        )


def _venue_address(venue: Venue) -> str:
    return ", ".join(p for p in (venue.address, venue.city) if p)
