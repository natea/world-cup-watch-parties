## 1. Location resolution (backend)

- [x] 1.1 Bundle a Massachusetts ZIP→(lat,lng) centroid data file under `data/` (document source + regeneration); add a loader
- [x] 1.2 Add a geocode resolver: ZIP via the bundled table (precision "zip"); street address via the US Census Bureau geocoder (precision "address"), behind a small provider seam
- [x] 1.3 Add `GET /api/geocode/?zip=` / `?address=` returning `{lat, lng, label, precision}`; no-match and geocoder-unavailable return cleanly (no 500); never persist input coordinates
- [x] 1.4 Tests: ZIP hit/miss, address geocode (mocked) success + failure fallback, response shape

## 2. Map-screen proximity UI (frontend)

- [x] 2.1 Add a "Find watch parties near you" control on the Map screen only: ZIP/address input (resolve on submit) + "Use my location" (browser geolocation)
- [x] 2.2 On resolve, set the map `lat`/`lng` anchor (reuse existing `/api/map` anchor + Haversine sort); handle geolocation denial / no-match with a prompt to enter a ZIP
- [x] 2.3 Show per-venue distance in miles (km available); label address-based distances exact and ZIP-based approximate
- [x] 2.4 URL-sync the anchor + precision so a located map is shareable and survives reload; keep it scoped to the map view

## 3. Tests & docs

- [x] 3.1 Endpoint + ordering tests: distance-sorted map from a known anchor; ZIP and address paths
- [x] 3.2 README + API endpoint table: `/api/geocode/`, the Map proximity control, the Census dependency (address only), and the privacy note (location not stored)
