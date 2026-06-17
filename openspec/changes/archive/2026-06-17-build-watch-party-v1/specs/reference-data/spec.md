## ADDED Requirements

### Requirement: Authoritative reference-data load

The system SHALL load teams and the canonical FIFA fixture list from an authoritative structured source via a dedicated management command, separate from any LLM-extracted data.

#### Scenario: Load teams and fixtures

- **WHEN** the reference-data load command runs against a structured teams + fixtures source
- **THEN** `Team` rows are upserted by `fifa_code` and `Match` rows are upserted by `fifa_match_number`, with kickoff times stored timezone-aware in UTC

#### Scenario: Reference data is not LLM-derived

- **WHEN** the reference-data command runs
- **THEN** it reads only structured inputs and never invokes an LLM extractor, so kickoff times and matchups cannot be fabricated

### Requirement: Knockout fixtures before teams resolve

The system SHALL represent knockout fixtures whose opponents are not yet known, using nullable team references, placeholder labels, and a stable bracket slot.

#### Scenario: Unresolved knockout fixture loads

- **WHEN** a Round of 32 or Quarterfinal fixture with no assigned opponents is loaded
- **THEN** the `Match` is created with null `home_team`/`away_team`, populated `home_placeholder`/`away_placeholder` (e.g. "Winner Group C"), and a stable `bracket_slot`

#### Scenario: Re-running the load is idempotent

- **WHEN** the reference-data load command is run again
- **THEN** existing teams and matches are updated in place by their natural keys and no duplicates are created
