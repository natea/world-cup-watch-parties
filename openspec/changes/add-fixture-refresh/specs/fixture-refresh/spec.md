## ADDED Requirements

### Requirement: Idempotent scheduled refresh command

The system SHALL provide a single command that fetches the authoritative fixtures, upserts reference data, re-materializes screening policies, and logs a summary — safe to run repeatedly.

#### Scenario: Refresh updates fixtures and screenings

- **WHEN** the refresh command runs against the FIFA calendar API
- **THEN** teams and matches are upserted by their natural keys, screening policies are re-materialized, and a summary of changes (e.g. newly-resolved fixtures, screenings created) is logged

#### Scenario: Repeated runs are stable

- **WHEN** the refresh command runs twice with no upstream change
- **THEN** the second run makes no net change to fixtures or screenings

### Requirement: Knockout resolution propagates to screenings

The system SHALL, when a knockout fixture's opponents become known upstream, update that match in place and create screenings for venues that follow a now-involved team.

#### Scenario: A resolved team's supporter bar lights up

- **WHEN** a knockout match that previously had placeholder opponents resolves to include a real team, and the refresh runs
- **THEN** the match's teams are filled in (same fixture number / bracket slot) and that team's `by_team` supporter venues gain screenings for the match without manual edits

### Requirement: Fail-safe on unavailable or implausible data

The system SHALL leave the existing data unchanged when the upstream fetch fails or returns an implausible payload, rather than corrupting or emptying the schedule.

#### Scenario: Upstream unavailable

- **WHEN** the FIFA fetch fails (network/HTTP error) during a refresh
- **THEN** the command exits without modifying any data and reports the failure

#### Scenario: Implausible payload rejected

- **WHEN** the fetched payload fails contract validation or a sanity check (e.g. an unexpected match count)
- **THEN** the refresh aborts and the previously loaded fixtures remain intact

#### Scenario: Authored data is never destroyed

- **WHEN** a refresh runs
- **THEN** venues, affiliations, and policies (authored data) are left untouched; only reference data and generated screenings are updated

### Requirement: Visible fixture freshness

The system SHALL record the time of the last successful refresh and expose it so the client can show when fixtures were last updated.

#### Scenario: Last-updated is available

- **WHEN** a refresh completes successfully
- **THEN** a "fixtures last refreshed" timestamp is recorded and retrievable by the client

### Requirement: Scheduled execution

The system SHALL run the refresh on a schedule in production so the fixture list stays current without manual intervention.

#### Scenario: Scheduled run keeps the live schedule current

- **WHEN** the scheduled job runs during the tournament
- **THEN** the live database reflects the latest FIFA fixtures and the screenings derived from them
