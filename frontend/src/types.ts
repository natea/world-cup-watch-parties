// Mirror of the DRF serializer shapes.

export interface Team {
  name: string;
  fifa_code: string;
  flag_emoji: string;
  fifa_rank: number | null;
  group: string;
  confederation: string;
}

export interface Match {
  fifa_match_number: number | null;
  stage: string;
  group: string;
  kickoff: string; // ISO UTC
  host_city: string;
  host_stadium: string;
  home_team: Team | null;
  away_team: Team | null;
  home_placeholder: string;
  away_placeholder: string;
  bracket_slot: string;
  label: string;
  is_resolved: boolean;
}

export interface Affiliation {
  affiliation_type: "national_hub" | "club_home";
  team: Team | null;
  club: string;
  note: string;
}

export interface VenueImage {
  url: string;
  attribution: string | null; // present for licensed photos (google_places, wikimedia)
  source: "google_places" | "wikimedia" | "fallback" | string;
}

export interface Venue {
  name: string;
  slug: string;
  venue_type: string;
  environment: "indoor" | "outdoor" | "mixed";
  address: string;
  city: string;
  region: string;
  latitude: number | null;
  longitude: number | null;
  serves_alcohol: boolean;
  capacity: number | null;
  has_food: boolean;
  website: string;
  affiliations: Affiliation[];
  image: VenueImage;
  source: string;
  source_url: string;
  needs_review: boolean;
  notes: string;
  updated_at: string;
}

export interface Screening {
  id: number;
  venue: Venue;
  match: Match;
  starts_at: string; // ISO UTC
  ends_at: string | null;
  cost_type: string;
  registration_required: boolean;
  entry_guaranteed: boolean;
  price_note: string;
  is_generated: boolean;
  is_free: boolean;
  is_family_friendly: boolean;
  source: string;
  source_url: string;
  needs_review: boolean;
  notes: string;
}

export interface ScheduleDay {
  date: string;
  screenings: Screening[];
}

export interface MapVenue {
  venue: Venue;
  screenings: Omit<Screening, "venue">[];
  distance_km?: number;
}

export interface Meta {
  venue_types: { value: string; label: string }[];
  regions: { value: string; label: string }[];
  cost_types: { value: string; label: string }[];
  environments: string[];
  team_modes: string[];
  fixtures_refreshed_at: string | null; // ISO timestamp of last successful refresh, or null
}

// A typeahead search suggestion. `target` says how selecting it navigates.
export type SuggestionTarget =
  | { kind: "venue"; slug: string }
  | { kind: "team"; code: string };

export interface Suggestion {
  type: "venue" | "team";
  label: string;
  sublabel: string;
  target: SuggestionTarget;
}

// A resolved map anchor: where "near me" distances are measured from.
export interface Anchor {
  lat: number;
  lng: number;
  label: string;
  precision: "address" | "zip" | "device";
}

// The shared, composable filter set — one object honored by all three views.
export interface Filters {
  team?: string;
  team_mode?: "playing" | "hub";
  cost?: "free" | "paid";
  environment?: "indoor" | "outdoor";
  venue_type?: string;
  region?: string;
  exclude_bars?: boolean;
  family_friendly?: boolean;
  // Past games are hidden by default; this opts them back in.
  show_past?: boolean;
}
