"""Tasks 5.1/5.2 — FIFA fixture mapping (offline) and authoritative load."""
import json
from pathlib import Path

import pytest
from django.core.management import call_command

from events.models import Match, Screening, Team

FIXTURE = Path(__file__).parent / "fixtures" / "fifa_sample.json"
REFERENCE = "data/fifa_reference.json"
WATCH_PARTIES = "data/watch_parties.json"


def test_mapping_from_raw_payload(tmp_path):
    """fetchfixtures maps a raw FIFA payload to the contract without network."""
    out = tmp_path / "ref.json"
    call_command("fetchfixtures", source=str(FIXTURE), out=str(out))
    bundle = json.loads(out.read_text())

    by_num = {m["fifa_match_number"]: m for m in bundle["matches"]}

    # Resolved group match.
    g = by_num[5]
    assert g["stage"] == "group" and g["group"] == "C"
    assert g["home_team_code"] == "HAI" and g["away_team_code"] == "SCO"
    assert g["kickoff"].startswith("2026-06-14T01:00:00")
    assert g["host_stadium"] == "Boston Stadium"

    # Unresolved knockout: null teams, placeholders, stable bracket slot.
    k = by_num[73]
    assert k["stage"] == "r32"
    assert k["home_team_code"] is None and k["away_team_code"] is None
    assert k["home_placeholder"] == "2A" and k["away_placeholder"] == "2B"
    assert k["bracket_slot"] == "r32-73"

    # Teams carry flags (self-contained, so a fresh deploy keeps UI flags).
    flags = {t["fifa_code"]: t["flag_emoji"] for t in bundle["teams"]}
    assert flags["SCO"] and flags["HAI"]


@pytest.mark.django_db
def test_authoritative_load_lights_up_every_team():
    """Loading the committed snapshot yields the full tournament, and a
    non-Gillette nation gains screenings once policies materialize."""
    if not Path(REFERENCE).exists():
        pytest.skip("committed FIFA reference snapshot not present")

    call_command("loadreferencedata", path=REFERENCE)
    assert Match.objects.count() == 104
    assert Team.objects.count() == 48

    call_command("importwatchparties", WATCH_PARTIES)

    # The USA does not play at Gillette, but all_matches venues screen its games.
    usa = Team.objects.get(fifa_code="USA")
    assert Match.objects.involving(usa).count() >= 1
    assert Screening.objects.for_team(usa).exists()
    # Its supporter hub (Banshee, all_matches) is visible.
    assert Screening.objects.at_supporter_hub(team=usa).exists()
