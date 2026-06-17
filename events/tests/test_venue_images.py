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

from events import places, wikimedia
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
def test_serializer_candidate_match_falls_back_until_confirmed():
    # A candidate match keeps a place_id but image_source="candidate" — it must
    # fall back, not show an unverified photo, until a reviewer confirms it.
    venue = _make_venue(
        venue_type=VenueType.WATERFRONT,
        place_id="ChIJcandidate",
        image_source="candidate",
    )
    img = VenueSerializer(venue).data["image"]
    assert img["source"] == "fallback"
    assert img["attribution"] is None
    assert img["url"] == "/venue-fallbacks/waterfront.png"


@pytest.mark.django_db
def test_serializer_wikimedia_tier():
    venue = _make_venue(
        venue_type=VenueType.PLAZA,
        image_source="wikimedia",
        image_url="https://upload.wikimedia.org/x/plaza.jpg",
        image_attribution="Photo: Jane Doe, CC BY-SA 4.0 via Wikimedia Commons",
    )
    img = VenueSerializer(venue).data["image"]
    assert img["source"] == "wikimedia"
    assert img["url"] == "https://upload.wikimedia.org/x/plaza.jpg"
    assert img["attribution"] == "Photo: Jane Doe, CC BY-SA 4.0 via Wikimedia Commons"


@pytest.mark.django_db
def test_serializer_google_tier_wins_over_wikimedia():
    # A confirmed Google photo takes precedence even if image_url is set.
    venue = _make_venue(
        place_id="ChIJabc",
        image_source="google_places",
        image_attribution="Photo by X via Google",
        image_url="https://upload.wikimedia.org/x/ignored.jpg",
    )
    img = VenueSerializer(venue).data["image"]
    assert img["source"] == "google_places"


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
    # Marked as a candidate (photo-review signal), NOT trusted as a photo, and
    # the data-quality needs_review flag is left untouched.
    assert venue.image_source == "candidate"
    assert venue.place_id == "ChIJother"
    assert venue.needs_review is False


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


# --- wikimedia client (transport mocked) -----------------------------------
def _commons_page(license_name, artist="<a>Jane Doe</a>", with_url=True):
    info = {"extmetadata": {}}
    if with_url:
        info["thumburl"] = "https://upload.wikimedia.org/x/plaza.jpg"
    if license_name is not None:
        info["extmetadata"]["LicenseShortName"] = {"value": license_name}
    if artist is not None:
        info["extmetadata"]["Artist"] = {"value": artist}
    return {"query": {"pages": {"1": {"index": 1, "imageinfo": [info]}}}}


def test_wikimedia_find_image_free_license(monkeypatch):
    monkeypatch.setattr(wikimedia, "_get", lambda url, params: _commons_page("CC BY-SA 4.0"))
    img = wikimedia.find_image("City Hall Plaza", city="Boston")
    assert img is not None
    assert img.url == "https://upload.wikimedia.org/x/plaza.jpg"
    assert img.attribution == "Photo: Jane Doe, CC BY-SA 4.0 via Wikimedia Commons"


def test_wikimedia_rejects_nonfree_license(monkeypatch):
    monkeypatch.setattr(
        wikimedia, "_get", lambda url, params: _commons_page("All rights reserved")
    )
    assert wikimedia.find_image("Somewhere", city="Boston") is None


def test_wikimedia_fails_closed_on_error(monkeypatch):
    monkeypatch.setattr(wikimedia, "_get", lambda url, params: None)
    assert wikimedia.find_image("Somewhere") is None


def test_wikimedia_empty_query_returns_none():
    assert wikimedia.find_image("", city="") is None


# --- confirm / reject review workflow --------------------------------------
@pytest.mark.django_db
def test_confirm_promotes_flagged_candidate(monkeypatch):
    from django.core.management import call_command

    venue = _make_venue(
        name="The Banshee",
        place_id="ChIJcandidate",
        image_source="candidate",
        needs_review=True,  # data-quality flag — confirm must NOT touch it
    )
    monkeypatch.setattr(places, "is_enabled", lambda: True)
    monkeypatch.setattr(
        places,
        "photo_for_place",
        lambda place_id, **k: places.PlacePhoto(
            url="https://example.com/p.jpg", attribution="Photo by The Banshee via Google"
        ),
    )

    call_command("resolvevenueplaces", "--confirm", venue.slug)
    venue.refresh_from_db()
    assert venue.image_source == "google_places"
    assert venue.image_attribution == "Photo by The Banshee via Google"
    assert venue.needs_review is True  # data-quality flag left untouched
    assert venue.place_id == "ChIJcandidate"


@pytest.mark.django_db
def test_confirm_noops_cleanly_without_key(monkeypatch):
    from django.core.management import call_command

    venue = _make_venue(
        place_id="ChIJcandidate", image_source="candidate", needs_review=True
    )
    monkeypatch.setattr(places, "is_enabled", lambda: False)

    def _boom(*a, **k):  # pragma: no cover
        raise AssertionError("photo_for_place must not be called without a key")

    monkeypatch.setattr(places, "photo_for_place", _boom)
    call_command("resolvevenueplaces", "--confirm", venue.slug)
    venue.refresh_from_db()
    # Promoted to google_places with empty attribution; the proxy re-resolves.
    assert venue.image_source == "google_places"
    assert venue.image_attribution == ""
    assert venue.needs_review is True  # data-quality flag left untouched


@pytest.mark.django_db
def test_reject_clears_candidate_to_fallback():
    from django.core.management import call_command

    venue = _make_venue(
        venue_type=VenueType.WATERFRONT,
        place_id="ChIJcandidate",
        image_source="candidate",
        needs_review=True,  # data-quality flag — reject must NOT touch it
    )
    call_command("resolvevenueplaces", "--reject", venue.slug)
    venue.refresh_from_db()
    assert venue.place_id == ""
    assert venue.image_source == ""
    assert venue.needs_review is True  # data-quality flag left untouched
    # Now serializes to the category fallback.
    img = VenueSerializer(venue).data["image"]
    assert img["source"] == "fallback"
    assert img["url"] == "/venue-fallbacks/waterfront.png"


# --- wikimedia backfill command --------------------------------------------
@pytest.mark.django_db
def test_wikimedia_backfill_stores_hit_and_is_idempotent(monkeypatch):
    from django.core.management import call_command

    venue = _make_venue(name="City Hall Plaza", venue_type=VenueType.PLAZA, city="Boston")

    calls = {"n": 0}

    def fake_find(name, city="", lat=None, lng=None):
        calls["n"] += 1
        return wikimedia.WikiImage(
            url="https://upload.wikimedia.org/x/plaza.jpg",
            attribution="Photo: Jane Doe, CC BY-SA 4.0 via Wikimedia Commons",
        )

    monkeypatch.setattr(wikimedia, "find_image", fake_find)

    call_command("resolvevenuewikimedia")
    venue.refresh_from_db()
    assert venue.image_source == "wikimedia"
    assert venue.image_url == "https://upload.wikimedia.org/x/plaza.jpg"
    assert venue.image_attribution == "Photo: Jane Doe, CC BY-SA 4.0 via Wikimedia Commons"
    assert calls["n"] == 1

    # Idempotent: a second run skips the already-wikimedia venue (no new call).
    call_command("resolvevenuewikimedia")
    assert calls["n"] == 1


@pytest.mark.django_db
def test_wikimedia_backfill_noop_on_no_result_leaves_fallback(monkeypatch):
    from django.core.management import call_command

    venue = _make_venue(venue_type=VenueType.BAR)
    monkeypatch.setattr(wikimedia, "find_image", lambda *a, **k: None)

    call_command("resolvevenuewikimedia")
    venue.refresh_from_db()
    assert venue.image_source == ""
    assert venue.image_url == ""
    img = VenueSerializer(venue).data["image"]
    assert img["source"] == "fallback"


@pytest.mark.django_db
def test_wikimedia_backfill_skips_confirmed_google(monkeypatch):
    from django.core.management import call_command

    venue = _make_venue(place_id="ChIJabc", image_source="google_places")

    def _boom(*a, **k):  # pragma: no cover - confirmed Google is never overwritten
        raise AssertionError("find_image must not be called for a confirmed Google venue")

    monkeypatch.setattr(wikimedia, "find_image", _boom)
    call_command("resolvevenuewikimedia")
    venue.refresh_from_db()
    assert venue.image_source == "google_places"
