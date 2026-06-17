from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("schedule/", views.ScheduleView.as_view(), name="schedule"),
    path("map/", views.MapView.as_view(), name="map"),
    path("screenings/", views.ScreeningsView.as_view(), name="screenings"),
    path("search/", views.SearchView.as_view(), name="search"),
    path("geocode/", views.GeocodeView.as_view(), name="geocode"),
    # More specific photo route before the catch-all venue detail.
    path("venues/<slug:slug>/photo", views.VenuePhotoView.as_view(), name="venue-photo"),
    path("venues/<slug:slug>/", views.VenueDetailView.as_view(), name="venue-detail"),
    path("teams/", views.TeamListView.as_view(), name="teams"),
    path("meta/", views.MetaView.as_view(), name="meta"),
]
