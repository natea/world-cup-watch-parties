## ADDED Requirements

### Requirement: Native iOS and Android apps from the web build

The system SHALL package the existing web build as native iOS and Android applications via Capacitor, loading the bundled web assets without a separate web rewrite.

#### Scenario: App launches and renders the SPA

- **WHEN** the native app is launched on iOS or Android
- **THEN** it loads the bundled web build and renders the schedule/map/team UI

#### Scenario: One build powers web and native

- **WHEN** the web build is produced and synced to the native projects
- **THEN** the native apps run the same UI as the web app, with no divergent web codebase

### Requirement: Production API client over HTTPS

The native app SHALL fetch data from the deployed production API over HTTPS, and the API SHALL accept requests from the native app's origin.

#### Scenario: Native build targets production

- **WHEN** the app is built for release
- **THEN** its API base URL points at the production API (not a local/dev host)

#### Scenario: Cross-origin requests are allowed

- **WHEN** the native webview calls the API from its Capacitor origin
- **THEN** the API permits the request (the native origins are in the CORS allowlist)

### Requirement: Native geolocation for proximity

The system SHALL obtain the device location through the native geolocation capability (with a web fallback) so proximity search and the "you are here" marker work with a proper permission flow.

#### Scenario: Locate on native

- **WHEN** the user taps "use my location" in the native app and grants permission
- **THEN** the device location anchors the map's distance sort and shows a "you are here" marker

#### Scenario: Permission denied is graceful

- **WHEN** location permission is denied or unavailable
- **THEN** the app remains usable and prompts for a ZIP or address instead

#### Scenario: Web fallback unchanged

- **WHEN** the same code runs on the web
- **THEN** it uses the browser geolocation API as before

### Requirement: Native share

The system SHALL provide a share action that uses the native OS share sheet on device (with a web fallback) to share a venue or match.

#### Scenario: Share a venue/match

- **WHEN** the user taps share in the native app
- **THEN** the OS share sheet opens with a link/summary for that venue or match

### Requirement: External links open in the system browser

The system SHALL open outbound links (maps, venue sites, partner links) in the system browser rather than trapping them in the app webview.

#### Scenario: Tapping an external link

- **WHEN** the user taps an external link in the native app
- **THEN** it opens in the system browser and the app webview is not navigated away

### Requirement: Mobile chrome

The system SHALL present native chrome appropriate to mobile devices: content clears the device safe areas, the status bar matches the active theme, and the app has a splash screen and icons.

#### Scenario: Safe areas respected

- **WHEN** the app runs on a device with a notch / home indicator
- **THEN** the header and content are inset so nothing is obscured

#### Scenario: Status bar matches theme

- **WHEN** the user is in light or dark mode
- **THEN** the status bar styling matches it
