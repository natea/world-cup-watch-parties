"""Tasks 1.4/3.1 — geocode resolution (ZIP offline + address mocked) and the
distance-sorted map from a resolved anchor."""
from unittest import mock

import pytest
from rest_framework.test import APIClient

from events import geocoding


@pytest.fixture
def client():
    return APIClient()


def test_zip_resolves_offline():
    geocoding._zip_table.cache_clear()
    r = geocoding.resolve_zip("02139")  # Cambridge
    assert r and r["precision"] == "zip"
    assert 42.0 < r["lat"] < 42.7 and -71.3 < r["lng"] < -70.9


def test_unknown_or_invalid_zip_returns_none():
    assert geocoding.resolve_zip("99999") is None
    assert geocoding.resolve_zip("abc") is None
    assert geocoding.resolve_zip("") is None


def test_geocode_endpoint_zip(client):
    body = client.get("/api/geocode/?zip=02139").json()
    assert body["result"]["precision"] == "zip"


def test_geocode_endpoint_unknown_zip_is_clean(client):
    body = client.get("/api/geocode/?zip=99999").json()
    assert body["result"] is None  # no error


def test_address_path_mocked(client):
    fake = {
        "result": {
            "addressMatches": [
                {"coordinates": {"x": -71.0578, "y": 42.3603}, "matchedAddress": "1 CITY HALL SQ, BOSTON, MA"}
            ]
        }
    }

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            import json

            return json.dumps(fake).encode()

    with mock.patch("urllib.request.urlopen", return_value=FakeResp()):
        body = client.get("/api/geocode/?address=1 City Hall Square Boston MA").json()
    assert body["result"]["precision"] == "address"
    assert round(body["result"]["lat"], 2) == 42.36


def test_address_geocoder_failure_degrades(client):
    with mock.patch("urllib.request.urlopen", side_effect=OSError("network down")):
        body = client.get("/api/geocode/?address=somewhere").json()
    assert body["result"] is None  # graceful, no 500


@pytest.mark.django_db
def test_map_sorted_by_distance_from_anchor(seeded, client):
    # Anchor at City Hall Plaza -> the Fan Festival there should be nearest.
    body = client.get("/api/map/?lat=42.3603&lng=-71.0578").json()
    venues = body["venues"]
    dists = [v["distance_km"] for v in venues]
    assert dists == sorted(dists)
    assert venues[0]["venue"]["slug"] == "fifa-fan-festival-city-hall-plaza"
