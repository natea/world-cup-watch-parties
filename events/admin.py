from django.contrib import admin
from django.utils.html import format_html

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
        "photo_thumb",
        "name",
        "venue_type",
        "city",
        "region",
        "photo_status",
        "review_flag",
    )
    list_display_links = ("name",)
    list_filter = ("image_source", "needs_review", "venue_type", "environment", "region")

    @admin.display(description="Photo status", ordering="image_source")
    def photo_status(self, obj):
        """Friendly, intuitive photo-match state (separate from data-quality)."""
        label, color = {
            "google_places": ("✓ Google photo", "#16a34a"),
            "wikimedia": ("✓ Wikimedia", "#16a34a"),
            "candidate": ("● candidate — confirm", "#b45309"),
            "": ("illustration (fallback)", "#6b7280"),
        }.get(obj.image_source, (obj.image_source, "#6b7280"))
        return format_html('<span style="color:{}">{}</span>', color, label)

    @admin.display(description="Data review", ordering="needs_review")
    def review_flag(self, obj):
        """Data-quality flag, shown so the colors match intuition: amber = needs
        attention, muted = fine. (The raw boolean icon is green-for-True, which
        reads backwards.)"""
        if obj.needs_review:
            return format_html(
                '<span style="color:#b45309;font-weight:600">⚠ needs review</span>'
            )
        return format_html('<span style="color:#9ca3af">— ok</span>')
    search_fields = ("name", "city", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("candidate_photo_preview",)
    inlines = (VenueAffiliationInline, ScreeningPolicyInline)
    actions = ("confirm_google_match", "reject_match")

    @admin.display(description="Photo")
    def photo_thumb(self, obj):
        """Small thumbnail in the changelist so a reviewer can eyeball matches.
        Loads via the photo proxy (302 → Google / Wikimedia / fallback)."""
        if not obj.pk:
            return "—"
        return format_html(
            '<img src="/api/venues/{}/photo" loading="lazy" '
            'style="height:40px;width:64px;object-fit:cover;border-radius:4px" />',
            obj.slug,
        )

    @admin.display(description="Candidate / current photo")
    def candidate_photo_preview(self, obj):
        """Larger preview on the change form to confirm a low-confidence match.
        Shows the candidate photo plus a Google Maps link to verify the place."""
        if not obj or not obj.pk:
            return "—"
        if not obj.place_id and obj.image_source != "wikimedia":
            return "No place match — venue uses the category-illustration fallback."
        maps = format_html(
            '<a href="https://www.google.com/maps/search/?api=1&query={}" '
            'target="_blank" rel="noreferrer">Verify on Google Maps ↗</a>',
            f"{obj.name}, {obj.address}, {obj.city}".strip(", "),
        )
        return format_html(
            '<div><img src="/api/venues/{}/photo" '
            'style="max-height:260px;border-radius:8px;display:block;margin-bottom:8px" />'
            "<div>source: <b>{}</b> &middot; place_id: <code>{}</code></div>"
            "<div>{}</div></div>",
            obj.slug,
            obj.image_source or "(unconfirmed)",
            obj.place_id or "—",
            maps,
        )

    @admin.action(description="Confirm Google photo match")
    def confirm_google_match(self, request, queryset):
        """Promote selected candidates to a confirmed google_places source.

        Operates only on the photo `image_source`; leaves `needs_review` (the
        import's data-quality flag) untouched."""
        confirmed = 0
        for venue in queryset:
            if not venue.place_id:
                continue
            photo = (
                places.photo_for_place(venue.place_id) if places.is_enabled() else None
            )
            venue.image_source = "google_places"
            venue.image_attribution = photo.attribution if photo else ""
            venue.save(update_fields=["image_source", "image_attribution"])
            confirmed += 1
        self.message_user(request, f"Confirmed {confirmed} Google photo match(es).")

    @admin.action(description="Reject match (drop to next image tier)")
    def reject_match(self, request, queryset):
        """Clear the candidate place_id/source so the venue falls back.
        Leaves `needs_review` (data-quality flag) untouched."""
        rejected = queryset.update(
            place_id="",
            image_source="",
            image_attribution="",
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
