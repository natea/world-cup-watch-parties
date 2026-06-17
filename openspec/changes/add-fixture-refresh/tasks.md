## 1. Refresh command

- [x] 1.1 Add `events/management/commands/refreshfixtures.py` chaining: fetch FIFA API → validate (contract + sanity thresholds) → upsert teams/matches → re-materialize policies → log a change summary
- [x] 1.2 Reuse the existing idempotent paths (`fetchfixtures` mapping, `loadreferencedata` upsert, clean rebuild of `is_generated` screenings + `ScreeningPolicy.materialize()`)
- [x] 1.3 Fail-safe: on fetch failure or implausible payload, log and leave all data unmodified; never delete authored venue/affiliation/policy rows

## 2. No-downgrade guard

- [x] 2.1 In the match upsert, never overwrite resolved `home_team`/`away_team` with null/placeholder values (only resolved→resolved corrections and time changes apply); apply in the shared upsert so it protects both the seed and the refresh
- [x] 2.2 Test: a stale source with placeholders does not revert an already-resolved knockout; a real team→team correction still applies

## 3. Freshness + staleness alerting

- [x] 3.1 Record `fixtures_refreshed_at` on each successful run (settings singleton or a small model row); expose via `/api/meta/` and show "fixtures updated <when>" in the client
- [x] 3.2 Staleness alerting: log routine failures quietly; when a run can't refresh AND last success > 24h ago, escalate (alert + non-zero exit). Channel: Slack webhook or email (one-line config)

## 4. Scheduling & deploy

- [x] 4.1 Add a Render Cron Job in `render.yaml` running `refreshfixtures` every 6 hours, sharing the web service env/DB
- [x] 4.2 In `build.sh`, after the snapshot seed, run `refreshfixtures` as a fail-safe step (deploy ends fresh when FIFA is up; snapshot fallback when down)

## 5. Tests & docs

- [x] 5.1 Test: a placeholder knockout that resolves to a real team gets its teams filled in and its `by_team` venues gain screenings after refresh
- [x] 5.2 Test: failed fetch / implausible payload leaves existing fixtures and screenings intact; idempotent re-run is a no-op
- [x] 5.3 README/ops note: the refresh command, the every-6h cron, the deploy fail-safe step, the FIFA dependency + fail-safe behavior, the no-downgrade guard, and the freshness/staleness-alert behavior
