## ADDED Requirements

### Requirement: Fetch authoritative fixtures from the FIFA API

The system SHALL provide a management command that retrieves the full FIFA 2026 fixture list from FIFA's v3 calendar API and writes a reference-data bundle to disk, using the season identifier as a documented, overridable default.

#### Scenario: Fetch writes a reference bundle

- **WHEN** the fetch command runs against the FIFA calendar endpoint for season 285023
- **THEN** it writes a `{teams, matches}` JSON file containing all 104 matches and every participating team

#### Scenario: Season is overridable

- **WHEN** the command is invoked with an explicit season identifier
- **THEN** it queries that season instead of the default

### Requirement: Map FIFA fields to the reference-data contract

The system SHALL map each FIFA match to the existing reference-data contract: match number, UTC kickoff, team codes (null for unresolved knockouts), stage, group, stadium, and placeholders.

#### Scenario: Resolved group match maps fully

- **WHEN** a First Stage match with both teams is mapped
- **THEN** it produces a match with `fifa_match_number` from `MatchNumber`, `stage` "group", a single-letter `group`, UTC `kickoff` from `Date`, and `home_team_code`/`away_team_code` from the teams' country codes

#### Scenario: Unresolved knockout maps to placeholders

- **WHEN** a knockout match with no assigned teams is mapped
- **THEN** it produces a match with null team codes, the FIFA placeholder text in `home_placeholder`/`away_placeholder`, the correct knockout `stage`, and a stable `bracket_slot`

#### Scenario: Team codes align with affiliations

- **WHEN** the teams are mapped
- **THEN** the FIFA 3-letter country codes are used as `fifa_code`, so existing venue affiliations (e.g. USA, Brazil, Croatia) resolve to the loaded teams

### Requirement: Offline snapshot is the canonical seed source

The system SHALL commit the fetched reference bundle so that routine seeding never requires a live call to the undocumented FIFA endpoint.

#### Scenario: Seeding works without network access

- **WHEN** `loadreferencedata --path` is run against the committed snapshot with no network available
- **THEN** the full teams + fixtures load succeeds

### Requirement: Reconcile provisional Gillette match numbers

The system SHALL replace the prior provisional Gillette match numbers with the authoritative FIFA numbers so that existing watch-party policies referencing specific matches remain correct.

#### Scenario: Specific policies retarget to real fixtures

- **WHEN** the authoritative fixtures are loaded and the watch-party data has been reconciled
- **THEN** each `specific` policy that previously referenced a provisional Gillette number references the corresponding real FIFA match number, and no provisional fixture remains in the reference seed

#### Scenario: No duplicate or corrupted Gillette fixtures

- **WHEN** the authoritative list is loaded after reconciliation
- **THEN** each of the seven Gillette matches exists exactly once, keyed by its real FIFA number, with the correct matchup and kickoff

### Requirement: Full-list load lights up every team

The system SHALL, after loading the authoritative fixtures and re-materializing policies, expose matches for every participating nation and make `by_team` supporter venues visible.

#### Scenario: A non-Gillette nation gains screenings

- **WHEN** the authoritative fixtures are loaded and policies re-materialized
- **THEN** a nation that does not play at Gillette (e.g. the USA, Brazil, or Croatia) has matches in the team "playing" query, and its `by_team` supporter venue has at least one materialized screening
