"""Task 2.4 — reference-data load is idempotent and handles unresolved knockouts."""
import pytest
from django.core.management import call_command

from events.models import Match, Team


@pytest.mark.django_db
def test_load_is_idempotent():
    call_command("loadreferencedata", builtin=True)
    teams_after_first = Team.objects.count()
    matches_after_first = Match.objects.count()

    call_command("loadreferencedata", builtin=True)  # re-run
    assert Team.objects.count() == teams_after_first
    assert Match.objects.count() == matches_after_first


@pytest.mark.django_db
def test_unresolved_knockout_fixture():
    call_command("loadreferencedata", builtin=True)
    r32 = Match.objects.get(fifa_match_number=88)
    assert r32.home_team is None and r32.away_team is None
    assert r32.home_placeholder == "Winner Group C"
    assert r32.bracket_slot == "R32-3"
    assert r32.is_resolved is False
    assert r32.label == "Winner Group C vs Runner-up Group I"


@pytest.mark.django_db
def test_kickoffs_are_timezone_aware():
    call_command("loadreferencedata", builtin=True)
    for m in Match.objects.all():
        assert m.kickoff.tzinfo is not None


@pytest.mark.django_db
def test_shared_no_downgrade_guard_protects_seed_loader():
    """The no-downgrade guard lives in the shared upsert, so even a re-seed from
    a stale source can't revert an already-resolved knockout to placeholders."""
    from events.import_contract import MatchIn, TeamIn
    from events.management.commands.loadreferencedata import upsert_matches, upsert_teams

    teams = [TeamIn.model_validate({"name": "Argentina", "fifa_code": "ARG"}),
             TeamIn.model_validate({"name": "Brazil", "fifa_code": "BRA"})]
    by_code = upsert_teams(teams)

    resolved = MatchIn.model_validate({
        "fifa_match_number": 73, "stage": "r32", "kickoff": "2026-06-28T20:00:00Z",
        "home_team_code": "ARG", "away_team_code": "BRA", "bracket_slot": "r32-73",
    })
    upsert_matches([resolved], by_code)
    assert Match.objects.get(fifa_match_number=73).is_resolved

    stale = MatchIn.model_validate({
        "fifa_match_number": 73, "stage": "r32", "kickoff": "2026-06-28T20:00:00Z",
        "home_placeholder": "W1", "away_placeholder": "W2", "bracket_slot": "r32-73",
    })
    result = upsert_matches([stale], by_code)
    m = Match.objects.get(fifa_match_number=73)
    assert m.is_resolved and m.home_team.fifa_code == "ARG"
    assert result["newly_resolved"] == []
