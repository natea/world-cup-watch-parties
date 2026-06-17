"""
The three projections of the Screening spine, plus small support endpoints.

All three read endpoints route their query params through the same
`apply_screening_filters`, so an identical filter set produces consistent
results across schedule, map, and team views.
"""
from __future__ import annotations

from collections import OrderedDict
from zoneinfo import ZoneInfo

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import apply_screening_filters, base_screening_queryset
from .geocoding import resolve as resolve_location
from .search import DEFAULT_LIMIT, build_suggestions
from .models import (
    CostType,
    Region,
    Screening,
    Team,
    Venue,
    VenueType,
    _haversine_km,
)
from .serializers import (
    MapScreeningSerializer,
    ScreeningSerializer,
    TeamSerializer,
    VenueSerializer,
)

# Massachusetts local time, used to group the schedule by local calendar day.
EVENT_TZ = ZoneInfo("America/New_York")


class ScheduleView(APIView):
    """Screenings ordered by kickoff, grouped by local (MA) calendar day."""

    def get(self, request):
        qs = apply_screening_filters(base_screening_queryset(), request.query_params)
        qs = qs.order_by("starts_at")

        groups: "OrderedDict[str, list]" = OrderedDict()
        for screening in qs:
            local_day = screening.starts_at.astimezone(EVENT_TZ).date().isoformat()
            groups.setdefault(local_day, []).append(screening)

        days = [
            {
                "date": day,
                "screenings": ScreeningSerializer(items, many=True).data,
            }
            for day, items in groups.items()
        ]
        return Response({"timezone": str(EVENT_TZ), "days": days})


class MapView(APIView):
    """Venues that have >=1 screening passing the filters, each with its
    relevant screenings. Optional `lat`/`lng` anchor sorts by distance."""

    def get(self, request):
        qs = apply_screening_filters(base_screening_queryset(), request.query_params)
        qs = qs.filter(venue__latitude__isnull=False, venue__longitude__isnull=False)

        anchor = self._parse_anchor(request.query_params)
        by_venue: "OrderedDict[int, dict]" = OrderedDict()
        for screening in qs.order_by("starts_at"):
            v = screening.venue
            entry = by_venue.get(v.id)
            if entry is None:
                entry = {"venue": v, "screenings": []}
                by_venue[v.id] = entry
            entry["screenings"].append(screening)

        venues = []
        for entry in by_venue.values():
            v = entry["venue"]
            item = {
                "venue": VenueSerializer(v).data,
                "screenings": MapScreeningSerializer(entry["screenings"], many=True).data,
            }
            if anchor is not None and v.latitude is not None and v.longitude is not None:
                item["distance_km"] = round(
                    _haversine_km(anchor[0], anchor[1], float(v.latitude), float(v.longitude)),
                    2,
                )
            venues.append(item)

        if anchor is not None:
            venues.sort(key=lambda x: x.get("distance_km", float("inf")))

        return Response({"anchor": anchor, "venues": venues})

    @staticmethod
    def _parse_anchor(params):
        lat, lng = params.get("lat"), params.get("lng")
        if lat is None or lng is None:
            return None
        try:
            return (float(lat), float(lng))
        except (TypeError, ValueError):
            return None


class ScreeningsView(APIView):
    """Flat screenings list — drives the team ("alliance") view. Accepts the
    `team` + `team_mode` params plus the shared filters."""

    def get(self, request):
        qs = apply_screening_filters(base_screening_queryset(), request.query_params)
        qs = qs.order_by("starts_at")
        return Response({"screenings": ScreeningSerializer(qs, many=True).data})


class VenueDetailView(APIView):
    """One venue with its full profile and every screening it hosts."""

    def get(self, request, slug):
        venue = get_object_or_404(Venue, slug=slug)
        screenings = (
            Screening.objects.filter(venue=venue)
            .select_related("match", "match__home_team", "match__away_team")
            .order_by("starts_at")
        )
        return Response(
            {
                "venue": VenueSerializer(venue).data,
                "screenings": ScreeningSerializer(screenings, many=True).data,
            }
        )


class SearchView(APIView):
    """Typeahead search across venues and teams: GET /api/search/?q=<query>.

    Returns ranked, typed suggestions; each carries a `target` telling the
    client how to navigate (open a venue's detail, or focus a team)."""

    def get(self, request):
        q = request.query_params.get("q", "")
        try:
            limit = int(request.query_params.get("limit", DEFAULT_LIMIT))
        except (TypeError, ValueError):
            limit = DEFAULT_LIMIT
        return Response({"suggestions": build_suggestions(q, limit=limit)})


class GeocodeView(APIView):
    """Resolve a ZIP or address to coordinates for the map's distance anchor:
    GET /api/geocode/?zip=02139  or  ?address=<street address>.

    Returns {lat, lng, label, precision} on success, or {result: null} when the
    location can't be resolved (so the client falls back to a ZIP or no anchor).
    The user's coordinates are used only to answer this request — never stored."""

    def get(self, request):
        result = resolve_location(
            zip_code=request.query_params.get("zip"),
            address=request.query_params.get("address"),
        )
        return Response({"result": result})


class TeamListView(APIView):
    def get(self, request):
        teams = Team.objects.all()
        return Response({"teams": TeamSerializer(teams, many=True).data})


class MetaView(APIView):
    """Filter vocabulary for the client (enum labels for the UI controls)."""

    def get(self, request):
        return Response(
            {
                "venue_types": [{"value": v, "label": l} for v, l in VenueType.choices],
                "regions": [{"value": v, "label": l} for v, l in Region.choices],
                "cost_types": [{"value": v, "label": l} for v, l in CostType.choices],
                "environments": ["indoor", "outdoor"],
                "team_modes": ["playing", "hub"],
            }
        )
