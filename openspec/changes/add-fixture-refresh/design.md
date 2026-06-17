## Context

Reference data (teams + the 104-match fixture list) comes from FIFA's v3 calendar API via `fetchfixtures`, is loaded idempotently by `loadreferencedata --path` (upsert by `fifa_match_number`), and screening policies expand into concrete screenings via `ScreeningPolicy.materialize()`. The model was built for this: knockout matches exist before their teams do (nullable teams + placeholders + a stable `bracket_slot`), so resolving them is an in-place update, and `by_team` policies re-materialize to attach venues to newly-involving fixtures (PRD §8.4–8.6). What's missing is automation: nothing runs the chain as the bracket resolves.

## Goals / Non-Goals

**Goals:**
- Keep the live schedule correct as FIFA resolves the bracket, without manual steps.
- One idempotent command that fetches, loads, re-materializes, and logs.
- Fail safe: a bad or unavailable upstream never corrupts or empties the data.
- A visible "fixtures last refreshed" signal.

**Non-Goals:**
- Live scores / minute-by-minute updates (this is a finder, not live results).
- Re-committing `data/fifa_reference.json` on every refresh (the snapshot stays the deploy seed; the cron updates the running DB).
- Changing venue/affiliation/policy *content* — refresh only touches reference data + generated screenings.

## Decisions

**One command, `refreshfixtures`, chaining the existing idempotent pieces.** It calls the FIFA fetch+map, validates, upserts teams/matches, then re-materializes policies and logs a diff (newly-resolved fixtures, new screenings). Rationale: reuse the proven, idempotent paths; a single entry point is what cron invokes and what we test. Alternative: separate cron steps — rejected; a single transactional-ish command is easier to reason about and guard.

**Run on Render Cron.** The app already deploys on Render; a Cron Job sharing the web service's env/DB runs `refreshfixtures` on a schedule. Cadence: once daily during the group stage; a few times daily on knockout days (Jun 29 R32, Jul 9 QF, etc.) when the prior round's results resolve opponents. Rationale: matches the data's actual change rate; cheap. Alternative: in-process scheduler / Celery beat — rejected as heavier than warranted.

**Guardrails / fail-safe.** Before writing: validate against the Pydantic contract (already), and sanity-check the payload (e.g. plausible match count, all kickoffs parse). On fetch failure, HTTP error, or an implausible payload, the command logs and exits non-zero **without modifying data** — the last good state stands. Authored venue/affiliation/policy rows are never deleted; only generated screenings are rebuilt (the importer already does a clean rebuild of `is_generated` rows, which `refreshfixtures` reuses).

**Knockout resolution propagates automatically.** When FIFA fills in a knockout's teams, `loadreferencedata` updates the `Match` in place (same `fifa_match_number`/`bracket_slot`); re-materializing `by_team` policies then creates screenings for venues that follow a now-involved team. `all_matches` venues already covered it. So "team advances → its bar lights up for the next match" happens with no manual edit.

**Freshness signal.** Stamp a `fixtures_refreshed_at` (settings/singleton or a tiny model row) on each successful run and expose it (e.g. in `/api/meta/`), so the UI can show "fixtures updated <when>". Complements the existing per-record provenance / `needs_review`.

## Risks / Trade-offs

- **Undocumented FIFA endpoint drifts or blocks the cron** → fail-safe keeps existing data; alert on repeated failures (log + optional notification). The committed snapshot still serves fresh deploys.
- **Upstream returns subtly wrong data** (e.g. a shifted kickoff) → contract validation + sanity thresholds catch gross errors; subtle changes flow through (which is the point) but are logged so they're auditable.
- **Cron updates prod DB out of band from git** → intended; the snapshot is the seed, the DB is the source of truth at runtime. Document that a redeploy re-seeds from the snapshot (so periodically refreshing the committed snapshot, or having deploy run `refreshfixtures`, avoids a deploy reverting to older fixtures). Open question below.
- **Concurrent refresh + deploy seed** → both idempotent upserts by natural key; last writer wins harmlessly.

## Migration Plan

Additive. Ship `refreshfixtures` + a Render Cron entry. Backfill the freshness timestamp on first run. Rollback = remove the cron job; nothing else depends on it. No data migration beyond an optional timestamp field.

## Open Questions

- Should a deploy run `refreshfixtures` (live FIFA) in `build.sh`, or keep seeding from the committed snapshot and let cron catch up? (Leaning: seed from snapshot at deploy for determinism, cron for freshness; optionally refresh the committed snapshot on a slower cadence.)
- Exact cron cadence and whether to ramp automatically around known knockout dates.
- Failure alerting channel (log-only vs. email/Slack) if the FIFA fetch fails N times.
