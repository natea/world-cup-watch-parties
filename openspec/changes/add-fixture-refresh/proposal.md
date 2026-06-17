## Why

The fixture list is only correct at the moment it's loaded. As the tournament progresses, FIFA fills in the bracket — Round-of-32 and Quarterfinal opponents resolve from placeholders ("Winner Group C") to real teams, kickoff times occasionally shift, and knockout matchups appear. Right now the data only updates when someone manually runs `fetchfixtures` + `loadreferencedata` and re-materializes policies. Without an automated refresh, the live site will show stale "TBD" matchups and miss newly-scheduled games once the group stage ends.

The building blocks already exist and are idempotent (`fetchfixtures` → FIFA API, `loadreferencedata --path` upserts by `fifa_match_number`, `ScreeningPolicy.materialize()`). This change wires them into a **scheduled, self-healing refresh** with guardrails so the schedule stays current automatically.

## What Changes

- Add a **`refreshfixtures` management command** that runs the full chain in one idempotent step: fetch the FIFA calendar API → validate → upsert teams/matches (resolving knockout placeholders into real teams in place) → re-materialize screening policies so `by_team` venues pick up newly-resolved fixtures → log a summary of what changed.
- Run it on a **schedule via a Render Cron Job** — daily during the group stage, and more frequently on knockout days (when results resolve the next round) — updating the live production database between deploys. (The committed `data/fifa_reference.json` remains the deploy-time seed.)
- **Data-integrity guardrails:** validate the payload against the Pydantic contract; abort and keep existing data if the fetch fails or the payload is implausible (e.g. not ~104 matches); never touch authored venue/affiliation data; only rebuild generated screenings.
- **Surface freshness:** record and expose a "fixtures last refreshed" timestamp (alongside the existing per-record provenance / `needs_review`).

## Capabilities

### New Capabilities
- `fixture-refresh`: a scheduled, idempotent, guarded refresh that keeps the fixture list (and the screenings derived from it) current as the bracket resolves, plus a visible last-updated signal.

### Modified Capabilities
<!-- Builds on the archived `fifa-fixtures` and `data-import` capabilities (fetch,
     upsert, materialize) without changing their requirements. -->

## Impact

- **New code:** `events/management/commands/refreshfixtures.py` (chains fetch + load + re-materialize with guardrails); a small "last refreshed" field/endpoint.
- **Ops:** a Render Cron Job entry in `render.yaml` running `refreshfixtures` on a schedule, sharing the web service's environment/DB.
- **External dependency:** the same undocumented FIFA v3 calendar endpoint used by `fetchfixtures` — called on a schedule; failures are non-fatal (existing data is retained).
- **No schema changes** beyond an optional timestamp; reuses the idempotent upsert + materialization paths.
- **Tests:** the refresh chain resolves a placeholder knockout into real teams and re-materializes its `by_team` screenings; a failed/implausible fetch leaves existing data intact.
