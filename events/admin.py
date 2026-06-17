from django.contrib import admin

from . import places
from .models import (
    Match,
    Screening,
    ScreeningPolicy,
    Team,
    Venue,
    VenueAffiliation,
)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "fifa_code", "group", "confederation", "fifa_rank")
    list_filter = ("confederation", "group")
    search_fields = ("name", "fifa_code")


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("fifa_match_number", "label", "stage", "kickoff", "host_stadium")
    list_filter = ("stage", "group")
    search_fields = ("home_placeholder", "away_placeholder", "bracket_slot")
    autocomplete_fields = ("home_team", "away_team")


class VenueAffiliationInline(admin.TabularInline):
    model = VenueAffiliation
    extra = 0
    autocomplete_fields = ("team",)


class ScreeningPolicyInline(admin.TabularInline):
    model = ScreeningPolicy
    extra = 0


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "venue_type",
        "environment",
        "city",
        "region",
        "image_source",
        "needs_review",
    )
    list_filter = ("needs_review", "image_source", "venue_type", "environment", "region")
    search_fields = ("name", "city", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = (VenueAffiliationInline, ScreeningPolicyInline)
    actions = ("confirm_google_match", "reject_match")

    @admin.action(description="Confirm Google photo match")
    def confirm_google_match(self, request, queryset):
        """Promote selected candidates to a confirmed google_places source."""
        confirmed = 0
        for venue in queryset:
            if not venue.place_id:
                continue
            photo = (
                places.photo_for_place(venue.place_id) if places.is_enabled() else None
            )
            venue.image_source = "google_places"
            venue.image_attribution = photo.attribution if photo else ""
            venue.needs_review = False
            venue.save(
                update_fields=["image_source", "image_attribution", "needs_review"]
            )
            confirmed += 1
        self.message_user(request, f"Confirmed {confirmed} Google photo match(es).")

    @admin.action(description="Reject match (drop to next image tier)")
    def reject_match(self, request, queryset):
        """Clear the candidate place_id + review flag so the venue falls back."""
        rejected = queryset.update(
            place_id="",
            image_source="",
            image_attribution="",
            needs_review=False,
        )
        self.message_user(request, f"Rejected {rejected} match(es).")


@admin.register(Screening)
class ScreeningAdmin(admin.ModelAdmin):
    list_display = (
        "venue",
        "match",
        "starts_at",
        "cost_type",
        "is_generated",
        "needs_review",
    )
    list_filter = ("needs_review", "cost_type", "is_generated")
    search_fields = ("venue__name",)
    autocomplete_fields = ("venue", "match")
    date_hierarchy = "starts_at"


@admin.register(VenueAffiliation)
class VenueAffiliationAdmin(admin.ModelAdmin):
    list_display = ("venue", "affiliation_type", "team", "club")
    list_filter = ("affiliation_type",)
    autocomplete_fields = ("venue", "team")


@admin.register(ScreeningPolicy)
class ScreeningPolicyAdmin(admin.ModelAdmin):
    list_display = ("venue", "policy_type", "default_cost_type")
    list_filter = ("policy_type",)
    autocomplete_fields = ("venue",)
