"""Tests for the add-fixture-refresh change (task 5).

All FIFA access is mocked via the `fetch_raw` seam — NO live network.
Covers: no-downgrade guard, resolve propagation to by_team screenings,
fail-safe on bad fetch/implausible payload, idempotent re-run, and
staleness-based escalation.
"""
from __future__ import annotations

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

import events.management.commands.refreshfixtures as refreshmod
from events.models import (
    CostType,
    Match,
    PolicyType,
    RefreshState,
    Screening,
    ScreeningPolicy,
    Team,
    Venue,
)

STAGE_FIRST = [{"Locale": "en-GB", "Description": "First Stage"}]
STAGE_R32 = [{"Locale": "en-GB", "Description": "Round of 32"}]


def _team(code, name):
    return {"IdCountry": code, "TeamName": [{"Locale": "en-GB", "Description": name}]}


def _group_match(number, group, home, away, date="2026-06-14T01:00:00Z"):
    return {
        "MatchNumber": number,
        "Date": date,
        "StageName": STAGE_FIRST,
        "GroupName": [{"Locale": "en-GB", "Description": f"Group {group}"}],
        "Stadium": {
            "Name": [{"Locale": "en-GB", "Description": "Some Stadium"}],
            "CityName": [{"Locale": "en-GB", "Description": "Somewhere"}],
        },
        "Home": _team(*home),
        "Away": _team(*away),
        "PlaceHolderA": None,
        "PlaceHolderB": None,
    }


def _knockout(number, home=None, away=None, ph_a="2A", ph_b="2B",
              date="2026-06-28T20:00:00Z"):
    return {
        "MatchNumber": number,
        "Date": date,
        "StageName": STAGE_R32,
        "GroupName": [],
        "Stadium": {
            "Name": [{"Locale": "en-GB", "Description": "Knockout Stadium"}],
            "CityName": [{"Locale": "en-GB", "Description": "Elsewhere"}],
        },
        "Home": _team(*home) if home else None,
        "Away": _team(*away) if away else None,
        "PlaceHolderA": None if home else ph_a,
        "PlaceHolderB": None if away else ph_b,
    }


def _payload(results):
    return {"Results": results}


def _make_plausible(results):
    """Pad with filler group matches so the payload clears MIN_PLAUSIBLE_MATCHES."""
    base = list(results)
    used = {r["MatchNumber"] for r in base}
    n = 100
    while len(base) < refreshmod.MIN_PLAUSIBLE_MATCHES + 1:
        while n in used:
            n += 1
        used.add(n)
        base.append(_group_match(n, "Z", ("AAA", "Team A"), ("BBB", "Team B")))
        n += 1
    return _payload(base)


def _patch_fetch(monkeypatch, payload_or_exc):
    def fake(season=None):
        if isinstance(payload_or_exc, Exception):
            raise payload_or_exc
        return payload_or_exc
    monkeypatch.setattr(refreshmod, "fetch_raw", fake)


# --- no-downgrade guard -----------------------------------------------------
@pytest.mark.django_db
def test_no_downgrade_stale_placeholder_does_not_revert_resolved(monkeypatch):
    # First refresh: knockout 73 is resolved to ARG vs BRA.
    resolved = _knockout(73, home=("ARG", "Argentina"), away=("BRA", "Brazil"))
    _patch_fetch(monkeypatch, _make_plausible([resolved]))
    call_command("refreshfixtures")
    m = Match.objects.get(fifa_match_number=73)
    assert m.is_resolved and m.home_team.fifa_code == "ARG"

    # Stale source: same fixture, back to placeholders. Must NOT revert.
    stale = _knockout(73, home=None, away=None, ph_a="W1", ph_b="W2")
    _patch_fetch(monkeypatch, _make_plausible([stale]))
    call_command("refreshfixtures")
    m.refresh_from_db()
    assert m.is_resolved, "resolved knockout was downgraded to placeholders"
    assert m.home_team.fifa_code == "ARG" and m.away_team.fifa_code == "BRA"


@pytest.mark.django_db
def test_resolved_to_different_resolved_correction_applies(monkeypatch):
    _patch_fetch(monkeypatch, _make_plausible(
        [_knockout(73, home=("ARG", "Argentina"), away=("BRA", "Brazil"))]))
    call_command("refreshfixtures")

    # Correction: away team changes to a different real team.
    _patch_fetch(monkeypatch, _make_plausible(
        [_knockout(73, home=("ARG", "Argentina"), away=("FRA", "France"))]))
    call_command("refreshfixtures")
    m = Match.objects.get(fifa_match_number=73)
    assert m.away_team.fifa_code == "FRA"


@pytest.mark.django_db
def test_kickoff_change_applies(monkeypatch):
    _patch_fetch(monkeypatch, _make_plausible(
        [_knockout(73, home=("ARG", "Argentina"), away=("BRA", "Brazil"),
                   date="2026-06-28T20:00:00Z")]))
    call_command("refreshfixtures")

    _patch_fetch(monkeypatch, _make_plausible(
        [_knockout(73, home=("ARG", "Argentina"), away=("BRA", "Brazil"),
                   date="2026-06-28T23:30:00Z")]))
    call_command("refreshfixtures")
    m = Match.objects.get(fifa_match_number=73)
    assert m.kickoff.hour == 23 and m.kickoff.minute == 30


# --- resolve propagation to by_team screenings ------------------------------
@pytest.mark.django_db
def test_resolved_knockout_lights_up_by_team_venue(monkeypatch):
    arg = Team.objects.create(name="Argentina", fifa_code="ARG")
    venue = Venue.objects.create(name="Argentina Bar", city="Boston", venue_type="bar")
    policy = ScreeningPolicy.objects.create(
        venue=venue, policy_type=PolicyType.BY_TEAM, default_cost_type=CostType.FREE_OPEN
    )
    policy.teams.add(arg)

    # Initially the knockout has placeholders → no ARG screening.
    _patch_fetch(monkeypatch, _make_plausible([_knockout(73, home=None, away=None)]))
    call_command("refreshfixtures")
    assert not Screening.objects.filter(venue=venue, match__fifa_match_number=73).exists()

    # Knockout resolves to include ARG → the by_team venue gains a screening.
    _patch_fetch(monkeypatch, _make_plausible(
        [_knockout(73, home=("ARG", "Argentina"), away=("BRA", "Brazil"))]))
    call_command("refreshfixtures")
    m = Match.objects.get(fifa_match_number=73)
    assert m.is_resolved
    assert Screening.objects.filter(
        venue=venue, match=m, is_generated=True).exists()


# --- fail-safe --------------------------------------------------------------
@pytest.mark.django_db
def test_failed_fetch_leaves_data_intact(monkeypatch):
    _patch_fetch(monkeypatch, _make_plausible(
        [_knockout(73, home=("ARG", "Argentina"), away=("BRA", "Brazil"))]))
    call_command("refreshfixtures")
    before = Match.objects.get(fifa_match_number=73)
    stamp = RefreshState.get().fixtures_refreshed_at
    n_matches = Match.objects.count()

    # Network failure (recent success → quiet, exit 0).
    _patch_fetch(monkeypatch, ConnectionError("FIFA down"))
    call_command("refreshfixtures")

    assert Match.objects.count() == n_matches
    after = Match.objects.get(fifa_match_number=73)
    assert after.home_team.fifa_code == "ARG" and after.is_resolved
    # Freshness stamp unchanged on failure.
    assert RefreshState.get().fixtures_refreshed_at == stamp


@pytest.mark.django_db
def test_implausible_payload_rejected(monkeypatch):
    _patch_fetch(monkeypatch, _make_plausible(
        [_knockout(73, home=("ARG", "Argentina"), away=("BRA", "Brazil"))]))
    call_command("refreshfixtures")
    n_matches = Match.objects.count()

    # Too few matches → implausible, recent success → quiet retain.
    _patch_fetch(monkeypatch, _payload(
        [_group_match(1, "A", ("USA", "United States"), ("MEX", "Mexico"))]))
    call_command("refreshfixtures")
    assert Match.objects.count() == n_matches


@pytest.mark.django_db
def test_idempotent_rerun_is_noop(monkeypatch):
    arg = Team.objects.create(name="Argentina", fifa_code="ARG")
    venue = Venue.objects.create(name="Argentina Bar", city="Boston", venue_type="bar")
    policy = ScreeningPolicy.objects.create(
        venue=venue, policy_type=PolicyType.BY_TEAM)
    policy.teams.add(arg)

    payload = _make_plausible(
        [_knockout(73, home=("ARG", "Argentina"), away=("BRA", "Brazil"))])
    _patch_fetch(monkeypatch, payload)
    call_command("refreshfixtures")
    matches, screenings = Match.objects.count(), Screening.objects.count()

    call_command("refreshfixtures")  # re-run, no upstream change
    assert Match.objects.count() == matches
    assert Screening.objects.count() == screenings


# --- staleness alerting -----------------------------------------------------
@pytest.mark.django_db
def test_no_prior_success_and_failed_fetch_escalates(monkeypatch):
    assert RefreshState.get().fixtures_refreshed_at is None
    _patch_fetch(monkeypatch, ConnectionError("FIFA down"))
    with pytest.raises(CommandError):
        call_command("refreshfixtures")


@pytest.mark.django_db
def test_stale_prior_success_and_failed_fetch_escalates(monkeypatch):
    state = RefreshState.get()
    state.fixtures_refreshed_at = timezone.now() - timezone.timedelta(hours=30)
    state.save()
    _patch_fetch(monkeypatch, ConnectionError("FIFA down"))
    with pytest.raises(CommandError):
        call_command("refreshfixtures")


@pytest.mark.django_db
def test_recent_success_and_failed_fetch_exits_cleanly(monkeypatch):
    state = RefreshState.get()
    state.fixtures_refreshed_at = timezone.now() - timezone.timedelta(hours=1)
    state.save()
    _patch_fetch(monkeypatch, ConnectionError("FIFA down"))
    call_command("refreshfixtures")  # no raise
