"""DRF serializers shaping the three view responses.

Match serialization always emits a TBD-safe label and resolved-or-placeholder
team info, so unresolved knockout fixtures render without special-casing in the
client.
"""
from __future__ import annotations

from rest_framework import serializers
from rest_framework.reverse import reverse

from .models import Match, Screening, Team, Venue, VenueAffiliation


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["name", "fifa_code", "flag_emoji", "fifa_rank", "group", "confederation"]


class MatchSerializer(serializers.ModelSerializer):
    label = serializers.CharField(read_only=True)
    is_resolved = serializers.BooleanField(read_only=True)
    home_team = TeamSerializer(read_only=True)
    away_team = TeamSerializer(read_only=True)

    class Meta:
        model = Match
        fields = [
            "fifa_match_number",
            "stage",
            "group",
            "kickoff",
            "host_city",
            "host_stadium",
            "home_team",
            "away_team",
            "home_placeholder",
            "away_placeholder",
            "bracket_slot",
            "label",
            "is_resolved",
        ]


class AffiliationSerializer(serializers.ModelSerializer):
    team = TeamSerializer(read_only=True)

    class Meta:
        model = VenueAffiliation
        fields = ["affiliation_type", "team", "club", "valid_from", "valid_to", "note"]


def fallback_image_url(venue_type: str) -> str:
    """URL (relative to the static front end) of the category illustration."""
    return f"/venue-fallbacks/{venue_type}.png"


class VenueSerializer(serializers.ModelSerializer):
    affiliations = AffiliationSerializer(many=True, read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Venue
        fields = [
            "name",
            "slug",
            "venue_type",
            "environment",
            "address",
            "city",
            "region",
            "latitude",
            "longitude",
            "serves_alcohol",
            "capacity",
            "has_food",
            "website",
            "affiliations",
            "image",
            "source",
            "source_url",
            "needs_review",
            "notes",
            "updated_at",
        ]

    def get_image(self, obj: Venue) -> dict:
        """Uniform image object, resolved over a three-tier chain:

          1. **Confirmed Google photo** (`image_source == "google_places"` with
             a `place_id`) — served via the attributed proxy. The backfill sets
             this only for high-confidence matches; ambiguous matches keep a
             candidate `place_id` but leave `image_source` blank so they fall
             through rather than show an unverified photo of the wrong place.
          2. **Wikimedia Commons photo** (`image_source == "wikimedia"` with an
             `image_url`) — a CC-licensed image of a public place, with its
             required attribution.
          3. **Honest SVG category illustration** keyed by `venue_type` — never
             implies it's a photo of the specific venue.

        (Unsplash/stock imagery was considered and rejected: it would
        misrepresent the specific venue.)
        """
        if obj.place_id and obj.image_source == "google_places":
            request = self.context.get("request")
            url = reverse("events:venue-photo", kwargs={"slug": obj.slug}, request=request)
            return {
                "url": url,
                "attribution": obj.image_attribution or None,
                "source": "google_places",
            }
        if obj.image_source == "wikimedia" and obj.image_url:
            return {
                "url": obj.image_url,
                "attribution": obj.image_attribution or None,
                "source": "wikimedia",
            }
        return {
            "url": fallback_image_url(obj.venue_type),
            "attribution": None,
            "source": "fallback",
        }


class ScreeningSerializer(serializers.ModelSerializer):
    venue = VenueSerializer(read_only=True)
    match = MatchSerializer(read_only=True)
    is_free = serializers.BooleanField(read_only=True)
    is_family_friendly = serializers.BooleanField(read_only=True)

    class Meta:
        model = Screening
        fields = [
            "id",
            "venue",
            "match",
            "starts_at",
            "ends_at",
            "cost_type",
            "registration_required",
            "entry_guaranteed",
            "price_note",
            "age_override",
            "is_generated",
            "is_free",
            "is_family_friendly",
            "source",
            "source_url",
            "needs_review",
            "notes",
        ]


class MapScreeningSerializer(serializers.ModelSerializer):
    """A screening as shown inside a map pin (venue is implied by the pin)."""

    match = MatchSerializer(read_only=True)
    is_free = serializers.BooleanField(read_only=True)
    is_family_friendly = serializers.BooleanField(read_only=True)

    class Meta:
        model = Screening
        fields = [
            "id",
            "match",
            "starts_at",
            "cost_type",
            "registration_required",
            "entry_guaranteed",
            "price_note",
            "is_free",
            "is_family_friendly",
        ]
