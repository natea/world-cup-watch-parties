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
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from . import places
from .filters import apply_screening_filters, base_screening_queryset
from .geocoding import resolve as resolve_location
from .search import DEFAULT_LIMIT, build_suggestions
from .serializers import fallback_image_url
from .models import (
    CostType,
    Match,
    Region,
    RefreshState,
    Screening,
    Stage,
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
        refreshed_at = RefreshState.get().fixtures_refreshed_at
        return Response(
            {
                "venue_types": [{"value": v, "label": l} for v, l in VenueType.choices],
                "regions": [{"value": v, "label": l} for v, l in Region.choices],
                "cost_types": [{"value": v, "label": l} for v, l in CostType.choices],
                "environments": ["indoor", "outdoor"],
                "team_modes": ["playing", "hub"],
                "fixtures_refreshed_at": refreshed_at.isoformat() if refreshed_at else None,
            }
        )


# Mirror of refreshfixtures.STALENESS_THRESHOLD: how long data may go un-refreshed
# before we consider it stale (the cron runs every 6h, so 24h means ~4 misses).
STALENESS_HOURS = 24


class FixturesHealthView(APIView):
    """At-a-glance health of the FIFA fixture refresh, so you can confirm the cron
    is working without reading Render logs.

    Reports the last refresh time + age, a staleness flag, and resolved-vs-TBD
    fixture counts (overall and by stage). During the group stage every knockout
    fixture is a TBD placeholder, so `tbd > 0` with `resolved` ~= the group games
    is the expected, healthy state — not a failure.
    """

    def get(self, request):
        now = timezone.now()
        refreshed_at = RefreshState.get().fixtures_refreshed_at

        age_seconds = (now - refreshed_at).total_seconds() if refreshed_at else None
        stale = refreshed_at is None or age_seconds > STALENESS_HOURS * 3600

        # A match is "resolved" once both teams are known (knockout opponents are
        # TBD placeholders until group results lock in).
        resolved_q = Q(home_team__isnull=False) & Q(away_team__isnull=False)
        total = Match.objects.count()
        resolved = Match.objects.filter(resolved_q).count()

        # Per-stage breakdown, ordered by the canonical stage progression.
        stage_order = [s.value for s in Stage]
        per_stage = (
            Match.objects.values("stage")
            .annotate(total=Count("id"), resolved=Count("id", filter=resolved_q))
            .order_by()
        )
        by_stage_map = {row["stage"]: row for row in per_stage}
        by_stage = [
            {
                "stage": s,
                "total": by_stage_map[s]["total"],
                "resolved": by_stage_map[s]["resolved"],
                "tbd": by_stage_map[s]["total"] - by_stage_map[s]["resolved"],
            }
            for s in stage_order
            if s in by_stage_map
        ]

        # A few upcoming TBD knockout fixtures, to make the "awaiting advancement"
        # state concrete.
        tbd_samples = [
            {
                "kickoff": m.kickoff.isoformat(),
                "stage": m.stage,
                "matchup": f"{m.home_placeholder or 'TBD'} vs {m.away_placeholder or 'TBD'}",
            }
            for m in Match.objects.filter(~resolved_q).order_by("kickoff")[:6]
        ]

        return Response(
            {
                "fixtures_refreshed_at": refreshed_at.isoformat() if refreshed_at else None,
                "age_seconds": int(age_seconds) if age_seconds is not None else None,
                "age_human": _humanize_age(age_seconds),
                "stale": stale,
                "staleness_threshold_hours": STALENESS_HOURS,
                "matches": {
                    "total": total,
                    "resolved": resolved,
                    "tbd": total - resolved,
                },
                "by_stage": by_stage,
                "generated_screenings": Screening.objects.filter(is_generated=True).count(),
                "tbd_samples": tbd_samples,
            }
        )


def _humanize_age(seconds: float | None) -> str | None:
    """Compact 'last refresh' age, e.g. '2h ago' / 'never'."""
    if seconds is None:
        return "never"
    mins = int(seconds // 60)
    if mins < 1:
        return "just now"
    if mins < 60:
        return f"{mins} min ago"
    hours = mins // 60
    if hours < 24:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"
