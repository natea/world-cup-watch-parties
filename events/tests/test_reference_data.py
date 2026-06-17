"""Task 2.4 — reference-data load is idempotent and handles unresolved knockouts."""
import pytest
from django.core.management import call_command

from events.models import Match, Team


@pytest.mark.django_db
def test_load_is_idempotent():
    call_command("loadreferencedata")
    teams_after_first = Team.objects.count()
    matches_after_first = Match.objects.count()

    call_command("loadreferencedata")  # re-run
    assert Team.objects.count() == teams_after_first
    assert Match.objects.count() == matches_after_first


@pytest.mark.django_db
def test_unresolved_knockout_fixture():
    call_command("loadreferencedata")
    r32 = Match.objects.get(fifa_match_number=88)
    assert r32.home_team is None and r32.away_team is None
    assert r32.home_placeholder == "Winner Group C"
    assert r32.bracket_slot == "R32-3"
    assert r32.is_resolved is False
    assert r32.label == "Winner Group C vs Runner-up Group I"


@pytest.mark.django_db
def test_kickoffs_are_timezone_aware():
    call_command("loadreferencedata")
    for m in Match.objects.all():
        assert m.kickoff.tzinfo is not None
