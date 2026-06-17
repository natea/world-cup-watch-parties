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

# Fail-safe live refresh AFTER the snapshot seed: when FIFA is reachable the
# deploy ends fully fresh; when it isn't, the no-downgrade guard + `|| true`
# mean a FIFA outage can never fail or regress a deploy (the snapshot stands).
uv run python manage.py refreshfixtures || true
