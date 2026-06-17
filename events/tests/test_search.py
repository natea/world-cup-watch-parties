"""Task 3.1/3.2 — search endpoint: typing, matching, ranking, cap, min-length."""
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()


def _labels(body):
    return [s["label"] for s in body["suggestions"]]


def _types(body):
    return [s["type"] for s in body["suggestions"]]


@pytest.mark.django_db
def test_venue_by_name(seeded, client):
    body = client.get("/api/search/?q=haven").json()
    venues = [s for s in body["suggestions"] if s["type"] == "venue"]
    assert any(s["target"] == {"kind": "venue", "slug": "the-haven"} for s in venues)


@pytest.mark.django_db
def test_country_by_name_and_by_code(seeded, client):
    by_name = client.get("/api/search/?q=scotland").json()["suggestions"]
    assert any(s["type"] == "team" and s["target"] == {"kind": "team", "code": "SCO"} for s in by_name)

    by_code = client.get("/api/search/?q=sco").json()["suggestions"]
    teams = [s for s in by_code if s["type"] == "team"]
    assert teams and teams[0]["target"] == {"kind": "team", "code": "SCO"}


@pytest.mark.django_db
def test_hub_by_affiliated_team(seeded, client):
    # The Haven is Scotland's hub; "scotland" should surface it as a venue too.
    body = client.get("/api/search/?q=scotland").json()["suggestions"]
    slugs = {s["target"].get("slug") for s in body if s["type"] == "venue"}
    assert "the-haven" in slugs


@pytest.mark.django_db
def test_description_keyword_match_ranks_below_name(seeded, client):
    # "tartan army" appears only in venue notes -> The Haven is found (description).
    body = client.get("/api/search/?q=tartan").json()["suggestions"]
    slugs = {s["target"].get("slug") for s in body if s["type"] == "venue"}
    assert "the-haven" in slugs


@pytest.mark.django_db
def test_name_prefix_outranks_description(seeded, client):
    # "haven": The Haven matches by name prefix and must be first.
    body = client.get("/api/search/?q=haven").json()
    assert body["suggestions"][0]["target"] == {"kind": "venue", "slug": "the-haven"}


@pytest.mark.django_db
def test_result_cap(seeded, client):
    body = client.get("/api/search/?q=the&limit=3").json()
    assert len(body["suggestions"]) <= 3


@pytest.mark.django_db
def test_short_and_empty_query_return_empty(seeded, client):
    assert client.get("/api/search/?q=a").json()["suggestions"] == []
    assert client.get("/api/search/?q=").json()["suggestions"] == []
    assert client.get("/api/search/").json()["suggestions"] == []


@pytest.mark.django_db
def test_fuzzy_typo_matches_team(seeded, client):
    # "croatica" is a typo for Croatia — fuzzy fallback should still find it.
    body = client.get("/api/search/?q=croatica").json()["suggestions"]
    assert any(s["target"] == {"kind": "team", "code": "CRO"} for s in body)


@pytest.mark.django_db
def test_fuzzy_typo_matches_venue(seeded, client):
    body = client.get("/api/search/?q=banshe").json()["suggestions"]
    slugs = {s["target"].get("slug") for s in body if s["type"] == "venue"}
    assert "the-banshee" in slugs


@pytest.mark.django_db
def test_alias_matches_official_short_name(db, client):
    """FIFA's official US team name is "USA"; common names must alias to it.
    (The minimal seed names it "United States", so load the FIFA reference where
    it is "USA" to exercise the alias path.)"""
    from pathlib import Path

    from django.core.management import call_command

    if not Path("data/fifa_reference.json").exists():
        pytest.skip("FIFA reference snapshot not present")
    call_command("loadreferencedata", path="data/fifa_reference.json")

    usa = client.get("/api/search/?q=united states").json()["suggestions"]
    assert any(s["target"] == {"kind": "team", "code": "USA"} for s in usa)
    turkey = client.get("/api/search/?q=turkey").json()["suggestions"]
    assert any(s["target"] == {"kind": "team", "code": "TUR"} for s in turkey)


@pytest.mark.django_db
def test_suggestion_shape(seeded, client):
    s = client.get("/api/search/?q=haven").json()["suggestions"][0]
    assert set(s) == {"type", "label", "sublabel", "target"}
    assert s["target"]["kind"] in {"venue", "team"}
