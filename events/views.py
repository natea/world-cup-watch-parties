"""
The three projections of the Screening spine, plus small support endpoints.

All three read endpoints route their query params through the same
`apply_screening_filters`, so an identical filter set produces consistent
results across schedule, map, and team views.
"""
from __future__ import annotations

from collections import OrderedDict
from zoneinfo import ZoneInfo

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from rest_framework.response import Response
from rest_framework.views import APIView

from . import places
from .filters import apply_screening_filters, base_screening_queryset
from .serializers import fallback_image_url
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
                "venue": VenueSerializer(v, context={"request": request}).data,
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
                "venue": VenueSerializer(venue, context={"request": request}).data,
                "screenings": ScreeningSerializer(screenings, many=True).data,
            }
        )


class VenuePhotoView(APIView):
    """Attributed photo proxy: `GET /api/venues/<slug>/photo`.

    Keeps `GOOGLE_PLACES_API_KEY` server-side. On success it 302-redirects to the
    current Places photo URL (we never rehost the bytes). When the key is unset,
    the venue has no place_id, or the lookup fails, it redirects to the venue's
    category fallback illustration — so the client always lands on a usable
    image and no error is surfaced. Attribution is carried in the serializer's
    `image` object (captured at backfill time).
    """

    def get(self, request, slug):
        venue = get_object_or_404(Venue, slug=slug)
        fallback = fallback_image_url(venue.venue_type)

        if not venue.place_id or not places.is_enabled():
            return redirect(fallback)

        photo = places.photo_for_place(venue.place_id)
        if photo is None or not photo.url:
            return redirect(fallback)

        resp = redirect(photo.url)
        # Let browsers/CDN cache the redirect to bound per-photo cost. We cache
        # the redirect, not the bytes — compliant with Places terms.
        resp["Cache-Control"] = f"public, max-age={settings.VENUE_PHOTO_CACHE_SECONDS}"
        return resp


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
