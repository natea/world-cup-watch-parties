## ADDED Requirements

### Requirement: Schedule endpoint

The system SHALL expose a read endpoint returning screenings ordered by match kickoff and grouped by day, honoring the active filter set.

#### Scenario: Day-grouped schedule

- **WHEN** a client requests the schedule endpoint
- **THEN** the response contains screenings ordered by `match.kickoff`, grouped by local day, each carrying its venue, match (with resolved or placeholder teams), kickoff in UTC, and cost/access fields

#### Scenario: Multiple matches per day and venue

- **WHEN** a day has multiple matches and a venue shows more than one
- **THEN** every matching screening appears once, correctly attributed to its match and venue

### Requirement: Map endpoint

The system SHALL expose a read endpoint returning only venues that have at least one screening passing the active filters, each with coordinates and its relevant screening(s).

#### Scenario: Only matching venues with coordinates

- **WHEN** a client requests the map endpoint with an active filter set
- **THEN** the response includes only venues that have coordinates and at least one screening satisfying the filters

#### Scenario: Distance sorting from an anchor

- **WHEN** the request supplies an anchor latitude/longitude
- **THEN** venues are returned sorted by Haversine distance from the anchor, using a bounding-box prefilter

### Requirement: Screenings endpoint with team and filter parameters

The system SHALL expose a screenings endpoint that accepts team parameters and resolves either "matches featuring the team" or "venues affiliated with the team", and accepts the shared composable filters.

#### Scenario: Team featured in a match

- **WHEN** a client requests screenings for a team in "playing" mode
- **THEN** the response contains screenings of matches that feature that team

#### Scenario: Team supporter hub

- **WHEN** a client requests screenings for a team in "supporter hub" mode
- **THEN** the response contains screenings at venues affiliated with that team, independent of whether the team plays

#### Scenario: Followed team's later matches appear automatically

- **WHEN** a knockout fixture resolves to include a followed team and screenings are re-materialized
- **THEN** that team's newly scheduled screenings appear in the team query without manual data edits

### Requirement: Venue detail endpoint

The system SHALL expose a venue detail endpoint, keyed by venue slug, that returns the venue's full profile (including affiliations and provenance) and every screening it hosts ordered by kickoff.

#### Scenario: Existing venue returns profile and screenings

- **WHEN** a client requests the detail endpoint for a known venue slug
- **THEN** the response contains the venue's profile with its affiliations and provenance, plus all of its screenings ordered by kickoff with TBD-safe matchup labels

#### Scenario: Unknown venue returns not found

- **WHEN** a client requests the detail endpoint for a slug that does not exist
- **THEN** the endpoint responds with HTTP 404

### Requirement: Composable filters shared across all views

The system SHALL implement family-friendly, free/paid, indoor/outdoor, venue-type, and region filters as composable constraints over the Screening queryset, applied identically by the schedule, map, and screenings endpoints.

#### Scenario: Family-friendly is evaluated at screening time

- **WHEN** the family-friendly filter is active and a venue is all-ages by day but 21+ after its evening cutoff
- **THEN** the venue's daytime screenings are included and its post-cutoff screenings are excluded

#### Scenario: Free toggle derives from the cost enum

- **WHEN** the free filter is active
- **THEN** screenings of every non-ticketed cost type (including free-lottery and free-minimum) are included and ticketed screenings are excluded

#### Scenario: Filters compose consistently across views

- **WHEN** the same filter set (e.g. exclude-bars + outdoor + region) is applied to the schedule, map, and screenings endpoints
- **THEN** all three return results drawn from the same filtered screening set
