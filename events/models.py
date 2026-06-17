"""
Data model for a World Cup 2026 watch-party finder.

Design spine
------------
The atomic, attendable unit is a **Screening** = (Venue, Match, time, access).
Everything the frontend shows is a projection of Screening:

    schedule view  -> Screening ordered by match.kickoff, grouped by day
    map view       -> Venues that have >=1 Screening passing the active filter
    "by team" view -> Screening.objects.for_team(t)  (a venue showing the match)
                      OR Screening.objects.at_supporter_hub(t) (the team's bar)

The two senses of "team" are kept separate on purpose: a match *featuring* a
team (derived from Match) vs a venue *affiliated with* a team
(VenueAffiliation). Users want to be able to mean either.

Three filters that look like booleans but aren't, and are modeled as
underlying facts + computed predicates instead:

  * family-friendly : depends on whether minors are allowed AT THE SCREENING'S
                      TIME (some venues flip to 21+ in the evening), so it is a
                      predicate over (Venue, time), not a Venue flag.
  * free / paid     : Fan Fest is "free + registration + lottery + entry not
                      guaranteed" -- a distinct state from free-open and from
                      ticketed, so cost is an enum, not a bool.
  * indoor/outdoor  : several venues are both -> {indoor, outdoor, mixed}.
"""
from __future__ import annotations

import math
from datetime import time as dt_time

from django.db import models
from django.db.models import Q, F, Case, When, IntegerField
from django.utils import timezone
from django.utils.text import slugify

MINOR_AGE = 18  # under this = a minor, for the family-friendly predicate


# ---------------------------------------------------------------------------
# Reference data: teams and the canonical FIFA match schedule
# ---------------------------------------------------------------------------
class Confederation(models.TextChoices):
    AFC = "AFC", "AFC (Asia)"
    CAF = "CAF", "CAF (Africa)"
    CONCACAF = "CONCACAF", "CONCACAF (North/Central America)"
    CONMEBOL = "CONMEBOL", "CONMEBOL (South America)"
    OFC = "OFC", "OFC (Oceania)"
    UEFA = "UEFA", "UEFA (Europe)"


class Team(models.Model):
    name = models.CharField(max_length=80, unique=True)
    fifa_code = models.CharField(max_length=3, unique=True, help_text="e.g. FRA, SCO")
    flag_emoji = models.CharField(max_length=8, blank=True)
    fifa_rank = models.PositiveIntegerField(null=True, blank=True)
    group = models.CharField(max_length=1, blank=True, help_text="Group letter, e.g. C")
    confederation = models.CharField(max_length=10, choices=Confederation.choices, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.flag_emoji} {self.name}".strip()


class Stage(models.TextChoices):
    GROUP = "group", "Group stage"
    R32 = "r32", "Round of 32"
    R16 = "r16", "Round of 16"
    QF = "qf", "Quarterfinal"
    SF = "sf", "Semifinal"
    THIRD = "third", "Third place"
    FINAL = "final", "Final"


class MatchQuerySet(models.QuerySet):
    def involving(self, team: "Team") -> "MatchQuerySet":
        """Resolved matches that feature `team`. Knockout matches only match
        once their teams are filled in (see bracket_slot / re-materialize)."""
        return self.filter(Q(home_team=team) | Q(away_team=team))

    def at_gillette(self) -> "MatchQuerySet":
        return self.filter(host_stadium__icontains="gillette")


class Match(models.Model):
    """The canonical FIFA fixture. This is reference data and should come from
    an authoritative source, NOT be extracted from prose (see import notes)."""
    fifa_match_number = models.PositiveIntegerField(
        unique=True, null=True, blank=True,
        help_text="Canonical FIFA fixture number; the stable natural key.",
    )
    stage = models.CharField(max_length=8, choices=Stage.choices)
    group = models.CharField(max_length=1, blank=True)
    kickoff = models.DateTimeField(help_text="Store timezone-aware (UTC).")
    host_city = models.CharField(max_length=80, blank=True)
    host_stadium = models.CharField(max_length=120, blank=True)

    # Nullable because knockout opponents are TBD during the group stage.
    home_team = models.ForeignKey(
        Team, null=True, blank=True, on_delete=models.PROTECT, related_name="home_matches")
    away_team = models.ForeignKey(
        Team, null=True, blank=True, on_delete=models.PROTECT, related_name="away_matches")
    home_placeholder = models.CharField(max_length=60, blank=True, help_text='e.g. "Winner Group C"')
    away_placeholder = models.CharField(max_length=60, blank=True)
    bracket_slot = models.CharField(
        max_length=20, blank=True,
        help_text='Stable knockout slot id, e.g. "R32-3", so resolution can be re-applied.',
    )

    objects = MatchQuerySet.as_manager()

    class Meta:
        ordering = ["kickoff"]

    @property
    def is_resolved(self) -> bool:
        return self.home_team_id is not None and self.away_team_id is not None

    @property
    def label(self) -> str:
        home = self.home_team.name if self.home_team_id else (self.home_placeholder or "TBD")
        away = self.away_team.name if self.away_team_id else (self.away_placeholder or "TBD")
        return f"{home} vs {away}"

    def involves(self, team: "Team") -> bool:
        return team.id in (self.home_team_id, self.away_team_id)

    def __str__(self) -> str:
        return f"{self.label} ({self.kickoff:%b %d})"


# ---------------------------------------------------------------------------
# Venues
# ---------------------------------------------------------------------------
class Region(models.TextChoices):
    GREATER_BOSTON = "greater_boston", "Greater Boston"
    CAMBRIDGE_SOMERVILLE = "cambridge_somerville", "Cambridge / Somerville"
    NORTH_SHORE = "north_shore", "North Shore"
    SOUTH_SHORE = "south_shore", "South Shore"
    METROWEST = "metrowest", "MetroWest"
    FOXBOROUGH = "foxborough", "Foxborough / Gillette"
    WORCESTER = "worcester", "Worcester / Central"
    OTHER = "other", "Other"


class VenueType(models.TextChoices):
    BAR = "bar", "Bar / pub"
    BREWERY = "brewery", "Brewery / taproom"
    RESTAURANT = "restaurant", "Restaurant"
    PLAZA = "plaza", "Public plaza / fan festival"
    PARK = "park", "Park / outdoor space"
    COMMUNITY = "community", "Municipal / community space"
    HOTEL = "hotel", "Hotel"
    ENTERTAINMENT = "entertainment", "Entertainment (bowling, arcade)"
    MARKET = "market", "Food hall / market"
    WATERFRONT = "waterfront", "Waterfront / boat"
    UNIVERSITY = "university", "University"
    STADIUM = "stadium", "Stadium"


class Environment(models.TextChoices):
    INDOOR = "indoor", "Indoor"
    OUTDOOR = "outdoor", "Outdoor"
    MIXED = "mixed", "Indoor & outdoor"


class VenueQuerySet(models.QuerySet):
    def with_coordinates(self) -> "VenueQuerySet":
        return self.exclude(latitude__isnull=True).exclude(longitude__isnull=True)

    def exclude_bars(self) -> "VenueQuerySet":
        """The 'exclude bars' lever from the family-friendly UI. NOTE this is a
        SEPARATE concept from whether minors are allowed -- see Screening."""
        return self.exclude(venue_type__in=[VenueType.BAR, VenueType.BREWERY])

    def in_region(self, region: str) -> "VenueQuerySet":
        return self.filter(region=region)

    def nearby(self, lat: float, lng: float, radius_km: float = 8.0) -> list["Venue"]:
        """Bounding-box prefilter in SQL, exact Haversine in Python. Fine for a
        ~150-venue dataset; swap for PostGIS/GeoDjango if this grows."""
        dlat = radius_km / 111.0
        dlng = radius_km / (111.0 * max(math.cos(math.radians(lat)), 1e-6))
        box = self.with_coordinates().filter(
            latitude__gte=lat - dlat, latitude__lte=lat + dlat,
            longitude__gte=lng - dlng, longitude__lte=lng + dlng,
        )
        out = []
        for v in box:
            d = _haversine_km(lat, lng, float(v.latitude), float(v.longitude))
            if d <= radius_km:
                v.distance_km = round(d, 2)
                out.append(v)
        return sorted(out, key=lambda v: v.distance_km)


class Venue(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    venue_type = models.CharField(max_length=16, choices=VenueType.choices)
    environment = models.CharField(max_length=8, choices=Environment.choices, default=Environment.INDOOR)

    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=80)
    region = models.CharField(max_length=24, choices=Region.choices, default=Region.GREATER_BOSTON)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # --- facts that feed the computed family-friendly predicate ---
    serves_alcohol = models.BooleanField(default=True)
    default_min_age = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Minimum entry age normally. NULL = all ages welcome.",
    )
    evening_min_age = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Min age that applies after `evening_cutoff` (e.g. 21+ after 8pm).",
    )
    evening_cutoff = models.TimeField(
        null=True, blank=True,
        help_text="Local time after which evening_min_age applies.",
    )

    capacity = models.PositiveIntegerField(null=True, blank=True)
    has_food = models.BooleanField(default=True)
    website = models.URLField(blank=True)

    # --- venue imagery (rights-safe) ---
    # We persist only the Google place_id (allowed long-term) plus image-source
    # metadata; we NEVER store photo bytes. The photo is fetched on demand
    # through the attributed backend proxy. When place_id is empty the venue
    # falls back to a category illustration keyed by venue_type.
    place_id = models.CharField(
        max_length=255, blank=True,
        help_text="Google Place ID; resolved once via `resolvevenueplaces`.",
    )
    image_source = models.CharField(
        max_length=32, blank=True,
        help_text='How the image is sourced: "google_places", "wikimedia", or blank = fallback.',
    )
    image_url = models.URLField(
        max_length=500, blank=True,
        help_text=(
            "Stable external image URL for the Wikimedia tier. Google photos stay "
            "proxy-resolved and do NOT use this field."
        ),
    )
    image_attribution = models.CharField(
        max_length=255, blank=True,
        help_text="Required attribution text captured from the image source metadata.",
    )

    # provenance / data-quality
    source = models.CharField(max_length=120, blank=True)
    source_url = models.URLField(blank=True)
    needs_review = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = VenueQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:180]
        super().save(*args, **kwargs)

    def effective_min_age_at(self, when=None):
        """Effective minimum entry age at a given datetime/time (or None)."""
        if when is not None and self.evening_cutoff and self.evening_min_age is not None:
            t = when.timetz() if hasattr(when, "timetz") else when
            t = t.replace(tzinfo=None) if hasattr(t, "tzinfo") and t.tzinfo else t
            if t >= self.evening_cutoff:
                return self.evening_min_age
        return self.default_min_age

    def allows_minors_at(self, when=None) -> bool:
        eff = self.effective_min_age_at(when)
        return eff is None or eff < MINOR_AGE

    def __str__(self) -> str:
        return self.name


# ---------------------------------------------------------------------------
# Affiliation: "this venue is a supporter hub for team X / club Y"
# (the second sense of team; independent of any match)
# ---------------------------------------------------------------------------
class AffiliationType(models.TextChoices):
    NATIONAL_HUB = "national_hub", "National team supporters hub"
    CLUB_HOME = "club_home", "Club home bar"


class VenueAffiliation(models.Model):
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="affiliations")
    affiliation_type = models.CharField(max_length=16, choices=AffiliationType.choices)
    team = models.ForeignKey(
        Team, null=True, blank=True, on_delete=models.CASCADE, related_name="venue_hubs",
        help_text="Set for national_hub.")
    club = models.CharField(max_length=80, blank=True, help_text='Set for club_home, e.g. "Liverpool FC".')
    # Time-bounded because some venues convert just for the tournament
    # (e.g. a Man United pub becoming a Scottish pub for the group stage).
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="affiliation_target_matches_type",
                condition=(
                    (Q(affiliation_type="national_hub") & Q(team__isnull=False))
                    | (Q(affiliation_type="club_home") & ~Q(club=""))
                ),
            ),
        ]

    def __str__(self) -> str:
        target = self.team.name if self.team_id else self.club
        return f"{self.venue.name} ⟶ {target}"


# ---------------------------------------------------------------------------
# Screening: the atomic attendable unit; all three views read from this.
# ---------------------------------------------------------------------------
class CostType(models.TextChoices):
    FREE_OPEN = "free_open", "Free, open entry"
    FREE_REGISTRATION = "free_registration", "Free, registration required"
    FREE_LOTTERY = "free_lottery", "Free, lottery (entry not guaranteed)"
    FREE_MINIMUM = "free_minimum", "Free entry, purchase/table minimum"
    TICKETED = "ticketed", "Ticketed / paid"


class ScreeningQuerySet(models.QuerySet):
    # --- view drivers ---
    def for_day(self, d) -> "ScreeningQuerySet":
        return self.filter(starts_at__date=d)

    def upcoming(self, now=None) -> "ScreeningQuerySet":
        return self.filter(starts_at__gte=now or timezone.now())

    def for_team(self, team: "Team") -> "ScreeningQuerySet":
        """Screenings of a match that FEATURES the team (first sense)."""
        return self.filter(Q(match__home_team=team) | Q(match__away_team=team))

    def at_supporter_hub(self, *, team: "Team" = None, club: str = "") -> "ScreeningQuerySet":
        """Screenings at a venue AFFILIATED with the team/club (second sense)."""
        if team is not None:
            return self.filter(venue__affiliations__team=team)
        return self.filter(venue__affiliations__club__iexact=club)

    # --- filters ---
    def free(self) -> "ScreeningQuerySet":
        return self.exclude(cost_type=CostType.TICKETED)

    def paid(self) -> "ScreeningQuerySet":
        return self.filter(cost_type=CostType.TICKETED)

    def indoor(self):
        return self.filter(venue__environment__in=[Environment.INDOOR, Environment.MIXED])

    def outdoor(self):
        return self.filter(venue__environment__in=[Environment.OUTDOOR, Environment.MIXED])

    def venue_type(self, *types):
        return self.filter(venue__venue_type__in=types)

    def exclude_bars(self):
        return self.exclude(venue__venue_type__in=[VenueType.BAR, VenueType.BREWERY])

    def family_friendly(self) -> "ScreeningQuerySet":
        """Minors allowed at the screening's start time.

        Computed per-row because the effective age can flip in the evening.
        Implemented as a Case/When annotation; verified on PostgreSQL. On
        backends where comparing an extracted time to a TimeField column is
        unsupported, fall back to filtering in Python via
        `Screening.is_family_friendly`."""
        evening_applies = (
            Q(venue__evening_cutoff__isnull=False)
            & Q(venue__evening_min_age__isnull=False)
            & Q(starts_at__time__gte=F("venue__evening_cutoff"))
        )
        qs = self.annotate(
            _eff_min_age=Case(
                When(age_override__isnull=False, then=F("age_override")),
                When(evening_applies, then=F("venue__evening_min_age")),
                default=F("venue__default_min_age"),
                output_field=IntegerField(),
            )
        )
        return qs.filter(Q(_eff_min_age__isnull=True) | Q(_eff_min_age__lt=MINOR_AGE))


class Screening(models.Model):
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="screenings")
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="screenings")
    starts_at = models.DateTimeField(help_text="Often == match.kickoff, but may differ (doors).")
    ends_at = models.DateTimeField(null=True, blank=True)

    cost_type = models.CharField(max_length=20, choices=CostType.choices, default=CostType.FREE_OPEN)
    registration_required = models.BooleanField(default=False)
    entry_guaranteed = models.BooleanField(default=True, help_text="False for capped/lottery sessions.")
    price_note = models.CharField(max_length=120, blank=True, help_text='e.g. "$10", "$80 incl. transit".')

    age_override = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Screening-specific min age; overrides the venue's rule when set.",
    )
    is_generated = models.BooleanField(
        default=False, help_text="True if materialized from a ScreeningPolicy.")

    source = models.CharField(max_length=120, blank=True)
    source_url = models.URLField(blank=True)
    needs_review = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    objects = ScreeningQuerySet.as_manager()

    class Meta:
        ordering = ["starts_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["venue", "match", "starts_at"], name="uniq_screening_natural_key"),
        ]

    @property
    def is_free(self) -> bool:
        return self.cost_type != CostType.TICKETED

    @property
    def is_family_friendly(self) -> bool:
        """Canonical per-screening evaluation (source of truth)."""
        if self.age_override is not None:
            return self.age_override < MINOR_AGE
        return self.venue.allows_minors_at(self.starts_at)

    def __str__(self) -> str:
        return f"{self.venue.name}: {self.match.label} @ {self.starts_at:%b %d %H:%M}"


# ---------------------------------------------------------------------------
# ScreeningPolicy: rule for venues that show many/all matches. Materializes
# into concrete Screening rows so every view stays uniform.
# ---------------------------------------------------------------------------
class PolicyType(models.TextChoices):
    ALL_MATCHES = "all_matches", "Shows every match"
    BY_TEAM = "by_team", "Shows matches involving selected teams"
    SPECIFIC = "specific", "Shows a specific set of matches"


class ScreeningPolicy(models.Model):
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="policies")
    policy_type = models.CharField(max_length=16, choices=PolicyType.choices)
    teams = models.ManyToManyField(Team, blank=True, related_name="screening_policies")
    matches = models.ManyToManyField(Match, blank=True, related_name="screening_policies")

    # defaults stamped onto generated screenings
    default_cost_type = models.CharField(max_length=20, choices=CostType.choices, default=CostType.FREE_OPEN)
    source = models.CharField(max_length=120, blank=True)

    def matching_matches(self) -> "MatchQuerySet":
        if self.policy_type == PolicyType.ALL_MATCHES:
            return Match.objects.all()
        if self.policy_type == PolicyType.BY_TEAM:
            teams = list(self.teams.all())
            return Match.objects.filter(
                Q(home_team__in=teams) | Q(away_team__in=teams)).distinct()
        return self.matches.all()

    def materialize(self) -> int:
        """Expand the rule into Screening rows (idempotent). Re-run after the
        knockout bracket resolves so BY_TEAM policies pick up new fixtures."""
        count = 0
        for match in self.matching_matches():
            _, created = Screening.objects.update_or_create(
                venue=self.venue, match=match, starts_at=match.kickoff,
                defaults={
                    "cost_type": self.default_cost_type,
                    "is_generated": True,
                    "source": self.source or "policy",
                },
            )
            count += int(created)
        return count

    def __str__(self) -> str:
        return f"{self.venue.name}: {self.get_policy_type_display()}"


# ---------------------------------------------------------------------------
def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
