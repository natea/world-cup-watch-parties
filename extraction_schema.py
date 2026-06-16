"""
Import / extraction contract.

This Pydantic schema is the single source of truth for the JSON that gets
loaded into the database. It does double duty:

  1. As the *extraction* contract handed to an LLM (its JSON schema becomes the
     tool definition), so the model is forced to emit exactly these shapes.
  2. As the *validation* layer in the import management command, so nothing
     hand-edited or model-generated reaches the DB unvalidated.

Records reference each other by stable natural keys:
  Team    -> fifa_code        ("FRA")
  Match   -> fifa_match_number (int)
  Venue   -> slug             ("the-haven")
This lets the importer be idempotent (update_or_create on the natural key).
"""
from __future__ import annotations

from datetime import datetime, date, time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# --- enums kept in lockstep with models.py ---
class Stage(str, Enum):
    group = "group"; r32 = "r32"; r16 = "r16"; qf = "qf"; sf = "sf"; third = "third"; final = "final"


class VenueType(str, Enum):
    bar = "bar"; brewery = "brewery"; restaurant = "restaurant"; plaza = "plaza"
    park = "park"; community = "community"; hotel = "hotel"; entertainment = "entertainment"
    market = "market"; waterfront = "waterfront"; university = "university"; stadium = "stadium"


class Environment(str, Enum):
    indoor = "indoor"; outdoor = "outdoor"; mixed = "mixed"


class Region(str, Enum):
    greater_boston = "greater_boston"; cambridge_somerville = "cambridge_somerville"
    north_shore = "north_shore"; south_shore = "south_shore"; metrowest = "metrowest"
    foxborough = "foxborough"; worcester = "worcester"; other = "other"


class AffiliationType(str, Enum):
    national_hub = "national_hub"; club_home = "club_home"


class CostType(str, Enum):
    free_open = "free_open"; free_registration = "free_registration"
    free_lottery = "free_lottery"; free_minimum = "free_minimum"; ticketed = "ticketed"


class PolicyType(str, Enum):
    all_matches = "all_matches"; by_team = "by_team"; specific = "specific"


class TeamIn(BaseModel):
    name: str
    fifa_code: str = Field(min_length=2, max_length=3)
    flag_emoji: str = ""
    fifa_rank: Optional[int] = None
    group: str = ""
    confederation: str = ""


class MatchIn(BaseModel):
    fifa_match_number: int
    stage: Stage
    group: str = ""
    kickoff: datetime
    host_city: str = ""
    host_stadium: str = ""
    home_team_code: Optional[str] = None   # FK by fifa_code; null for unresolved knockouts
    away_team_code: Optional[str] = None
    home_placeholder: str = ""
    away_placeholder: str = ""
    bracket_slot: str = ""


class AffiliationIn(BaseModel):
    affiliation_type: AffiliationType
    team_code: Optional[str] = None        # for national_hub
    club: str = ""                         # for club_home
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    note: str = ""

    @model_validator(mode="after")
    def _check_target(self):
        if self.affiliation_type == AffiliationType.national_hub and not self.team_code:
            raise ValueError("national_hub affiliation requires team_code")
        if self.affiliation_type == AffiliationType.club_home and not self.club:
            raise ValueError("club_home affiliation requires club")
        return self


class PolicyIn(BaseModel):
    policy_type: PolicyType
    team_codes: list[str] = Field(default_factory=list)        # for by_team
    match_numbers: list[int] = Field(default_factory=list)     # for specific
    default_cost_type: CostType = CostType.free_open


class VenueIn(BaseModel):
    name: str
    slug: str
    venue_type: VenueType
    environment: Environment = Environment.indoor
    address: str = ""
    city: str
    region: Region = Region.greater_boston
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    serves_alcohol: bool = True
    default_min_age: Optional[int] = None      # None = all ages
    evening_min_age: Optional[int] = None
    evening_cutoff: Optional[time] = None

    capacity: Optional[int] = None
    has_food: bool = True
    website: str = ""

    source: str = ""
    source_url: str = ""
    needs_review: bool = False
    notes: str = ""

    affiliations: list[AffiliationIn] = Field(default_factory=list)
    policies: list[PolicyIn] = Field(default_factory=list)


class ScreeningIn(BaseModel):
    venue_slug: str                # FK by slug
    match_number: int              # FK by fifa_match_number
    starts_at: datetime
    ends_at: Optional[datetime] = None
    cost_type: CostType = CostType.free_open
    registration_required: bool = False
    entry_guaranteed: bool = True
    price_note: str = ""
    age_override: Optional[int] = None
    source: str = ""
    source_url: str = ""
    needs_review: bool = False
    notes: str = ""


class ImportBundle(BaseModel):
    """Top-level payload. Load reference data (teams, matches) from an
    authoritative source; venues/screenings/policies may be LLM-extracted."""
    teams: list[TeamIn] = Field(default_factory=list)
    matches: list[MatchIn] = Field(default_factory=list)
    venues: list[VenueIn] = Field(default_factory=list)
    screenings: list[ScreeningIn] = Field(default_factory=list)
