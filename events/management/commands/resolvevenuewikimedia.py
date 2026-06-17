"""
Resolve venues to Wikimedia Commons images (the second image tier).

For venues NOT confirmed on the Google tier (`image_source != "google_places"`)
and without an `image_url`, this matches the venue against Wikimedia Commons via
`events.wikimedia` and, on a confident hit, stores `image_url` +
`image_attribution` + `image_source="wikimedia"`. Venues with no hit keep
falling through to the honest SVG category illustration.

    python manage.py resolvevenuewikimedia            # resolve eligible venues
    python manage.py resolvevenuewikimedia --refresh   # re-resolve wikimedia ones too
    python manage.py resolvevenuewikimedia --dry-run    # report, write nothing

Idempotent: venues already on the google_places or wikimedia tier are skipped
unless `--refresh` (which re-resolves only the wikimedia tier — confirmed Google
photos are never overwritten). All Wikimedia access goes through
`events.wikimedia`, which tests monkeypatch — this command makes NO live network
call under test, and fails closed (leaves the fallback) on any error.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from events import wikimedia
from events.models import Venue


class Command(BaseCommand):
    help = "Resolve venues to Wikimedia Commons images (idempotent, fails closed)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Re-resolve venues already on the wikimedia tier.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing.",
        )

    def handle(self, *args, **options):
        refresh = options["refresh"]
        dry_run = options["dry_run"]

        resolved = missed = skipped = 0
        for venue in Venue.objects.all().order_by("name"):
            # Never touch a confirmed Google photo.
            if venue.image_source == "google_places":
                skipped += 1
                continue
            already_wikimedia = venue.image_source == "wikimedia" and venue.image_url
            if already_wikimedia and not refresh:
                skipped += 1
                continue
            # Skip venues that already carry an image_url (some other tier) unless
            # refreshing the wikimedia tier specifically.
            if venue.image_url and not already_wikimedia:
                skipped += 1
                continue

            hit = wikimedia.find_image(
                venue.name,
                city=venue.city,
                lat=float(venue.latitude) if venue.latitude is not None else None,
                lng=float(venue.longitude) if venue.longitude is not None else None,
            )
            if hit is None or not hit.url:
                missed += 1
                self.stdout.write(f"  · no commons image: {venue.name}")
                continue

            resolved += 1
            self.stdout.write(f"  ✓ {venue.name} → {hit.url}")
            if not dry_run:
                venue.image_url = hit.url
                venue.image_attribution = hit.attribution
                venue.image_source = "wikimedia"
                venue.save(
                    update_fields=["image_url", "image_attribution", "image_source"]
                )

        verb = "Would resolve" if dry_run else "Resolved"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {resolved} via Wikimedia, {missed} with no image "
                f"(stay on fallback), skipped {skipped}."
            )
        )
