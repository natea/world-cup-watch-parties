"""
Resolve venues to Google `place_id`s (the venue-image backfill).

Matches each venue by name + address/city via the Places client and writes
`place_id` + `image_source="google_places"`. Low-confidence/ambiguous matches
are flagged with `needs_review=True` rather than storing a guessed identifier.

    python manage.py resolvevenueplaces            # resolve unresolved venues
    python manage.py resolvevenueplaces --refresh   # re-resolve even resolved ones
    python manage.py resolvevenueplaces --dry-run    # report, write nothing

Idempotent: venues that already have a `place_id` are skipped unless
`--refresh`. No-ops with no console error when `GOOGLE_PLACES_API_KEY` is unset
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
        parser.add_argument(
            "--confirm",
            nargs="+",
            metavar="SLUG",
            help=(
                "Promote flagged candidate(s) by slug: set "
                'image_source="google_places", resolve+store attribution, '
                "clear needs_review."
            ),
        )
        parser.add_argument(
            "--reject",
            nargs="+",
            metavar="SLUG",
            help=(
                "Reject flagged candidate(s) by slug: clear the candidate "
                "place_id and needs_review so the venue drops to the next tier."
            ),
        )

    def handle(self, *args, **options):
        # Review actions operate on existing candidates and run independently of
        # the resolve pass (and, for --confirm, no-op cleanly without a key).
        if options.get("confirm"):
            self._confirm(options["confirm"], options["dry_run"])
            return
        if options.get("reject"):
            self._reject(options["reject"], options["dry_run"])
            return

        if not places.is_enabled():
            self.stdout.write(
                "GOOGLE_PLACES_API_KEY not configured — nothing to resolve "
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
                    # Resolve the photo once now to capture the required
                    # attribution string, so it can be rendered with the image
                    # without a per-request lookup (Google requires attribution
                    # be displayed). The URL itself is short-lived, so we store
                    # only the attribution and let the proxy re-resolve the URL.
                    photo = places.photo_for_place(match.place_id)
                    venue.place_id = match.place_id
                    venue.image_source = "google_places"
                    venue.image_attribution = photo.attribution if photo else ""
                    venue.save(
                        update_fields=["place_id", "image_source", "image_attribution"]
                    )
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

    # --- review actions ----------------------------------------------------
    def _confirm(self, slugs, dry_run):
        """Promote a reviewed candidate to a confirmed Google photo source."""
        confirmed = 0
        for venue in Venue.objects.filter(slug__in=slugs).order_by("name"):
            if not venue.place_id:
                self.stdout.write(f"  ! {venue.slug}: no candidate place_id to confirm")
                continue
            self.stdout.write(f"  ✓ confirm {venue.slug} → {venue.place_id}")
            confirmed += 1
            if dry_run:
                continue
            # Resolve the photo once to capture attribution (no-ops to "" when
            # the key is unset; the proxy re-resolves the URL at request time).
            photo = places.photo_for_place(venue.place_id) if places.is_enabled() else None
            venue.image_source = "google_places"
            venue.image_attribution = photo.attribution if photo else ""
            venue.needs_review = False
            venue.save(
                update_fields=["image_source", "image_attribution", "needs_review"]
            )
        self._report_missing(slugs)
        verb = "Would confirm" if dry_run else "Confirmed"
        self.stdout.write(self.style.SUCCESS(f"{verb} {confirmed}."))

    def _reject(self, slugs, dry_run):
        """Reject a candidate: clear place_id + needs_review → next tier."""
        rejected = 0
        for venue in Venue.objects.filter(slug__in=slugs).order_by("name"):
            self.stdout.write(f"  ✗ reject {venue.slug}")
            rejected += 1
            if dry_run:
                continue
            venue.place_id = ""
            venue.image_source = ""
            venue.image_attribution = ""
            venue.needs_review = False
            venue.save(
                update_fields=[
                    "place_id",
                    "image_source",
                    "image_attribution",
                    "needs_review",
                ]
            )
        self._report_missing(slugs)
        verb = "Would reject" if dry_run else "Rejected"
        self.stdout.write(self.style.SUCCESS(f"{verb} {rejected}."))

    def _report_missing(self, slugs):
        found = set(Venue.objects.filter(slug__in=slugs).values_list("slug", flat=True))
        for slug in slugs:
            if slug not in found:
                self.stdout.write(f"  ? unknown venue slug: {slug}")


def _venue_address(venue: Venue) -> str:
    return ", ".join(p for p in (venue.address, venue.city) if p)
