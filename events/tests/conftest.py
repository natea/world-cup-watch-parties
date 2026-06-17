"""Shared pytest fixtures: seed the DB the same way the app does."""
import pytest
from django.core.management import call_command

SAMPLE = "sample_data.json"


@pytest.fixture
def seeded(db):
    """Reference data + sample import, materialized — the minimal test world.

    Uses the in-code provisional seed (--builtin) paired with sample_data.json,
    which is self-contained and decoupled from the full authoritative FIFA
    fixture file."""
    call_command("loadreferencedata", builtin=True)
    call_command("importwatchparties", SAMPLE)
    return None
