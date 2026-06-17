import type { Match } from "./types";

// Times are stored UTC; render in Massachusetts local time.
const TZ = "America/New_York";

// Expand a FIFA bracket placeholder code into plain English.
//   "1E"      → "Winner Group E"
//   "2A"      → "Runner-up Group A"
//   "3ABCDF"  → "3rd place (A/B/C/D/F)"  (best-third-placed team, group TBD)
//   "W73"/"L73" → "Winner/Loser of Match 73"
export function teamPlaceholder(code: string): string {
  if (!code) return "TBD";
  const group = code.match(/^([123])([A-L]+)$/);
  if (group) {
    const [, pos, letters] = group;
    if (pos === "1") return `Winner Group ${letters}`;
    if (pos === "2") return `Runner-up Group ${letters}`;
    return letters.length === 1
      ? `3rd place Group ${letters}`
      : `3rd place (${letters.split("").join("/")})`;
  }
  const wl = code.match(/^([WL])(\d+)$/i);
  if (wl) return `${wl[1].toUpperCase() === "W" ? "Winner" : "Loser"} of Match ${wl[2]}`;
  return code;
}

// Display label for a match: resolved teams when known, otherwise the
// humanized placeholders (so the schedule reads "Winner Group E vs 3rd place
// (A/B/C/D/F)" instead of the cryptic "1E vs 3ABCDF").
export function matchDisplayLabel(match: Match): string {
  if (match.is_resolved) return match.label;
  return `${teamPlaceholder(match.home_placeholder)} vs ${teamPlaceholder(match.away_placeholder)}`;
}

// Local (MA) calendar day key, YYYY-MM-DD, for grouping screenings by day.
export function localDayKey(iso: string): string {
  return new Date(iso).toLocaleDateString("en-CA", { timeZone: TZ });
}

export function localTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US", {
    timeZone: TZ,
    hour: "numeric",
    minute: "2-digit",
  });
}

export function localDateLong(isoDate: string): string {
  // isoDate is a YYYY-MM-DD (already a local calendar day from the API).
  const [y, m, d] = isoDate.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-US", {
    timeZone: "UTC",
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}

// Short local date for contexts not already grouped by day (map popups, team view).
export function localDateShort(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    timeZone: TZ,
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

// A Google Maps "listing" link for a venue, by name + address.
export function googleMapsUrl(parts: {
  name: string;
  address?: string;
  city?: string;
}): string {
  const query = [parts.name, parts.address, parts.city].filter(Boolean).join(", ");
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}

const COST_LABELS: Record<string, string> = {
  free_open: "Free",
  free_registration: "Free · registration",
  free_lottery: "Free · lottery (entry not guaranteed)",
  free_minimum: "Free · purchase minimum",
  ticketed: "Ticketed",
};

export function costLabel(cost: string): string {
  return COST_LABELS[cost] ?? cost;
}
