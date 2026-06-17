"""
Scheduled, idempotent, self-healing fixture refresh.

Chains the existing proven pieces in one transactional, guarded step:

    fetch FIFA calendar API  (fetchfixtures.fetch_raw)
      -> map + contract-validate  (fetchfixtures.build_bundle)
      -> sanity-check the payload  (plausible match count)
      -> upsert teams/matches  (loadreferencedata.upsert_*, no-downgrade guard)
      -> re-materialize ALL ScreeningPolicy rows  (by_team picks up new fixtures)
      -> stamp fixtures_refreshed_at + log a one-line change summary

Designed for a Render Cron Job (every 6h) and as the fail-safe step in build.sh.

Fail-safe semantics
-------------------
On ANY fetch failure / HTTP error / implausible payload the command leaves ALL
data untouched (no partial writes — the upsert + re-materialize run inside one
transaction) and logs a warning. Authored venue/affiliation/policy rows are
never deleted; only generated (`is_generated`) screenings are rebuilt by
re-materialize.

Staleness alerting
------------------
A single failed run is a quiet non-event (log warning, retain data, exit 0).
But if a run can't refresh AND the last successful refresh was more than 24h ago
(or never), it escalates: a clearly-marked log.error ALERT line + a non-zero
exit (CommandError). This avoids alert noise from transient FIFA hiccups while
surfacing genuinely stale data.

The FIFA network access goes through fetchfixtures.fetch_raw, so tests can
monkeypatch the seam with no live network.
"""
from __future__ import annotations

import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from events.import_contract import MatchIn, TeamIn
from events.management.commands.fetchfixtures import DEFAULT_SEASON, build_bundle, fetch_raw
from events.management.commands.loadreferencedata import upsert_matches, upsert_teams
from events.models import RefreshState, ScreeningPolicy

logger = logging.getLogger(__name__)

# A plausible World Cup 2026 calendar has 104 matches; require a clear floor so
# a truncated/garbage payload can never overwrite the schedule.
MIN_PLAUSIBLE_MATCHES = 64

# How long the data may go un-refreshed before a failed run escalates to an alert.
STALENESS_THRESHOLD = timezone.timedelta(hours=24)


class Command(BaseCommand):
    help = "Fetch the FIFA calendar, upsert fixtures (no-downgrade), re-materialize policies."

    def add_arguments(self, parser):
        parser.add_argument(
            "--season", default=DEFAULT_SEASON, help="FIFA idSeason (default: 2026)."
        )

    def handle(self, *args, **opts):
        state = RefreshState.get()

        # --- fetch + map + validate + sanity-check (no writes yet) ---
        try:
            raw = fetch_raw(opts["season"])
            bundle = build_bundle(raw)  # contract-validated dicts
            teams = [TeamIn.model_validate(t) for t in bundle["teams"]]
            matches = [MatchIn.model_validate(m) for m in bundle["matches"]]
            if len(matches) < MIN_PLAUSIBLE_MATCHES:
                raise ValueError(
                    f"implausible match count {len(matches)} "
                    f"(< {MIN_PLAUSIBLE_MATCHES}); refusing to overwrite fixtures"
                )
        except Exception as exc:
            # Fail-safe: leave ALL data untouched. Decide quiet-vs-alert by staleness.
            self._handle_failure(state, exc)
            return

        # --- write: upsert + re-materialize, all-or-nothing ---
        with transaction.atomic():
            team_by_code = upsert_teams(teams)
            result = upsert_matches(matches, team_by_code)
            screenings_created = 0
            for policy in ScreeningPolicy.objects.all():
                screenings_created += policy.materialize()
            state.fixtures_refreshed_at = timezone.now()
            state.save(update_fields=["fixtures_refreshed_at"])

        summary = (
            f"refreshfixtures OK: {result['count']} matches upserted, "
            f"{len(result['newly_resolved'])} newly-resolved fixtures, "
            f"{screenings_created} screenings created."
        )
        logger.info(summary)
        self.stdout.write(self.style.SUCCESS(summary))

    def _handle_failure(self, state: RefreshState, exc: Exception):
        last = state.fixtures_refreshed_at
        stale = last is None or (timezone.now() - last) > STALENESS_THRESHOLD

        if stale:
            last_desc = last.isoformat() if last else "never"
            # ALERT channel: a single, clearly-marked log.error line. A real
            # Slack/email webhook is out of scope for this change.
            # TODO(alerting): wire this ALERT line to a Slack webhook or email
            #   (one line of config); intentionally no network call / new dep here.
            logger.error(
                "ALERT refreshfixtures: fixtures stale — no successful refresh "
                "since %s and this run failed: %s",
                last_desc,
                exc,
            )
            raise CommandError(
                f"Fixture refresh failed and data is stale (last success: {last_desc}): {exc}"
            )

        # Transient failure within the freshness window: quiet, retain data, exit 0.
        msg = f"refreshfixtures: fetch failed, data left unchanged (recent success retained): {exc}"
        logger.warning(msg)
        self.stdout.write(self.style.WARNING(msg))
