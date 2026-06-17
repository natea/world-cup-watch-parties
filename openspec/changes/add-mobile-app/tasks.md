## 1. Capacitor setup

- [ ] 1.1 Add Capacitor to `frontend/` (`@capacitor/core`, `@capacitor/cli`, `@capacitor/ios`, `@capacitor/android`); `capacitor.config.ts` with `appId`, `appName`, `webDir: "dist"`
- [ ] 1.2 Ensure the Vite build is webview-safe (relative asset base, e.g. `base: "./"` if needed); `cap add ios` + `cap add android`; commit the native projects
- [ ] 1.3 Confirm the bundled SPA loads and renders in the iOS Simulator and Android emulator

## 2. Production API + CORS

- [ ] 2.1 Mobile build sets `VITE_API_BASE` to the production API URL (no localhost fallback for release builds)
- [ ] 2.2 Add the Capacitor native origins (`capacitor://localhost`, `http(s)://localhost`) to Django `CORS_ALLOWED_ORIGINS`; verify on-device API calls succeed

## 3. Native capabilities (behind a platform check; web fallback preserved)

- [ ] 3.1 Geolocation: wrap location lookup to use `@capacitor/geolocation` natively, `navigator.geolocation` on web; add iOS `NSLocationWhenInUseUsageDescription` + Android location permissions; drive a "you are here" marker from the device position
- [ ] 3.2 Share: add a share action via `@capacitor/share` natively, `navigator.share`/copy on web
- [ ] 3.3 External links: open outbound links via `@capacitor/browser` natively

## 4. Mobile chrome

- [ ] 4.1 `viewport-fit=cover` + `env(safe-area-inset-*)` padding on header/content
- [ ] 4.2 Status bar themed to light/dark (`@capacitor/status-bar`); splash screen (`@capacitor/splash-screen`); generate app icons

## 5. Build, test, docs

- [ ] 5.1 Document the release flow: `vite build` → `cap sync` → open in Xcode / Android Studio → run/submit; note toolchain + signing prerequisites
- [ ] 5.2 Smoke test on iOS Simulator + Android emulator: schedule/map/team load from prod API, proximity (locate), share, external link, theme + safe areas
- [ ] 5.3 README: a "Mobile (Capacitor)" section; record `appId`/display name and the canonical mobile API URL

## 6. Follow-ons (out of scope here — noted for sequencing)

- [ ] 6.1 (separate change) Push notifications: device-token storage, APNs/FCM, match-reminder sends
- [ ] 6.2 (separate change) Social/identity: accounts + "who's going to this watch party" presence
