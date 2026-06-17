import { useEffect, useState } from "react";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { api } from "../api";
import type { Filters, MapVenue } from "../types";
import { ScreeningCard } from "./ScreeningCard";

// Fix Leaflet's default marker icon paths under a bundler.
const icon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
});

// Boston / Greater Boston default center + the City Hall Plaza anchor.
const CENTER: [number, number] = [42.34, -71.08];
const ANCHOR = { lat: 42.3603, lng: -71.0578 };

export function MapView({
  filters,
  onOpenVenue,
}: {
  filters: Filters;
  onOpenVenue: (slug: string) => void;
}) {
  const [venues, setVenues] = useState<MapVenue[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .map(filters, ANCHOR)
      .then((d) => {
        setVenues(d.venues);
        setError(null);
      })
      .catch((e) => setError(String(e)));
  }, [filters]);

  if (error) return <p className="status error">{error}</p>;

  return (
    <div className="mapwrap">
      <MapContainer center={CENTER} zoom={11} className="leaflet">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {venues.map((mv) => (
          <Marker
            key={mv.venue.slug}
            position={[Number(mv.venue.latitude), Number(mv.venue.longitude)]}
            icon={icon}
          >
            <Popup>
              <button
                type="button"
                className="pop-venue-link"
                onClick={() => onOpenVenue(mv.venue.slug)}
              >
                <strong>{mv.venue.name}</strong> →
              </button>
              <div className="popmeta">
                {mv.venue.city}
                {mv.distance_km !== undefined && ` · ${mv.distance_km} km`}
              </div>
              {mv.venue.affiliations.map((a, i) => (
                <div key={i} className="affil">
                  🏴 {a.team ? a.team.name : a.club} hub
                </div>
              ))}
              <div className="poplist">
                {mv.screenings.map((s) => (
                  <ScreeningCard
                    key={s.id}
                    match={s.match}
                    starts_at={s.starts_at}
                    cost_type={s.cost_type}
                    is_family_friendly={s.is_family_friendly}
                    registration_required={s.registration_required}
                    entry_guaranteed={s.entry_guaranteed}
                    showDate
                  />
                ))}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      <p className="maphint">
        {venues.length} venue{venues.length === 1 ? "" : "s"} with a matching screening · sorted by
        distance from City Hall Plaza
      </p>
    </div>
  );
}
