## Why

The map already plots venues and can sort them by distance from an anchor point — but there's no way for a user to *set* that anchor to where they actually are. They want to type their **ZIP code** (or full **address**) and immediately see the watch parties nearest them, sorted by distance, with the distances shown. Today the anchor is only reachable by hand-editing `lat`/`lng` query params; this exposes it as a first-class, on-map control.

## What Changes

- Add server-side **location resolution** that turns a user's input into coordinates:
  - **ZIP code** → a bundled Massachusetts ZIP-centroid lookup (offline, no API key, no network). Distances are to the ZIP centroid (clearly labeled as approximate).
  - **Street address** → the free **US Census Bureau geocoder** (no key, US-only) for exact coordinates and therefore exact distances. Degrades gracefully (falls back to ZIP/none) if the service is unavailable.
- Expose this via a small endpoint (e.g. `GET /api/geocode/?zip=` or `?address=`) returning `{lat, lng, label, precision}`; the existing map endpoint's `lat`/`lng` anchor + Haversine sort does the rest (no new distance math).
- Add a **"Find watch parties near you" control on the Map screen only**: an input accepting a ZIP or address, plus a **"Use my location"** button (browser geolocation). On resolve, the map re-centers, venues sort by distance, and each shows its distance (in **miles** for US users). The anchor is **URL-synced** so a located map is shareable.
- Make distance display and the anchor **map-scoped** — the schedule and by-team views are unchanged.
- **Privacy:** user location is used only to compute distances for the request; it is **not stored**.

## Capabilities

### New Capabilities
- `proximity-search`: resolve a user's ZIP or address (or device location) to coordinates and drive the map's distance-sorted, distance-labeled view from it.

### Modified Capabilities
<!-- The map endpoint's lat/lng anchor + Haversine distance sort already exists
     in the (archived) screening-api capability; proximity-search builds on it
     and does not change its requirements. -->

## Impact

- **New code:** a geocode resolver + endpoint (`events/`), a bundled MA ZIP-centroid data file, and a Map-screen location control + geolocation in the client (`frontend/`).
- **External dependency (optional, address-only):** US Census Bureau geocoding API — no key, US-only, called at request time; ZIP and "use my location" paths need no external service.
- **No schema changes**; reuses the existing map anchor/Haversine path.
- **Tests:** ZIP→coordinates resolution, address geocode (mocked), unknown/invalid input handling, and distance-sorted ordering from a known anchor.
