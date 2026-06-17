## ADDED Requirements

### Requirement: Venues carry a stable place identifier

The system SHALL store a Google Place identifier, an external image URL (for the Wikimedia tier), and image-source metadata on each venue, without storing image bytes.

#### Scenario: Place identifier persisted

- **WHEN** a venue is resolved to a Google place
- **THEN** its place identifier and image source are stored on the venue, and no image file is persisted

#### Scenario: Wikimedia URL persisted

- **WHEN** a venue is resolved to a Wikimedia Commons image
- **THEN** its external image URL, attribution, and image source are stored on the venue, and no image bytes are persisted

### Requirement: Backfill resolves venues to places

The system SHALL provide an idempotent command that matches venues to Google places by name and address and flags low-confidence matches for review.

#### Scenario: Confident match is stored

- **WHEN** the resolve command runs for a venue with a clear name/address match
- **THEN** it stores the place identifier and does not re-resolve it on a later run unless a refresh is requested

#### Scenario: Ambiguous match is flagged

- **WHEN** the resolve command cannot confidently match a venue
- **THEN** it flags the venue for review rather than storing a guessed identifier

### Requirement: Reviewer confirms or rejects ambiguous matches

The system SHALL let a reviewer confirm or reject a flagged candidate match (a venue with a candidate place identifier but no confirmed image source), via both a management command and an admin action.

#### Scenario: Confirm promotes a candidate

- **WHEN** a reviewer confirms a venue that has a candidate place identifier
- **THEN** its image source is set to the Google place tier, its required attribution is captured, and its review flag is cleared, so the venue serves the confirmed place photo

#### Scenario: Reject drops a candidate to the next tier

- **WHEN** a reviewer rejects a flagged candidate
- **THEN** the candidate place identifier and review flag are cleared and the venue falls through to the next image tier

#### Scenario: Confirm works without the API key

- **WHEN** a reviewer confirms a candidate while the photo API key is not configured
- **THEN** the venue is still promoted to the place tier with empty attribution, and no external photo call is made (the proxy resolves the photo at request time)

#### Scenario: Reviewer sees the candidate photo in admin

- **WHEN** a reviewer opens a flagged venue in the admin (or scans the venue changelist)
- **THEN** the candidate photo is shown as a preview (with the place identifier and a link to verify the place) so the match can be confirmed or rejected by sight, and venues are filterable by review flag and image source

### Requirement: Wikimedia Commons photo tier

The system SHALL resolve a Creative-Commons-licensed Wikimedia Commons photo for venues that are not confirmed on the Google tier, store its stable URL and required attribution, and fail closed when no licensed image is available.

#### Scenario: Commons image stored with attribution

- **WHEN** the Wikimedia backfill finds a confident, free-licensed Commons image for an eligible venue
- **THEN** it stores the image URL, the required attribution, and the Wikimedia image source, and does not re-resolve it on a later run unless a refresh is requested

#### Scenario: No licensed image leaves the fallback

- **WHEN** the Wikimedia lookup returns no result or only non-free-licensed images, or errors
- **THEN** the venue is left unchanged and continues to show the category fallback, and no error is surfaced

#### Scenario: Confirmed Google photo is never overwritten

- **WHEN** the Wikimedia backfill runs over a venue already confirmed on the Google tier
- **THEN** that venue is skipped and its Google photo source is preserved

### Requirement: Stock imagery is not used

The system SHALL NOT use stock-photo sources (e.g. Unsplash) for venue images, because generic stock imagery misrepresents the specific venue.

#### Scenario: Gap falls to an honest illustration

- **WHEN** a venue has neither a confirmed Google photo nor a licensed Commons photo
- **THEN** its image is the honest category illustration, not a stock photo of a different place

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
- **THEN** it includes an image object with a URL, an attribution (present only for licensed photos), and a source indicating whether it is a Google place photo, a Wikimedia Commons photo, or the fallback

### Requirement: Image rendering with attribution in the UI

The system SHALL display the venue image in the venue detail view and render the attribution whenever the image is a licensed photo (Google place or Wikimedia Commons).

#### Scenario: Detail view shows photo and credit

- **WHEN** a venue with a licensed photo (Google place or Wikimedia Commons) is opened in the detail view
- **THEN** its photo is shown with the attribution caption visible

#### Scenario: Image load error swaps to the fallback

- **WHEN** the venue image fails to load in the detail view
- **THEN** the image is swapped to the category fallback illustration so the view always shows something honest

#### Scenario: Lists avoid per-row photo calls

- **WHEN** venues are shown in a list, card, or map pin
- **THEN** the view does not trigger a per-row external photo call, using the fallback (or a cached thumbnail) instead

### Requirement: Feature degrades safely without configuration

The system SHALL function with the image feature unconfigured: builds, pages, and existing endpoints work, with every venue showing the fallback.

#### Scenario: Unconfigured deploy

- **WHEN** the application runs without the image API key configured
- **THEN** all venues display the category fallback and no errors are surfaced to users
