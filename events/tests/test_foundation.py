"""Task 1.6 — the project boots and all six models are registered."""
from django.apps import apps
from django.contrib import admin


def test_all_six_models_registered():
    expected = {"Team", "Match", "Venue", "VenueAffiliation", "Screening", "ScreeningPolicy"}
    registered = {m.__name__ for m in apps.get_app_config("events").get_models()}
    assert expected <= registered


def test_models_in_admin():
    admin_models = {m.__name__ for m in admin.site._registry}
    for name in ("Team", "Match", "Venue", "VenueAffiliation", "Screening", "ScreeningPolicy"):
        assert name in admin_models


def test_settings_boot():
    from django.conf import settings

    assert "events" in settings.INSTALLED_APPS
    assert settings.USE_TZ is True
