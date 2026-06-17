from django.contrib import admin

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
    list_display = ("name", "venue_type", "environment", "city", "region", "needs_review")
    list_filter = ("needs_review", "venue_type", "environment", "region")
    search_fields = ("name", "city", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = (VenueAffiliationInline, ScreeningPolicyInline)


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
