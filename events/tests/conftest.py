"""Shared pytest fixtures: seed the DB the same way the app does."""
import pytest
from django.core.management import call_command

SAMPLE = "sample_data.json"


@pytest.fixture
def seeded(db):
    """Reference data + sample import, materialized — the v1 seed flow."""
    call_command("loadreferencedata")
    call_command("importwatchparties", SAMPLE)
    return None
