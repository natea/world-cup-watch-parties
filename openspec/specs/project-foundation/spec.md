# project-foundation Specification

## Purpose
TBD - created by archiving change build-watch-party-v1. Update Purpose after archive.
## Requirements
### Requirement: Runnable Django project

The system SHALL provide a Django project that boots, runs migrations, and serves an `events` app containing the relocated prototype models, extraction contract, and importer.

#### Scenario: Project boots and migrates

- **WHEN** a developer installs dependencies and runs the project's migrate command on a fresh database
- **THEN** all migrations apply cleanly and the development server starts without error

#### Scenario: Prototype models are the app's models

- **WHEN** the `events` app is loaded
- **THEN** the `Team`, `Match`, `Venue`, `VenueAffiliation`, `Screening`, `ScreeningPolicy` models from the prototype `models.py` are registered as app models with their querysets and constraints intact

### Requirement: Database configuration

The system SHALL target PostgreSQL for production and SHALL permit SQLite for local development, with database credentials supplied via environment configuration rather than hardcoded.

#### Scenario: PostgreSQL family-friendly predicate

- **WHEN** the project runs against PostgreSQL
- **THEN** the database-level `family_friendly` queryset filter executes via the `Case/When` annotation

#### Scenario: SQLite fallback

- **WHEN** the project runs against SQLite for local development
- **THEN** the application still functions, using the per-row Python `is_family_friendly` predicate where the DB-level filter is unsupported

### Requirement: Django admin for data review

The system SHALL register the core entities in the Django admin so a reviewer can correct records flagged with `needs_review`.

#### Scenario: Reviewer corrects a flagged venue

- **WHEN** a reviewer opens the admin and filters venues by `needs_review = true`
- **THEN** the flagged venues are listed and editable, and clearing the flag and saving persists the correction

