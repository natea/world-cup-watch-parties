## 1. Refresh command

- [ ] 1.1 Add `events/management/commands/refreshfixtures.py` chaining: fetch FIFA API → validate (contract + sanity thresholds) → upsert teams/matches → re-materialize policies → log a change summary
- [ ] 1.2 Reuse the existing idempotent paths (`fetchfixtures` mapping, `loadreferencedata` upsert, clean rebuild of `is_generated` screenings + `ScreeningPolicy.materialize()`)
- [ ] 1.3 Fail-safe: on fetch failure or implausible payload, abort with a non-zero exit and **no** data mutation; never delete authored venue/affiliation/policy rows

## 2. Freshness signal

- [ ] 2.1 Record `fixtures_refreshed_at` on each successful run (settings singleton or a small model row)
- [ ] 2.2 Expose it (e.g. via `/api/meta/`) and show "fixtures updated <when>" in the client

## 3. Scheduling

- [ ] 3.1 Add a Render Cron Job in `render.yaml` running `refreshfixtures`, sharing the web service env/DB; daily cadence with extra runs on knockout days
- [ ] 3.2 Decide deploy behavior: seed from the committed snapshot at deploy vs. refresh live (see design open question); document it

## 4. Tests & docs

- [ ] 4.1 Test: a placeholder knockout that resolves to a real team gets its teams filled in and its `by_team` venues gain screenings after refresh
- [ ] 4.2 Test: failed fetch / implausible payload leaves existing fixtures and screenings intact; idempotent re-run is a no-op
- [ ] 4.3 README/ops note: the refresh command, the cron schedule, the FIFA dependency + fail-safe behavior, and the freshness indicator
