## 1. Capacitor setup

- [x] 1.1 Add Capacitor to `frontend/` (`@capacitor/core`, `@capacitor/cli`, `@capacitor/ios`, `@capacitor/android`); `capacitor.config.ts` with `appId`, `appName`, `webDir: "dist"`
- [x] 1.2 `cap add ios` + `cap add android`; native projects committed (base stays `/` — Capacitor 8 serves from a localhost scheme, no relative-base change needed)
- [x] 1.3 Confirm the bundled SPA loads and renders in the iOS Simulator (verified). Android emulator pending the Android SDK.

## 2. Production API + CORS

- [x] 2.1 Mobile build sets `VITE_API_BASE` to the production API URL via `frontend/.env.production`
- [x] 2.2 Append the Capacitor native origins (`capacitor://localhost`, `http(s)://localhost`) to Django `CORS_ALLOWED_ORIGINS` (unconditionally, so prod's env-driven value still includes them). Confirmed prod currently rejects the native origin — this fix takes effect on deploy.

## 3. Native capabilities (behind a platform check; web fallback preserved)

- [x] 3.1 Geolocation: `frontend/src/native.ts` uses `@capacitor/geolocation` natively, `navigator.geolocation` on web; iOS `NSLocationWhenInUseUsageDescription` added; Android perms come from the plugin manifest; "you are here" marker already exists
- [x] 3.2 Share: `@capacitor/share` natively (`navigator.share`/clipboard fallback); Share button on the venue detail
- [x] 3.3 External links: a delegated click handler routes `target="_blank"` http(s) links through `@capacitor/browser` on native

## 4. Mobile chrome

- [x] 4.1 `viewport-fit=cover` + `env(safe-area-inset-*)` padding on `.app` (verified inset in the simulator)
- [x] 4.2 Status bar themed to light/dark (`@capacitor/status-bar`); splash background configured (`@capacitor/splash-screen`)
- [ ] 4.3 Generate app icons + splash artwork (needs a 1024px source image) — pending before store submission

## 5. Build, test, docs

- [x] 5.1 Documented the release flow (`vite build` → `cap sync` → Xcode/Android Studio) in the README, with toolchain notes
- [x] 5.2 iOS Simulator smoke test: app builds (`** BUILD SUCCEEDED **`), launches, and renders the SPA with safe areas + theme. Data load is blocked only by prod CORS (fixed here; effective on deploy). Android emulator + device-signed build pending the SDK.
- [x] 5.3 README "Mobile app (Capacitor)" section: `appId`, prod API URL, plugins, and the Xcode-MCP/axiom tooling note

## 7. iOS UI refinements (from simulator review)

- [x] 7.1 iOS-only bottom tab bar (frosted-glass) for thumb reach, gated to `data-platform="ios"`; the website keeps its top tabs
- [x] 7.2 Single safe-area inset: webview `contentInset: "never"` + CSS `env(safe-area-inset-*)` (fixed the top gap and the cut-off bottom bar caused by double-insetting)
- [x] 7.3 Tab buttons styled with background/border + filled-accent active state, plus monochrome icons (calendar / map-pin / people) on the iOS bar and web tabs
- [x] 7.4 Prevent iOS focus-zoom: tappable form controls (search/inputs/selects) kept at 16px on phones so focusing a field doesn't zoom/shift the layout
- [x] 7.5 Isolate the Leaflet map's stacking context (`isolation: isolate`) so its panes/controls can't paint over the bottom tab bar
- [x] 7.6 Responsive fixes surfaced on device: proximity "Go" button no longer overflows narrow screens; the "Massachusetts 2026" subtitle is hidden under 560px so the brand never wraps

## 6. Follow-ons (out of scope here — noted for sequencing)

- [ ] 6.1 (separate change) Push notifications: device-token storage, APNs/FCM, match-reminder sends
- [ ] 6.2 (separate change) Social/identity: accounts + "who's going to this watch party" presence
