## ADDED Requirements

### Requirement: Three first-class views over one filter set

The system SHALL provide a React + Vite + TypeScript single-page client with schedule, map, and team views, all reading from a single shared active filter set.

#### Scenario: Filter set is shared across views

- **WHEN** a user sets filters in one view and switches to another view
- **THEN** the active filters persist and the new view's results reflect the same filter set

#### Scenario: Schedule view

- **WHEN** the user opens the schedule view
- **THEN** screenings are shown grouped by day and ordered by kickoff, with local kickoff time rendered from the UTC value

#### Scenario: Map view

- **WHEN** the user opens the map view
- **THEN** an interactive map plots only venues with a screening matching the active filters, and selecting a pin reveals that venue's relevant screening(s)

#### Scenario: Team ("alliance") view

- **WHEN** the user selects one or more teams to follow
- **THEN** the view resolves to screenings of those teams' matches and/or screenings at their supporter-hub venues, with a clear distinction between the two senses

### Requirement: Graceful handling of TBD matchups

The system SHALL render fixtures with unresolved opponents using their placeholder labels without breaking any view.

#### Scenario: Unresolved knockout fixture displays

- **WHEN** a screening's match has null teams and placeholder labels
- **THEN** the UI displays the placeholders (e.g. "Winner Group C vs TBD") in all three views without error

### Requirement: Provenance and freshness display

The system SHALL surface source provenance and a last-updated/needs-review indication on screening and venue detail in the client.

#### Scenario: Source shown to the user

- **WHEN** a user inspects a screening or venue
- **THEN** the client displays its source and last-updated information, and indicates when a record is flagged for review

### Requirement: Game-grouped listing (no repeated matchups)

In listings where many venues show the same match, the client SHALL group screenings by game — same teams at the same kickoff — rendering the matchup and kickoff once as a header with the venues listed beneath it, rather than repeating the matchup on every venue row.

#### Scenario: Schedule groups venues under each game

- **WHEN** a day has one match shown at many venues
- **THEN** the schedule renders a single game header (kickoff time, matchup, stage/group) followed by a list of venue rows, each showing the venue, its city, and its cost/access badges without repeating the matchup or time

#### Scenario: Multiple games on one day each get their own group

- **WHEN** a day has more than one distinct match
- **THEN** each match forms its own header-plus-venues group, and groups are ordered by kickoff

#### Scenario: Team "playing" column is game-grouped

- **WHEN** a followed team's matches are shown in the team view's "is playing" column
- **THEN** the venues are grouped under each game using the same game-grouped layout

### Requirement: Venue detail page

The system SHALL provide an in-app venue detail page, reachable by selecting a venue name from any view, that presents the venue's full profile and every screening it hosts.

#### Scenario: Opening a venue from a listing

- **WHEN** a user selects a venue name in the schedule, team, or map view
- **THEN** the client navigates to that venue's detail page (reflected in the URL as a shareable parameter) showing its type, environment, address with an external map link, capacity, food/alcohol, supporter-team/club affiliations, notes, provenance, and last-updated/needs-review status

#### Scenario: Venue detail lists its screenings

- **WHEN** the venue detail page loads
- **THEN** it lists every screening the venue hosts with date and time, cost/access badges, and TBD-safe matchup labels

#### Scenario: Returning preserves prior view and filters

- **WHEN** the user dismisses the venue detail page
- **THEN** the client returns to the view and filter set they came from

### Requirement: Local date affordances in non-day-grouped contexts

The client SHALL show a local calendar date alongside the kickoff time wherever screenings are presented outside the day-grouped schedule (for example map popups and the team and venue-detail views).

#### Scenario: Map popup shows the date

- **WHEN** a user opens a map pin's popup
- **THEN** each screening shows both its local date and kickoff time
