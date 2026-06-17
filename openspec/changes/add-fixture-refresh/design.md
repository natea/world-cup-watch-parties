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

**Run on Render Cron, every 6 hours, one fixed schedule.** The app already deploys on Render; a Cron Job sharing the web service's env/DB runs `refreshfixtures` every 6 hours throughout the tournament. Rationale: the refresh is a cheap API call + idempotent upsert, every-6h keeps the data within a few hours of fresh, and a single fixed schedule avoids date-based ramp logic — a "where to watch" finder doesn't need minute-fresh matchups (people plan ahead; this isn't live scores). Alternatives considered: per-phase ramping / hourly on knockout days (more moving parts than warranted — can tighten later if desired); in-process scheduler / Celery beat (heavier than warranted).

**Deploy seeds from the committed snapshot, then runs a fail-safe live refresh.** `build.sh` keeps seeding from `data/fifa_reference.json` (deterministic, offline-safe — a FIFA outage can never block a deploy), then runs `refreshfixtures` immediately after as a fail-safe step. When FIFA is reachable the deploy ends fully fresh; when it isn't, the snapshot stands. Cron then keeps it fresh between deploys. Rationale: determinism + freshness without making deploys depend on an undocumented upstream. Alternative: live-fetch as the only seed — rejected (a FIFA outage would fail or empty a deploy).

**Resolved fixtures are never downgraded (no-downgrade guard).** The upsert MUST NOT replace a match's already-resolved teams with placeholders. This makes the snapshot-vs-live question moot: re-seeding from a stale snapshot (at deploy) can never un-resolve a knockout that cron already filled in. It also protects against an upstream blip that momentarily drops team data. (Genuine corrections — a real team→different real team, a kickoff change — still flow through; only resolved→placeholder regressions are blocked.)

**Guardrails / fail-safe.** Before writing: validate against the Pydantic contract (already), and sanity-check the payload (e.g. plausible match count, all kickoffs parse). On fetch failure, HTTP error, or an implausible payload, the command logs a warning and **leaves existing data untouched**. Authored venue/affiliation/policy rows are never deleted; only generated screenings are rebuilt (the importer already does a clean rebuild of `is_generated` rows, which `refreshfixtures` reuses).

**Knockout resolution propagates automatically.** When FIFA fills in a knockout's teams, `loadreferencedata` updates the `Match` in place (same `fifa_match_number`/`bracket_slot`); re-materializing `by_team` policies then creates screenings for venues that follow a now-involved team. `all_matches` venues already covered it. So "team advances → its bar lights up for the next match" happens with no manual edit.

**Freshness signal, doubling as the alert trigger.** Stamp a `fixtures_refreshed_at` on each successful run and expose it (e.g. in `/api/meta/`) so the UI can show "fixtures updated <when>". The same timestamp drives **staleness-based alerting**: an individual failed fetch is a non-event (data retained, logged), but if a run can't refresh **and** the last success was more than 24h ago, the command escalates (alert + non-zero exit). This avoids alert noise from transient FIFA hiccups while still flagging genuinely stale data. Channel: a Slack webhook (tooling already on hand) or email — whichever is one line of config.

## Risks / Trade-offs

- **Undocumented FIFA endpoint drifts or blocks the cron** → fail-safe keeps existing data; alert on repeated failures (log + optional notification). The committed snapshot still serves fresh deploys.
- **Upstream returns subtly wrong data** (e.g. a shifted kickoff) → contract validation + sanity thresholds catch gross errors; subtle changes flow through (which is the point) but are logged so they're auditable.
- **Cron updates prod DB out of band from git** → intended; the snapshot is the deploy seed, the DB is the runtime source of truth. The no-downgrade guard + the fail-safe `refreshfixtures` step in `build.sh` mean a redeploy can't revert resolved fixtures, so the committed snapshot can lag without harm (refresh it occasionally via `fetchfixtures` for a good cold-start baseline).
- **Concurrent refresh + deploy seed** → both idempotent upserts by natural key; last writer wins harmlessly, and the no-downgrade guard prevents a stale writer from regressing resolved data.

## Migration Plan

Additive. Ship `refreshfixtures` + the `build.sh` fail-safe refresh step + a Render Cron entry (every 6h). Backfill the freshness timestamp on first run. Rollback = remove the cron job and the `build.sh` line; nothing else depends on it. No data migration beyond a small timestamp.

## Resolved Decisions

- **Deploy seeding:** committed snapshot at deploy + a fail-safe live `refreshfixtures` step in `build.sh`; cron for ongoing freshness. The no-downgrade guard makes a stale snapshot harmless.
- **Cron cadence:** every 6 hours, one fixed schedule (no per-phase ramp); tighten to hourly during knockouts only if a need appears.
- **Failure alerting:** log every run; escalate (alert + non-zero exit) only when no successful refresh in >24h, derived from `fixtures_refreshed_at`. Channel: Slack webhook or email.
