"""Admin smoke tests — the venue changelist renders custom display columns
(photo_status / review_flag) per row, which is exactly where a bad
format_html call 500'd in production. Render it with rows to guard that."""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from events.models import Venue, VenueType


@pytest.mark.django_db
def test_venue_changelist_renders_with_rows():
    User = get_user_model()
    admin = User.objects.create_superuser("admin", "a@b.c", "pw")
    # One of each review/photo state so every display branch is exercised.
    Venue.objects.create(name="Flagged Bar", venue_type=VenueType.BAR, city="Boston",
                         needs_review=True, image_source="candidate", place_id="ChIJx")
    Venue.objects.create(name="Confirmed Pub", venue_type=VenueType.BAR, city="Boston",
                         needs_review=False, image_source="google_places", place_id="ChIJy")
    Venue.objects.create(name="Plain Plaza", venue_type=VenueType.PLAZA, city="Boston")

    client = Client()
    client.force_login(admin)
    resp = client.get("/admin/events/venue/")
    assert resp.status_code == 200
