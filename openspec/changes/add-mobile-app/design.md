## Context

The client is a React + Vite SPA (`frontend/`) that consumes a public, read-only DRF API over HTTPS (deployed on Render). It's already responsive and phone-first. Capacitor wraps a **static web build** in native iOS/Android shells; since Vite emits a static `dist/`, the wrap is additive — the same build powers web and both native apps. The motivation is the native-only capabilities (push, share, live location) and a base for social features.

## Goals / Non-Goals

**Goals (this change):**
- iOS and Android apps built from the existing Vite `dist/` via Capacitor, no web rewrite.
- The native app is a thin client of the **production** API over HTTPS.
- Native **geolocation** (proximity), native **share**, external links in the system browser.
- Mobile chrome: safe-area insets, themed status bar, splash, app icons.

**Non-Goals (explicitly deferred to their own changes):**
- **Push notifications** — needs device-token storage, a send service, and APNs/FCM credentials.
- **Social** ("who's going") — needs accounts/identity and a presence model.
- **Offline data** — the shell is bundled, but venue/match data still requires network (acceptable; it's a live event).
- App-store submission automation / CI signing (manual first release).

## Decisions

**Capacitor over the existing Vite build (`webDir: dist`).** `cap sync` copies `dist/` into the native projects. Rationale: zero rewrite, one codebase, proven approach. Confirmed compatible — Capacitor is bundler-agnostic; the only Vite consideration is that asset paths must be relative (`base: './'` in `vite.config` if needed) so the file-served webview resolves them. Alternative: React Native / a rewrite — rejected (throws away a working SPA).

**Native app is a remote-API client, bundled-shell.** The web assets ship inside the app (fast, offline shell), but data comes from the deployed API. The mobile build sets `VITE_API_BASE` to the prod API URL (no `localhost` fallback). The API must accept the Capacitor origins — `capacitor://localhost` (iOS), `http://localhost`/`https://localhost` (Android) — added to `CORS_ALLOWED_ORIGINS`. Since the API is public read-only, this is low-risk. Alternative: `server.url` pointing the webview at the live site — rejected; loses the bundled-shell speed/offline and complicates releases.

**Geolocation via the Capacitor plugin with a web fallback.** Replace the raw `navigator.geolocation` call in the proximity control with a small wrapper: use `@capacitor/geolocation` when running natively (proper iOS/Android permission prompts + `Info.plist`/manifest entries), fall back to `navigator.geolocation` on web. This also enables a true "you are here" marker driven by the device position (the map already has the red anchor pin). Detect platform with `Capacitor.isNativePlatform()`.

**External links + share through native APIs.** In a webview, `target="_blank"` can dead-end; route outbound links (Google Maps, venue sites, StageHopper) through `@capacitor/browser` natively. Share uses `@capacitor/share` natively with `navigator.share`/copy as web fallback. Both behind the same platform check, so web behavior is unchanged.

**Mobile chrome.** Add `viewport-fit=cover` + `env(safe-area-inset-*)` padding so the header/content clear the notch and home indicator; theme the status bar (`@capacitor/status-bar`) to match the light/dark setting; configure splash (`@capacitor/splash-screen`) and generate icons. These are native-only niceties that don't affect web.

**Project layout.** Capacitor config + `ios/`/`android/` live under `frontend/` (alongside the web project they wrap). Native folders are committed (standard Capacitor practice) so builds are reproducible; large generated artifacts are gitignored.

## Risks / Trade-offs

- **CORS / origin mismatch** → native requests fail silently → add the Capacitor origins to the allowlist and verify on-device early. [Risk] HTTPS required (Render API is HTTPS; mixed content would be blocked).
- **Asset path resolution in the file-served webview** → set Vite `base: './'` if absolute paths break; verify the bundle loads in the simulator before anything else.
- **Native toolchain + store overhead** → Xcode/Android Studio, signing, store accounts, privacy disclosures (location). One-time setup; document it. Manual first release, automate later.
- **Two release surfaces drift from web** → mitigated by sharing one build; a release is "rebuild web → `cap sync` → submit". Keep web and app version in lockstep.
- **Deferred features create expectations** → push/social are called out as separate changes so this one stays shippable and small.

## Migration Plan

Additive. Install Capacitor in `frontend/`, add platforms, wire the plugins behind platform checks (web untouched), add CORS origins server-side. Build/run in simulators, then on devices, then submit. Rollback = the web app is unaffected; native projects can be removed without touching the SPA.

## Open Questions

- App identifiers / display name (`appId` reverse-DNS, e.g. `app.stagehopper.worldcup`) and store listing details.
- Does the first release go to TestFlight / Play internal testing before public?
- Which Render API URL is canonical for the mobile `VITE_API_BASE` (custom domain vs `onrender.com`)?
