import { useCallback, useEffect, useState } from "react";
import type { Anchor, Filters } from "./types";

// A single shared, URL-synced filter set. Every view reads the same object, so
// switching views preserves filters and keeps results consistent. The URL is
// the source of truth, so a filtered view is shareable/bookmarkable.

const BOOL_KEYS: (keyof Filters)[] = ["exclude_bars", "family_friendly", "show_past"];

// Keys tracked separately from the filter set (view, open venue, map anchor).
const NON_FILTER_KEYS = new Set(["view", "venue", "alat", "alng", "aprec", "alabel"]);

function parse(search: string): Filters {
  const p = new URLSearchParams(search);
  const f: Filters = {};
  for (const [k, v] of p.entries()) {
    if (NON_FILTER_KEYS.has(k)) continue;
    if (BOOL_KEYS.includes(k as keyof Filters)) {
      (f as Record<string, unknown>)[k] = v === "true";
    } else {
      (f as Record<string, unknown>)[k] = v;
    }
  }
  return f;
}

function parseAnchor(search: string): Anchor | null {
  const p = new URLSearchParams(search);
  const lat = p.get("alat");
  const lng = p.get("alng");
  if (lat === null || lng === null) return null;
  const latN = Number(lat);
  const lngN = Number(lng);
  if (Number.isNaN(latN) || Number.isNaN(lngN)) return null;
  return {
    lat: latN,
    lng: lngN,
    label: p.get("alabel") ?? "",
    precision: (p.get("aprec") as Anchor["precision"]) ?? "address",
  };
}

function serialize(filters: Filters, view: string, venue: string | null, anchor: Anchor | null): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(filters)) {
    if (v === undefined || v === "" || v === false) continue;
    p.set(k, String(v));
  }
  p.set("view", view);
  if (venue) p.set("venue", venue);
  if (anchor) {
    p.set("alat", String(anchor.lat));
    p.set("alng", String(anchor.lng));
    p.set("aprec", anchor.precision);
    if (anchor.label) p.set("alabel", anchor.label);
  }
  return p.toString();
}

export function useFilters() {
  const [filters, setFilters] = useState<Filters>(() => parse(window.location.search));
  const [view, setView] = useState<string>(
    () => new URLSearchParams(window.location.search).get("view") ?? "schedule",
  );
  const [venue, setVenue] = useState<string | null>(
    () => new URLSearchParams(window.location.search).get("venue"),
  );
  const [anchor, setAnchor] = useState<Anchor | null>(() => parseAnchor(window.location.search));

  // Reflect state into the URL whenever it changes.
  useEffect(() => {
    const qs = serialize(filters, view, venue, anchor);
    const next = `${window.location.pathname}?${qs}`;
    window.history.replaceState(null, "", next);
  }, [filters, view, venue, anchor]);

  const setFilter = useCallback(<K extends keyof Filters>(key: K, value: Filters[K]) => {
    setFilters((prev) => {
      const next = { ...prev };
      if (value === undefined || value === "" || value === false) {
        delete next[key];
      } else {
        next[key] = value;
      }
      return next;
    });
  }, []);

  const clear = useCallback(() => setFilters({}), []);

  const openVenue = useCallback((slug: string) => setVenue(slug), []);
  const closeVenue = useCallback(() => setVenue(null), []);

  const setLocation = useCallback((a: Anchor | null) => setAnchor(a), []);

  return {
    filters,
    setFilter,
    clear,
    view,
    setView,
    venue,
    openVenue,
    closeVenue,
    anchor,
    setLocation,
  };
}
