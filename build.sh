#!/usr/bin/env bash
# Render build step for the Django API. Run from the repo root.
set -o errexit

# Install locked deps + the PostgreSQL driver (Render provides DATABASE_URL).
uv sync --frozen --extra postgres

# Collect static assets (Django admin + DRF browsable API) for WhiteNoise.
uv run python manage.py collectstatic --no-input

# Apply migrations, then seed reference data + watch parties.
# loadreferencedata defaults to the committed authoritative FIFA fixture
# snapshot (data/fifa_reference.json — all 104 matches / 48 teams). Both loaders
# are idempotent (upsert by natural key), so re-running on every deploy is safe.
uv run python manage.py migrate
uv run python manage.py loadreferencedata --path data/fifa_reference.json
uv run python manage.py importwatchparties data/watch_parties.json
