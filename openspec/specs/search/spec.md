# search Specification

## Purpose
TBD - created by archiving change add-search. Update Purpose after archive.
## Requirements
### Requirement: Typeahead search endpoint

The system SHALL provide a search endpoint that accepts a query string and returns a ranked, length-capped list of typed suggestions across venues, teams/countries, and supporter hubs.

#### Scenario: Query returns typed suggestions

- **WHEN** a client requests the search endpoint with a non-empty query
- **THEN** it returns a list of suggestions, each with a type, a display label, a sublabel, and a target describing how to navigate to it, capped at the configured maximum

#### Scenario: Short or empty query returns nothing

- **WHEN** the query is empty or shorter than the minimum length
- **THEN** the endpoint returns an empty suggestion list without error

### Requirement: Search matches names, codes, and description keywords

The system SHALL match the query against venue name/city, team name and FIFA code, supporter-hub club and affiliated team name, and keyword occurrences in venue notes.

#### Scenario: Venue found by name

- **WHEN** the query matches part of a venue's name
- **THEN** a venue suggestion for that venue is returned with a target that opens its detail page

#### Scenario: Country found by name or code

- **WHEN** the query matches a team's name or its three-letter FIFA code
- **THEN** a team suggestion is returned with a target that focuses that team in the by-team view

#### Scenario: Venue found by supporter-hub affiliation

- **WHEN** the query matches a supporter-hub club name or an affiliated team name
- **THEN** the affiliated venue is returned as a suggestion (e.g. a query for the team's supporters group returns its hub venue)

#### Scenario: Venue found by description keyword

- **WHEN** the query matches a keyword that appears only in a venue's notes/description
- **THEN** that venue is returned as a suggestion, ranked below name and code matches

### Requirement: Ranked, most-likely-first ordering

The system SHALL rank suggestions so that prefix and whole-word matches on names and codes appear before substring matches in descriptions.

#### Scenario: Name prefix outranks a description mention

- **WHEN** one result matches the query as a name prefix and another matches only inside its description
- **THEN** the name-prefix result is ordered before the description-only result

### Requirement: Cross-backend matching

The system SHALL perform case-insensitive matching that returns identical results on the local SQLite database and on PostgreSQL.

#### Scenario: Same results on either backend

- **WHEN** the same query runs against the SQLite dev database and the PostgreSQL production database with equivalent data
- **THEN** the set of matched venues and teams is the same

### Requirement: Header search UI with autocomplete

The system SHALL present a search box in the app header that autocompletes as the user types, with debounced requests and keyboard navigation, and that routes the selected suggestion into the existing views.

#### Scenario: Suggestions update while typing

- **WHEN** the user types in the search box
- **THEN** suggestions update after a short debounce, without a request per keystroke, and stale in-flight responses do not overwrite newer results

#### Scenario: Selecting a venue opens its detail

- **WHEN** the user selects a venue suggestion
- **THEN** the app opens that venue's detail view and the URL reflects the selection

#### Scenario: Selecting a team focuses the by-team view

- **WHEN** the user selects a team/country suggestion
- **THEN** the app switches to the by-team view with that team selected and the URL reflects the selection

#### Scenario: Keyboard navigation

- **WHEN** the suggestion list is open
- **THEN** the user can move the highlight with the arrow keys, choose with Enter, and dismiss with Escape

