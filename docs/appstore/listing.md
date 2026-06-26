# App Store listing: Match Day MA

Draft metadata for App Store Connect, rewritten to be IP-safe after the
Guideline 5.2.1 rejection (June 23, 2026). Avoids "FIFA", "World Cup", the
official tournament name, "official", "Gillette Stadium", and any team /
sponsor / broadcaster mark. Describes the product with generic soccer language
only. Tune wording before submitting.

- **Name (≤30):** Match Day MA: Soccer 2026  (26 chars)
  - Alternates: `Soccer Watch Parties MA` (24) · `KickOff MA: Soccer 2026` (24)
- **Subtitle (≤30):** Find soccer watch parties  (26 chars)
  - Alternates: `Watch the matches near you` (27) · `Boston soccer fan meetups` (26)
- **Bundle ID:** `app.stagehopper.worldcup`  (not store-visible; leave as-is)
- **Primary category:** Sports
- **Secondary category:** Travel (or Entertainment)
- **Primary language:** English (U.S.)
- **Price:** Free
- **Age rating:** 4+ (no objectionable content; note it lists bars/venues that serve alcohol, answer the questionnaire accordingly)

## Promotional text (≤170 chars)

Find soccer watch parties across Massachusetts for the 2026 tournament. Browse by schedule, map, or team. Bars, breweries, fan zones, and free community meetups.

## Description

The biggest soccer summer in years is coming to Massachusetts, and Match Day MA helps you find the best place to watch every match. Browse by schedule, by map, or by the team you follow, then pick the spot that fits your crowd.

No tickets, no accounts, just where to watch.

Find your match, your crowd, and your spot:

• SCHEDULE: every match, grouped by day, in your local time. Hide games that are already over with one tap.

• MAP: see watch parties near you. Enter a ZIP or address (or use your location) and sort venues by distance.

• BY TEAM: follow a team and see both where it is playing and which bars are its supporter hubs.

Filter the way you actually decide:
• Family-friendly (all-ages, and we hide venues that turn 21+ later in the evening)
• Free vs. ticketed
• Indoor vs. outdoor
• Venue type: bar, brewery, plaza/fan zone, park, hotel, community space, and more
• Region: Greater Boston, Cambridge/Somerville, North Shore, South Shore, MetroWest, Foxborough, Worcester

From downtown fan zones to free municipal watch parties, soccer-bar supporter crowds, and brewery and waterfront screenings, Match Day MA helps you find the right place to be for every game.

A finder, not a ticketing site. We link out; we don't transact.

Match Day MA is an independent finder and is not affiliated with, endorsed by, or sponsored by any soccer governing body, tournament organizer, or venue.

## Keywords (≤100 chars, comma-separated, no spaces after commas)

soccer,watch party,football,2026,matches,fixtures,fan fest,meetup,bars,boston,massachusetts,pub

(95 / 100 chars. No word duplicated from Name/Subtitle. Deliberately excludes
world, cup, fifa, gillette, and any team/sponsor/broadcaster name. Dropped
"fan zone" to fit the 100-char limit; "fan fest" + "pub" carry similar intent.)

## URLs

- **Support URL:** https://worldcup.stagehopper.app/  (or a dedicated support page)
- **Marketing URL:** https://worldcup.stagehopper.app/
- **Privacy Policy URL:** https://worldcup.stagehopper.app/privacy_worldcup.html

## App Privacy (App Store Connect questionnaire)

- **Location (Precise or Coarse):** collected, **not linked to identity**, **not used for tracking**, used only for **App Functionality** (sorting venues by distance). It is sent to our API to compute distances and is **not stored**.
- **Usage data / analytics:** privacy-friendly analytics (Umami), no cookies, no cross-site tracking, not linked to identity. Declare **Usage Data → Analytics**, not linked, no tracking. (Confirm against the current analytics config.)
- **No accounts, no contact info, no purchases.**

## Review notes (for App Review)

- No login required; all features are available immediately.
- "Use my location" is optional; the app is fully usable by typing a ZIP/address, and degrades gracefully if location is denied.
- External links (Google Maps, venue sites) open in the system browser by design.
- Data is sourced from public listings; the app links out and does not sell tickets.
- This version removes all third-party marks flagged under Guideline 5.2.1: the app, its metadata, screenshots, and legal pages no longer reference any unauthorized third-party tournament brand. Match Day MA is an independent, informational finder with no affiliation.

## What's New (version 1.0)

Initial release: schedule, map with proximity search, and by-team views for soccer watch parties across Massachusetts in 2026.

## Pre-submission scrub checklist (Guideline 5.2.1)

Done in code on this branch:
- [x] In-app header/footer brand renamed to "Match Day MA" (`frontend/src/App.tsx`).
- [x] Removed "Official FIFA standings" footer string (`frontend/src/App.tsx`).
- [x] Share text changed to "Watch the matches at ..." (`frontend/src/components/VenueDetail.tsx`).
- [x] `frontend/index.html` title + OG/Twitter metadata scrubbed.
- [x] `terms.html` and `privacy_worldcup.html` (web `public/`) scrubbed and disclaimer generalized.
- [x] `docs/appstore/privacy-policy.md` and this listing scrubbed.

Still required before resubmitting (manual / out of band):
- [ ] Re-run `bunx cap sync` so the native iOS bundle picks up the new web build (regenerates `frontend/ios/App/App/public/`).
- [ ] **Re-shoot all App Store screenshots and the app preview** so none show "WorldCup Watcher", "Official FIFA standings", the old metadata, or any team flags/marks used as a headline.
- [ ] Remove any "Gillette Stadium" caption from screenshots; refer to it generically (e.g., "the stadium in Foxborough").
- [ ] Update the App Store Connect app name, subtitle, keywords, description, and promo text to the values above.
- [ ] Consider a 30-minute IP attorney review before launch, given commercialization plans.
