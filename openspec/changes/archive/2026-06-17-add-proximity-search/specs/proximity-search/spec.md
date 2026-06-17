## ADDED Requirements

### Requirement: Resolve a ZIP code to coordinates

The system SHALL resolve a Massachusetts ZIP code to coordinates using a bundled offline lookup, returning the location and a precision marker indicating an approximate (centroid) result.

#### Scenario: Known ZIP resolves

- **WHEN** a client requests location resolution for a valid in-area ZIP code
- **THEN** the response returns coordinates, a human label, and a precision of "zip" without any external network call

#### Scenario: Unknown ZIP

- **WHEN** the ZIP is not in the bundled table
- **THEN** the response indicates no match, without error

### Requirement: Resolve a street address to coordinates

The system SHALL resolve a full street address to coordinates via an external US geocoder, returning a precision marker indicating an exact result, and SHALL degrade gracefully when the geocoder is unavailable or returns no match.

#### Scenario: Address geocodes to an exact point

- **WHEN** a client requests location resolution for a resolvable US street address
- **THEN** the response returns coordinates with a precision of "address"

#### Scenario: Geocoder unavailable or no match

- **WHEN** the geocoder cannot be reached or returns no result
- **THEN** the endpoint responds without error and signals that the address could not be resolved, so the client can fall back to a ZIP or no anchor

### Requirement: Distance-sorted map from a resolved location

The system SHALL drive the map's existing distance sort from the resolved coordinates, returning only venues with coordinates and ordering them nearest-first with a distance value.

#### Scenario: Nearest venues first

- **WHEN** the map is requested with a resolved anchor
- **THEN** venues with coordinates are returned sorted by distance from the anchor, each carrying its distance

### Requirement: Map-screen proximity control

The system SHALL provide, on the Map screen only, a control to enter a ZIP or address and a "use my location" action, route the resolved point into the map anchor, display per-venue distances, and reflect the anchor in the URL.

#### Scenario: Entering a ZIP re-centers the map

- **WHEN** the user enters a ZIP in the Map screen's location control
- **THEN** the map sorts venues by distance from that ZIP and shows each venue's distance, with the anchor reflected in the URL

#### Scenario: Use my location

- **WHEN** the user activates "use my location" and grants permission
- **THEN** the map sorts venues by distance from the device location

#### Scenario: Permission denied or unavailable

- **WHEN** geolocation is denied or unavailable
- **THEN** the map remains usable and prompts for a ZIP or address instead

#### Scenario: Exact vs approximate distances

- **WHEN** the anchor came from an address versus a ZIP
- **THEN** the UI presents address-based distances as exact and ZIP-based distances as approximate

#### Scenario: Other views unaffected

- **WHEN** the user switches to the schedule or by-team view
- **THEN** the proximity control and distance display do not appear there

### Requirement: User location is not persisted

The system SHALL use a user's location only to compute distances for the current request and SHALL NOT store it.

#### Scenario: No retention

- **WHEN** a proximity request is served
- **THEN** the user's coordinates are not written to the database or logs
