## Why

WorldCup Watcher is a phone-first product — people check "where can I watch this near me" on the go. Today that's mobile web. Native iOS/Android apps unlock capabilities mobile web can't do well, which are the real reasons to ship native:

- **Push notifications** — match reminders ("your team plays in 1 hour", "Round of 32 matchup just set"), the single biggest re-engagement lever.
- **Native share** — a one-tap, OS-native share sheet to send a venue/match to friends (clunky on web).
- **Live location on the map** — proper native geolocation to show "you are here" and sort venues by real distance, with a first-class permission flow.
- **A foundation for social features** — once there's an installed app with identity + push, "who else I know is going to this watch party?" becomes feasible.

The frontend is already a mobile-friendly React + Vite SPA, so wrapping it with **Capacitor** (which we've used successfully before) yields both platforms from the existing build with minimal change — no rewrite. This change delivers the **native shell + share + native geolocation** that make the app genuinely native today, and **paves the way** for push and social, which are scoped as their own follow-on changes (they need backend work: device-token storage, a send service / APNs+FCM, and identity).

## What Changes

- Add **Capacitor** to the `frontend/` web project (`@capacitor/core` + CLI + `@capacitor/ios` + `@capacitor/android`), with `capacitor.config.ts` pointing `webDir` at Vite's `dist/`. The native shells load the bundled web build.
- **Talk to the production API over HTTPS:** mobile builds set `VITE_API_BASE` to the deployed Render API (the app is a thin client; the API stays the source of truth). Add the Capacitor native origins (`capacitor://localhost`, `http(s)://localhost`) to Django's `CORS_ALLOWED_ORIGINS`.
- **Native geolocation:** use the Capacitor Geolocation plugin for "use my location" (with the existing `navigator.geolocation` as web fallback), plus the iOS `NSLocationWhenInUseUsageDescription` and Android location permissions.
- **Native share:** a share action (Capacitor Share plugin) to send a venue or match via the OS share sheet, with a web fallback (`navigator.share`).
- **External links** (Google Maps, venue websites, StageHopper) open in the **system browser** (Capacitor Browser plugin) rather than dead-ending in the webview.
- **Mobile chrome:** safe-area insets for the notch (`env(safe-area-inset-*)`), status-bar styling that matches the light/dark theme, a splash screen, and app icons.
- **Build/release flow** documented: `vite build` → `cap sync` → open in Xcode / Android Studio to run and submit. The web app is unchanged — the same `dist/` serves web and both native shells.

## Capabilities

### New Capabilities
- `mobile-app`: package the existing web build as native iOS and Android apps via Capacitor — production-API client, native geolocation, native share, external-link handling, and mobile chrome (safe areas, status bar, splash, icons).

<!-- Deliberately deferred to their own follow-on changes (they need backend +
     identity work this change only unblocks): push notifications
     (match reminders) and social ("who's going to this watch party"). -->

### Modified Capabilities
<!-- No behavior change to existing web capabilities; the API gains native origins
     in its CORS allowlist, which doesn't alter its requirements. -->

## Impact

- **New code/config:** `frontend/capacitor.config.ts`, `frontend/ios/` and `frontend/android/` native projects, app icons/splash assets, and small client touches (geolocation plugin wrapper, external-link helper, safe-area CSS, status-bar theming).
- **New dependencies (frontend):** `@capacitor/core`, `@capacitor/cli`, `@capacitor/ios`, `@capacitor/android`, `@capacitor/geolocation`, `@capacitor/browser`, `@capacitor/status-bar`, `@capacitor/splash-screen`.
- **Backend:** add Capacitor origins to `CORS_ALLOWED_ORIGINS`; no schema or endpoint change (the public read API already serves the web client).
- **Tooling:** native builds require Xcode (iOS) and Android Studio/SDK; app-store accounts and signing for submission.
- **No change to the web app** — Capacitor is additive over the same Vite build.
