# data-import Specification

## Purpose
TBD - created by archiving change build-watch-party-v1. Update Purpose after archive.
## Requirements
### Requirement: Validated, idempotent import

The system SHALL provide a management command that loads a JSON payload validated against the Pydantic import contract and upserts every record by its natural key.

#### Scenario: Import the seed payload

- **WHEN** the import command runs against `sample_data.json`
- **THEN** the payload is validated against the Pydantic schema and venues (by `slug`), affiliations, screenings (by venue+match+`starts_at`), and policies are upserted into the database

#### Scenario: Invalid payload is rejected before touching the database

- **WHEN** a payload fails Pydantic validation
- **THEN** the command aborts with a validation error and writes nothing to the database

#### Scenario: Re-running import does not duplicate

- **WHEN** the import command is run twice on the same payload
- **THEN** the second run updates rows in place and the row counts are unchanged

### Requirement: Policy materialization completes the import

The system SHALL materialize screening policies into concrete `Screening` rows at the end of the import, flagging generated screenings.

#### Scenario: "Shows every match" fans out

- **WHEN** a venue has an `all_matches` policy and the import finishes
- **THEN** one generated `Screening` per match is created for that venue with `is_generated = true`

#### Scenario: Re-materialize after bracket resolves

- **WHEN** a knockout fixture's teams are filled in and materialization is re-run
- **THEN** `by_team` policies pick up the newly involving fixtures and create the missing screenings without duplicating existing ones

### Requirement: Provenance on every imported record

The system SHALL persist source provenance and a `needs_review` flag on imported venues and screenings.

#### Scenario: Provenance is preserved

- **WHEN** a record carrying `source`/`source_url`/`needs_review` is imported
- **THEN** those fields are stored on the row and are retrievable for display and review

