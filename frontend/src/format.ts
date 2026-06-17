// Times are stored UTC; render in Massachusetts local time.
const TZ = "America/New_York";

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
