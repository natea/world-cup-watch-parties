import { useCallback, useEffect, useState } from "react";
import type { Filters } from "./types";

// A single shared, URL-synced filter set. Every view reads the same object, so
// switching views preserves filters and keeps results consistent. The URL is
// the source of truth, so a filtered view is shareable/bookmarkable.

const BOOL_KEYS: (keyof Filters)[] = ["exclude_bars", "family_friendly"];

// Keys that are tracked separately from the filter set.
const NON_FILTER_KEYS = new Set(["view", "venue"]);

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

function serialize(filters: Filters, view: string, venue: string | null): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(filters)) {
    if (v === undefined || v === "" || v === false) continue;
    p.set(k, String(v));
  }
  p.set("view", view);
  if (venue) p.set("venue", venue);
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

  // Reflect state into the URL whenever it changes.
  useEffect(() => {
    const qs = serialize(filters, view, venue);
    const next = `${window.location.pathname}?${qs}`;
    window.history.replaceState(null, "", next);
  }, [filters, view, venue]);

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

  return { filters, setFilter, clear, view, setView, venue, openVenue, closeVenue };
}
