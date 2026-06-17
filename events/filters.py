"""
Shared filter parser over the Screening spine.

Every view (schedule / map / team) routes its query params through
`apply_screening_filters` so the three projections honor an identical,
composable filter set — the "one model, three projections" contract from the
PRD. Each query param maps onto a `ScreeningQuerySet` method.
"""
from __future__ import annotations

from django.conf import settings

from .models import Screening, Team


def _truthy(value: str | None) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on"}


def base_screening_queryset():
    """Screenings with everything the serializers touch fetched up front.

    select_related covers the to-one hops (venue, match, both teams);
    prefetch_related covers the venue's reverse affiliations (+ their team),
    which VenueSerializer embeds — without it, serializing a list of screenings
    is an N+1 (one affiliations query per screening)."""
    return Screening.objects.select_related(
        "venue", "match", "match__home_team", "match__away_team"
    ).prefetch_related("venue__affiliations", "venue__affiliations__team")


def apply_screening_filters(qs, params):
    """Apply the shared, composable filters to a ScreeningQuerySet.

    Recognized params:
      team, team_mode (playing|hub), cost (free|paid),
      environment (indoor|outdoor), venue_type (csv), region, exclude_bars,
      family_friendly, day (YYYY-MM-DD), upcoming.
    """
    # --- team (two senses) ---
    team_code = params.get("team")
    if team_code:
        team = Team.objects.filter(fifa_code__iexact=team_code).first()
        if team is None:
            return qs.none()
        if params.get("team_mode") == "hub":
            qs = qs.at_supporter_hub(team=team)
        else:
            qs = qs.for_team(team)

    # --- cost ---
    cost = params.get("cost")
    if cost == "free":
        qs = qs.free()
    elif cost == "paid":
        qs = qs.paid()

    # --- environment ---
    environment = params.get("environment")
    if environment == "indoor":
        qs = qs.indoor()
    elif environment == "outdoor":
        qs = qs.outdoor()

    # --- venue type (csv) ---
    venue_types = params.get("venue_type")
    if venue_types:
        types = [t.strip() for t in venue_types.split(",") if t.strip()]
        if types:
            qs = qs.venue_type(*types)

    # --- region ---
    region = params.get("region")
    if region:
        qs = qs.filter(venue__region=region)

    # --- exclude bars (the family-friendly UI's second lever) ---
    if _truthy(params.get("exclude_bars")):
        qs = qs.exclude_bars()

    # --- day / upcoming ---
    day = params.get("day")
    if day:
        qs = qs.for_day(day)
    if _truthy(params.get("upcoming")):
        qs = qs.upcoming()

    # --- family-friendly (time-dependent predicate) ---
    if _truthy(params.get("family_friendly")):
        if settings.USING_POSTGRES:
            qs = qs.family_friendly()
        else:
            # SQLite can't reliably compare starts_at__time to a TimeField
            # column in the Case/When; fall back to the per-row Python
            # predicate (the canonical source of truth) and filter by id.
            allowed = [s.id for s in qs.select_related("venue") if s.is_family_friendly]
            qs = qs.filter(id__in=allowed)

    return qs.distinct()
