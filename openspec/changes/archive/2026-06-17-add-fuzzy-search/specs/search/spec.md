## ADDED Requirements

### Requirement: Common-name aliases for teams

The system SHALL resolve common everyday team names to teams whose official FIFA name differs, so that a query using the familiar name returns the team even when it shares no characters with the official name.

#### Scenario: Official short name found by common name

- **WHEN** the query is a common name for a team whose FIFA name is an official short form (e.g. "united states" for "USA", "turkey" for "Türkiye", "ivory coast" for "Côte d'Ivoire", "south korea" for "Korea Republic")
- **THEN** a team suggestion for that team is returned, ranked alongside name/code matches

#### Scenario: Alias prefix while typing

- **WHEN** the query is a prefix of an alias (e.g. "united")
- **THEN** the aliased team is suggested

### Requirement: Typo-tolerant fuzzy fallback

The system SHALL apply a fuzzy similarity fallback for queries at or above a minimum length, returning close-but-inexact matches on venue names, team names and aliases, and supporter-hub names, ranked below all exact and substring matches.

#### Scenario: Misspelled team or venue still matches

- **WHEN** the query is a near-miss of a team or venue name (e.g. "croatica" for "Croatia", "banshe" for "The Banshee")
- **THEN** the intended result is returned, ordered after exact and substring matches

#### Scenario: Misspelled supporter club still matches its venues

- **WHEN** the query is a near-miss of a supporter-hub club name (e.g. "liverpol")
- **THEN** the venues affiliated with that club are returned

#### Scenario: Very short queries do not trigger fuzzy noise

- **WHEN** the query is shorter than the fuzzy minimum length
- **THEN** no fuzzy matches are produced (only exact/substring matches apply)
