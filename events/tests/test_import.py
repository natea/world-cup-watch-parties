"""Task 3.5 — import is validated, idempotent, materializes policies, and
re-materializes after a knockout fixture resolves."""
import json

import pytest
from django.core.management import call_command

from events.models import Match, Screening, Team, Venue


@pytest.mark.django_db
def test_import_idempotent_row_counts(seeded):
    counts = (Venue.objects.count(), Screening.objects.count())
    call_command("importwatchparties", "sample_data.json")  # second run
    assert (Venue.objects.count(), Screening.objects.count()) == counts


@pytest.mark.django_db
def test_invalid_payload_aborts_with_no_writes(tmp_path, db):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"venues": [{"name": "x"}]}))  # missing required fields
    with pytest.raises(Exception):
        call_command("importwatchparties", str(bad))
    assert Venue.objects.count() == 0


@pytest.mark.django_db
def test_all_matches_policy_fans_out(seeded):
    banshee = Venue.objects.get(slug="the-banshee")
    generated = banshee.screenings.filter(is_generated=True)
    # One generated screening per match in the fixture list.
    assert generated.count() == Match.objects.count()
    assert generated.count() >= 1


@pytest.mark.django_db
def test_provenance_preserved(seeded):
    haven = Venue.objects.get(slug="the-haven")
    assert haven.source == "research-2026-06"
    assert Screening.objects.filter(source="research-2026-06").exists()


@pytest.mark.django_db
def test_rematerialize_after_bracket_resolves(seeded):
    """A by_team policy picks up a newly-resolved knockout fixture without
    duplicating existing screenings."""
    from events.models import PolicyType

    banshee = Venue.objects.get(slug="the-banshee")
    france = Team.objects.get(fifa_code="FRA")

    # Start clean: make this a France by_team policy and clear prior screenings
    # so we observe exactly what the policy materializes.
    banshee.screenings.all().delete()
    policy = banshee.policies.first()
    policy.policy_type = PolicyType.BY_TEAM
    policy.save()
    policy.teams.set([france])

    # The QF fixture (#99) is unresolved → not yet a France match.
    first = policy.materialize()
    before = banshee.screenings.filter(is_generated=True).count()
    assert before == first  # only France's already-resolved matches (e.g. #71)
    assert not banshee.screenings.filter(match__fifa_match_number=99).exists()

    # Bracket resolves: #99 now involves France. Re-materialize.
    qf = Match.objects.get(fifa_match_number=99)
    qf.home_team = france
    qf.save()
    created = policy.materialize()

    assert created >= 1
    assert banshee.screenings.filter(match__fifa_match_number=99).exists()
    assert banshee.screenings.filter(is_generated=True).count() == before + created
    # Re-running again creates nothing (idempotent).
    assert policy.materialize() == 0
