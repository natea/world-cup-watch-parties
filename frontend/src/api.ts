import type {
  Filters,
  MapVenue,
  Meta,
  ScheduleDay,
  Screening,
  Suggestion,
  Team,
  Venue,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api";

/** Serialize the shared filter set into query params understood by every endpoint. */
export function filtersToParams(filters: Filters): URLSearchParams {
  const p = new URLSearchParams();
  if (filters.team) {
    p.set("team", filters.team);
    p.set("team_mode", filters.team_mode ?? "playing");
  }
  if (filters.cost) p.set("cost", filters.cost);
  if (filters.environment) p.set("environment", filters.environment);
  if (filters.venue_type) p.set("venue_type", filters.venue_type);
  if (filters.region) p.set("region", filters.region);
  if (filters.exclude_bars) p.set("exclude_bars", "true");
  if (filters.family_friendly) p.set("family_friendly", "true");
  return p;
}

async function getJSON<T>(path: string, params?: URLSearchParams): Promise<T> {
  const qs = params && [...params.keys()].length ? `?${params.toString()}` : "";
  const res = await fetch(`${BASE}${path}${qs}`);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  schedule: (f: Filters) =>
    getJSON<{ timezone: string; days: ScheduleDay[] }>("/schedule/", filtersToParams(f)),

  map: (f: Filters, anchor?: { lat: number; lng: number }) => {
    const p = filtersToParams(f);
    if (anchor) {
      p.set("lat", String(anchor.lat));
      p.set("lng", String(anchor.lng));
    }
    return getJSON<{ anchor: [number, number] | null; venues: MapVenue[] }>("/map/", p);
  },

  screenings: (f: Filters) =>
    getJSON<{ screenings: Screening[] }>("/screenings/", filtersToParams(f)),

  venue: (slug: string) =>
    getJSON<{ venue: Venue; screenings: Screening[] }>(`/venues/${encodeURIComponent(slug)}/`),

  // Typeahead. Accepts an AbortSignal so the caller can cancel stale requests.
  search: async (q: string, signal?: AbortSignal): Promise<Suggestion[]> => {
    const res = await fetch(`${BASE}/search/?q=${encodeURIComponent(q)}`, { signal });
    if (!res.ok) throw new Error(`/search/ -> ${res.status}`);
    const data = (await res.json()) as { suggestions: Suggestion[] };
    return data.suggestions;
  },

  teams: () => getJSON<{ teams: Team[] }>("/teams/"),

  meta: () => getJSON<Meta>("/meta/"),
};
