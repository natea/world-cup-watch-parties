"""Venue-images capability tests.

All Google access is mocked via `events.places` monkeypatching — these tests
make NO live network call. They cover:

  * serializer `image` block: licensed-photo case (with attribution) vs the
    category-fallback case (by venue type, no attribution);
  * the photo proxy: redirects to the fallback when the key or place_id is
    missing, and never rehosts bytes (it 302-redirects to Google's URL);
  * the backfill command: stores a confident match, is idempotent, and flags an
    ambiguous match for review.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework.test import APIRequestFactory

from events import places
from events.models import Venue, VenueType
from events.serializers import VenueSerializer


@pytest.fixture
def client():
    return APIClient()


def _make_venue(**kwargs) -> Venue:
    defaults = dict(
        name="Test Tavern",
        venue_type=VenueType.BAR,
        city="Boston",
        address="1 Main St",
    )
    defaults.update(kwargs)
    return Venue.objects.create(**defaults)


# --- serializer ------------------------------------------------------------
@pytest.mark.django_db
def test_serializer_photo_case_has_attribution_and_proxy_url():
    venue = _make_venue(
        place_id="ChIJabc123",
        image_source="google_places",
        image_attribution="Photo by Jane Doe via Google",
    )
    request = APIRequestFactory().get("/api/venues/test-tavern/")
    data = VenueSerializer(venue, context={"request": request}).data
    img = data["image"]
    assert img["source"] == "google_places"
    assert img["attribution"] == "Photo by Jane Doe via Google"
    # URL points at the photo proxy, not a static fallback.
    assert img["url"].endswith("/api/venues/test-tavern/photo")


@pytest.mark.django_db
def test_serializer_ambiguous_match_falls_back_until_confirmed():
    # A flagged/ambiguous match keeps a candidate place_id but leaves
    # image_source blank — it must fall back, not show an unverified photo.
    venue = _make_venue(
        venue_type=VenueType.WATERFRONT,
        place_id="ChIJcandidate",
        image_source="",
        needs_review=True,
    )
    img = VenueSerializer(venue).data["image"]
    assert img["source"] == "fallback"
    assert img["attribution"] is None
    assert img["url"] == "/venue-fallbacks/waterfront.png"


@pytest.mark.django_db
def test_serializer_fallback_case_by_venue_type_no_attribution():
    venue = _make_venue(venue_type=VenueType.BREWERY)  # no place_id
    data = VenueSerializer(venue).data
    img = data["image"]
    assert img["source"] == "fallback"
    assert img["attribution"] is None
    assert img["url"] == "/venue-fallbacks/brewery.png"


# --- proxy -----------------------------------------------------------------
@pytest.mark.django_db
def test_proxy_falls_back_when_no_place_id(client):
    venue = _make_venue(venue_type=VenueType.PARK)  # no place_id
    r = client.get(f"/api/venues/{venue.slug}/photo")
    assert r.status_code == 302
    assert r["Location"] == "/venue-fallbacks/park.png"


@pytest.mark.django_db
def test_proxy_falls_back_when_key_missing(client, monkeypatch):
    venue = _make_venue(venue_type=VenueType.HOTEL, place_id="ChIJxyz")
    # Key unset → feature disabled; never calls Google.
    monkeypatch.setattr(places, "is_enabled", lambda: False)

    def _boom(*a, **k):  # pragma: no cover - must not be called
        raise AssertionError("photo_for_place must not be called without a key")

    monkeypatch.setattr(places, "photo_for_place", _boom)
    r = client.get(f"/api/venues/{venue.slug}/photo")
    assert r.status_code == 302
    assert r["Location"] == "/venue-fallbacks/hotel.png"


@pytest.mark.django_db
def test_proxy_redirects_to_google_without_rehosting(client, monkeypatch):
    venue = _make_venue(place_id="ChIJabc123")
    monkeypatch.setattr(places, "is_enabled", lambda: True)
    monkeypatch.setattr(
        places,
        "photo_for_place",
        lambda place_id, **k: places.PlacePhoto(
            url="https://example.com/photo.jpg", attribution="x"
        ),
    )
    r = client.get(f"/api/venues/{venue.slug}/photo")
    # 302-redirect to Google's URL — bytes are never served/rehosted by us.
    assert r.status_code == 302
    assert r["Location"] == "https://example.com/photo.jpg"
    assert "max-age" in r.get("Cache-Control", "")


@pytest.mark.django_db
def test_proxy_falls_back_on_lookup_error(client, monkeypatch):
    venue = _make_venue(venue_type=VenueType.PLAZA, place_id="ChIJabc123")
    monkeypatch.setattr(places, "is_enabled", lambda: True)
    monkeypatch.setattr(places, "photo_for_place", lambda place_id, **k: None)
    r = client.get(f"/api/venues/{venue.slug}/photo")
    assert r.status_code == 302
    assert r["Location"] == "/venue-fallbacks/plaza.png"


# --- backfill command ------------------------------------------------------
@pytest.mark.django_db
def test_backfill_stores_confident_match_and_is_idempotent(monkeypatch):
    from django.core.management import call_command

    venue = _make_venue(name="The Banshee", city="Boston")
    monkeypatch.setattr(places, "is_enabled", lambda: True)

    calls = {"n": 0}

    def fake_find(name, address=""):
        calls["n"] += 1
        return places.PlaceMatch(
            place_id="ChIJbanshee",
            display_name="The Banshee",  # exact → confident
            formatted_address="Boston, MA",
            photo_name="places/ChIJbanshee/photos/1",
        )

    monkeypatch.setattr(places, "find_place", fake_find)
    # Confident matches resolve the photo once to store its attribution.
    monkeypatch.setattr(
        places,
        "photo_for_place",
        lambda place_id, **k: places.PlacePhoto(
            url="https://example.com/p.jpg", attribution="Photo by The Banshee via Google"
        ),
    )

    call_command("resolvevenueplaces")
    venue.refresh_from_db()
    assert venue.place_id == "ChIJbanshee"
    assert venue.image_source == "google_places"
    assert venue.image_attribution == "Photo by The Banshee via Google"
    assert venue.needs_review is False
    assert calls["n"] == 1

    # Idempotent: a second run skips the already-resolved venue (no new call).
    call_command("resolvevenueplaces")
    assert calls["n"] == 1


@pytest.mark.django_db
def test_backfill_flags_ambiguous_match(monkeypatch):
    from django.core.management import call_command

    venue = _make_venue(name="The Tavern", city="Boston")
    monkeypatch.setattr(places, "is_enabled", lambda: True)
    monkeypatch.setattr(
        places,
        "find_place",
        lambda name, address="": places.PlaceMatch(
            place_id="ChIJother",
            display_name="Completely Different Pub & Grill House",  # low similarity
            formatted_address="Boston, MA",
            photo_name=None,
        ),
    )

    call_command("resolvevenueplaces")
    venue.refresh_from_db()
    assert venue.needs_review is True
    assert venue.image_source == ""  # not trusted as a confident source


@pytest.mark.django_db
def test_backfill_noop_without_key(monkeypatch):
    from django.core.management import call_command

    venue = _make_venue()
    monkeypatch.setattr(places, "is_enabled", lambda: False)

    def _boom(*a, **k):  # pragma: no cover
        raise AssertionError("find_place must not be called without a key")

    monkeypatch.setattr(places, "find_place", _boom)
    call_command("resolvevenueplaces")
    venue.refresh_from_db()
    assert venue.place_id == ""
