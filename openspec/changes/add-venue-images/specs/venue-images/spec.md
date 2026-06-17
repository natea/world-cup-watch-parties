## ADDED Requirements

### Requirement: Venues carry a stable place identifier

The system SHALL store a Google Place identifier and image-source metadata on each venue, without storing image bytes.

#### Scenario: Place identifier persisted

- **WHEN** a venue is resolved to a Google place
- **THEN** its place identifier and image source are stored on the venue, and no image file is persisted

### Requirement: Backfill resolves venues to places

The system SHALL provide an idempotent command that matches venues to Google places by name and address and flags low-confidence matches for review.

#### Scenario: Confident match is stored

- **WHEN** the resolve command runs for a venue with a clear name/address match
- **THEN** it stores the place identifier and does not re-resolve it on a later run unless a refresh is requested

#### Scenario: Ambiguous match is flagged

- **WHEN** the resolve command cannot confidently match a venue
- **THEN** it flags the venue for review rather than storing a guessed identifier

### Requirement: Attributed photo proxy

The system SHALL serve venue photos through a backend proxy that keeps the API key server-side and provides the required attribution, never rehosting image bytes in our own storage.

#### Scenario: Photo served with attribution

- **WHEN** a client requests a venue's photo and the venue has a place identifier and the API key is configured
- **THEN** the proxy returns the current place photo and the venue's image metadata includes the required attribution

#### Scenario: Missing key or identifier falls back

- **WHEN** the API key is not configured or the venue has no place identifier
- **THEN** the photo request resolves to the category fallback and no external photo call is made

### Requirement: Honest category fallback

The system SHALL provide a rights-free fallback image chosen by venue type when no licensed photo is available, visually distinct from a real photo.

#### Scenario: Fallback by venue type

- **WHEN** a venue has no usable place photo
- **THEN** the venue's image is a category illustration corresponding to its venue type, marked as a fallback (no photo attribution)

### Requirement: Uniform image field in the API

The system SHALL expose each venue's image as a single object describing its URL, attribution, and source, so the client renders it uniformly.

#### Scenario: Image object on a venue

- **WHEN** a venue is serialized
- **THEN** it includes an image object with a URL, an attribution (present only for licensed photos), and a source indicating whether it is a place photo or the fallback

### Requirement: Image rendering with attribution in the UI

The system SHALL display the venue image in the venue detail view and render the attribution whenever the image is a licensed photo.

#### Scenario: Detail view shows photo and credit

- **WHEN** a venue with a licensed photo is opened in the detail view
- **THEN** its photo is shown with the attribution caption visible

#### Scenario: Lists avoid per-row photo calls

- **WHEN** venues are shown in a list, card, or map pin
- **THEN** the view does not trigger a per-row external photo call, using the fallback (or a cached thumbnail) instead

### Requirement: Feature degrades safely without configuration

The system SHALL function with the image feature unconfigured: builds, pages, and existing endpoints work, with every venue showing the fallback.

#### Scenario: Unconfigured deploy

- **WHEN** the application runs without the image API key configured
- **THEN** all venues display the category fallback and no errors are surfaced to users
