"""The /api/fixtures/health/ endpoint: at-a-glance refresh + resolution health."""
import pytest
from rest_framework.test import APIClient

from events.models import RefreshState
from django.utils import timezone


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_health_reports_resolved_vs_tbd(seeded, client):
    r = client.get("/api/fixtures/health/")
    assert r.status_code == 200
    body = r.json()

    m = body["matches"]
    # Counts are internally consistent.
    assert m["total"] == m["resolved"] + m["tbd"]
    assert m["total"] > 0

    # Group games are resolved; knockout fixtures start as TBD placeholders.
    by_stage = {row["stage"]: row for row in body["by_stage"]}
    assert "group" in by_stage
    assert by_stage["group"]["tbd"] == 0  # group opponents are known
    # Per-stage totals sum back to the overall total.
    assert sum(row["total"] for row in body["by_stage"]) == m["total"]
    assert sum(row["resolved"] for row in body["by_stage"]) == m["resolved"]


@pytest.mark.django_db
def test_health_staleness_flag(seeded, client):
    # No refresh recorded yet -> stale + "never".
    assert client.get("/api/fixtures/health/").json()["stale"] is True
    assert client.get("/api/fixtures/health/").json()["age_human"] == "never"

    # A fresh refresh clears the staleness flag.
    state = RefreshState.get()
    state.fixtures_refreshed_at = timezone.now()
    state.save(update_fields=["fixtures_refreshed_at"])

    body = client.get("/api/fixtures/health/").json()
    assert body["stale"] is False
    assert body["fixtures_refreshed_at"] is not None
    assert body["age_seconds"] is not None
