"""Task 4.7 — the three endpoints honor the same filter set identically;
family-friendly and free toggles behave per the cost/age model."""
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_schedule_grouped_by_day(seeded, client):
    r = client.get("/api/schedule/")
    assert r.status_code == 200
    days = r.json()["days"]
    dates = [g["date"] for g in days]
    assert dates == sorted(dates)  # day-ordered
    # Every screening carries a venue + match label.
    sample = days[0]["screenings"][0]
    assert "venue" in sample and "label" in sample["match"]


@pytest.mark.django_db
def test_map_only_returns_venues_with_coordinates(seeded, client):
    r = client.get("/api/map/")
    assert r.status_code == 200
    venues = r.json()["venues"]
    slugs = {v["venue"]["slug"] for v in venues}
    # lucky-strike-somerville has no coordinates in the sample → excluded.
    assert "lucky-strike-somerville" not in slugs
    assert "fifa-fan-festival-city-hall-plaza" in slugs


@pytest.mark.django_db
def test_map_distance_sort(seeded, client):
    # Anchor at City Hall Plaza → it should be nearest (distance ~0).
    r = client.get("/api/map/?lat=42.3603&lng=-71.0578")
    venues = r.json()["venues"]
    distances = [v["distance_km"] for v in venues]
    assert distances == sorted(distances)
    assert venues[0]["venue"]["slug"] == "fifa-fan-festival-city-hall-plaza"


@pytest.mark.django_db
def test_team_playing_vs_hub_differ(seeded, client):
    playing = client.get("/api/screenings/?team=SCO&team_mode=playing").json()["screenings"]
    hub = client.get("/api/screenings/?team=SCO&team_mode=hub").json()["screenings"]
    # Scotland plays match 22 (shown at several venues); its hub is only the Haven.
    hub_slugs = {s["venue"]["slug"] for s in hub}
    assert hub_slugs == {"the-haven"}
    assert len(playing) >= 1
    assert playing != hub


@pytest.mark.django_db
def test_free_toggle_includes_lottery(seeded, client):
    free = client.get("/api/screenings/?cost=free").json()["screenings"]
    cost_types = {s["cost_type"] for s in free}
    # free_lottery (Fan Fest) must be included; nothing ticketed.
    assert "free_lottery" in cost_types
    assert "ticketed" not in cost_types


@pytest.mark.django_db
def test_family_friendly_excludes_bars(seeded, client):
    ff = client.get("/api/screenings/?family_friendly=true").json()["screenings"]
    slugs = {s["venue"]["slug"] for s in ff}
    # 21+ bars are excluded; the all-ages Fan Fest is included.
    assert "the-haven" not in slugs
    assert "the-banshee" not in slugs
    assert "fifa-fan-festival-city-hall-plaza" in slugs


@pytest.mark.django_db
def test_filter_set_consistent_across_views(seeded, client):
    """The same filter applied to schedule, map, and screenings draws from one
    filtered screening set."""
    q = "?exclude_bars=true&cost=free"
    sched = client.get(f"/api/schedule/{q}").json()
    sched_slugs = {s["venue"]["slug"] for g in sched["days"] for s in g["screenings"]}
    screenings = client.get(f"/api/screenings/{q}").json()["screenings"]
    scr_slugs = {s["venue"]["slug"] for s in screenings}
    map_slugs = {v["venue"]["slug"] for v in client.get(f"/api/map/{q}").json()["venues"]}
    # No bars anywhere.
    for collection in (sched_slugs, scr_slugs):
        assert "the-haven" not in collection and "the-banshee" not in collection
    # Map is the subset of screening venues that have coordinates.
    assert map_slugs <= scr_slugs


@pytest.mark.django_db
def test_venue_detail(seeded, client):
    r = client.get("/api/venues/the-banshee/")
    assert r.status_code == 200
    body = r.json()
    assert body["venue"]["slug"] == "the-banshee"
    assert body["venue"]["affiliations"]  # supporter hub data present
    # The Banshee's all_matches policy gives it a screening per match.
    assert len(body["screenings"]) >= 1
    assert all("match" in s and "label" in s["match"] for s in body["screenings"])


@pytest.mark.django_db
def test_venue_detail_404(seeded, client):
    assert client.get("/api/venues/does-not-exist/").status_code == 404


@pytest.mark.django_db
def test_tbd_matchup_serializes(seeded, client):
    screenings = client.get("/api/screenings/").json()["screenings"]
    unresolved = [s for s in screenings if not s["match"]["is_resolved"]]
    assert unresolved  # the generated knockout screenings
    assert all("vs" in s["match"]["label"] for s in unresolved)
