## Context

The map endpoint already accepts an `lat`/`lng` anchor and returns venues sorted by Haversine distance (built in the screening-api capability, with a bounding-box prefilter). What's missing is a humane way to *set* that anchor — from a ZIP, an address, or the device — and a Map-screen UI to drive it. This change is additive: it feeds coordinates into the existing distance machinery.

## Goals / Non-Goals

**Goals:**
- Type a ZIP → nearest watch parties, sorted by distance, distances shown.
- Type a full address → exact coordinates → exact distances.
- "Use my location" via browser geolocation.
- Scope the control and distance display to the Map screen; keep it URL-shareable.
- No API key required for the common paths (ZIP + geolocation).

**Non-Goals:**
- Directions / routing / travel time (link out to a maps app instead, later).
- Continuous location tracking; storing user location.
- Coverage outside Massachusetts / the US.
- Replacing the existing filters or the anchor query-param mechanism.

## Decisions

**ZIP via a bundled centroid table; address via the US Census geocoder.**
- ZIP is the common case and should be **offline and instant**: ship a small MA ZIP→(lat,lng) data file (~hundreds of rows) and look up locally. Distances are to the ZIP centroid — labeled "approximate" in the UI. No key, no network, no privacy exposure.
- Address needs real geocoding. Use the **US Census Bureau Geocoding API** (`geocoding.geo.census.gov`): free, no API key, US-only, purpose-built for addresses. It returns precise coordinates → exact distances. Alternatives considered: Nominatim/OSM (usage-policy + rate limits), Mapbox/Google (API keys + billing) — rejected for v1 to stay key-free; the resolver is written so a different provider can be swapped behind it.

**Reuse the map anchor; don't add new distance logic.** The resolver returns `{lat, lng, label, precision}`; the client passes `lat`/`lng` to the existing `/api/map` anchor. No duplicate Haversine, no endpoint coupling. `precision` ("address" | "zip" | "device") drives the UI's exact-vs-approximate wording.

**Map-only UI.** The location control lives on the Map screen; distance display (miles, with km available) is map-scoped. Schedule/by-team are untouched. The anchor (and precision) are URL-synced alongside the existing filter/view state so a located map is shareable and survives reload.

**Graceful degradation.** Address geocode failure (offline, rate-limited, no match) falls back to: ask for a ZIP, or proceed without an anchor (current behavior). Geolocation denial is handled the same way. The map never breaks because location couldn't be resolved.

## Risks / Trade-offs

- **External geocoder availability/limits (address path)** → ZIP and device paths need no external call; address failures degrade to ZIP/none with a clear message. [Risk] Census latency on the request path → resolve on submit (not per keystroke) and show a pending state.
- **ZIP centroid accuracy** → distances are approximate for ZIP; labeled as such. Acceptable for "what's near me" triage; address gives exact.
- **Bundled ZIP data freshness/size** → MA-only keeps it small; ZIP centroids change rarely. Document the source and regeneration step.
- **Privacy** → never persist user location; compute distance for the request and discard. Geolocation only on explicit button press.

## Open Questions

- Source/format for the bundled MA ZIP-centroid table (e.g. a trimmed Census ZCTA gazetteer), and where it lives (`data/`).
- Should distance default to **miles** (US audience) with a km toggle, or show both?
- Is a thin server-side cache of recent address lookups worth it, or premature at this scale?
