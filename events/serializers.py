"""DRF serializers shaping the three view responses.

Match serialization always emits a TBD-safe label and resolved-or-placeholder
team info, so unresolved knockout fixtures render without special-casing in the
client.
"""
from __future__ import annotations

from rest_framework import serializers

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


class VenueSerializer(serializers.ModelSerializer):
    affiliations = AffiliationSerializer(many=True, read_only=True)

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
            "source",
            "source_url",
            "needs_review",
            "notes",
            "updated_at",
        ]


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
