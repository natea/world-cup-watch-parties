import { useEffect, useState } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { api } from "../api";
import type { Anchor, Filters, MapVenue } from "../types";
import { ScreeningCard } from "./ScreeningCard";
import { ProximityControl } from "./ProximityControl";

// Fix Leaflet's default marker icon paths under a bundler.
const icon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
});

// The user's searched location — a distinct red dot, clearly different from the
// blue venue pins, so distances are easy to read off the map.
const anchorIcon = L.divIcon({
  className: "anchor-marker",
  html: '<span class="anchor-dot"></span>',
  iconSize: [20, 20],
  iconAnchor: [10, 10],
  popupAnchor: [0, -10],
});

// Default map center + anchor (downtown Boston / City Hall Plaza) when the user
// hasn't set a location.
const CENTER: [number, number] = [42.34, -71.08];
const DEFAULT_ANCHOR = { lat: 42.3603, lng: -71.0578, label: "downtown Boston" };

const milesFromKm = (km: number) => Math.round(km * 0.621371 * 10) / 10;

// Cap the popup to the next few upcoming screenings; "more" opens venue detail.
const POPUP_SCREENINGS = 5;

// Recenter/zoom the map imperatively when the anchor changes.
function Recenter({ anchor }: { anchor: Anchor | null }) {
  const map = useMap();
  useEffect(() => {
    if (anchor) map.flyTo([anchor.lat, anchor.lng], 12, { duration: 0.6 });
  }, [anchor, map]);
  return null;
}

export function MapView({
  filters,
  onOpenVenue,
  anchor,
  setLocation,
}: {
  filters: Filters;
  onOpenVenue: (slug: string) => void;
  anchor: Anchor | null;
  setLocation: (a: Anchor | null) => void;
}) {
  const [venues, setVenues] = useState<MapVenue[]>([]);
  const [error, setError] = useState<string | null>(null);

  const effective = anchor ?? DEFAULT_ANCHOR;
  const exact = anchor?.precision === "address" || anchor?.precision === "device";

  useEffect(() => {
    api
      .map(filters, { lat: effective.lat, lng: effective.lng })
      .then((d) => {
        setVenues(d.venues);
        setError(null);
      })
      .catch((e) => setError(String(e)));
  }, [filters, effective.lat, effective.lng]);

  return (
    <div className="mapwrap">
      <ProximityControl anchor={anchor} onResolve={setLocation} />
      {error ? (
        <p className="status error">{error}</p>
      ) : (
        <>
          <MapContainer center={CENTER} zoom={11} className="leaflet">
            <Recenter anchor={anchor} />
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {anchor && (
              <Marker
                position={[anchor.lat, anchor.lng]}
                icon={anchorIcon}
                zIndexOffset={1000}
              >
                <Popup>
                  📍 {anchor.label || "Your location"}
                  {!exact && <div className="popmeta">approximate (ZIP centroid)</div>}
                </Popup>
              </Marker>
            )}
            {venues.map((mv) => (
              <Marker
                key={mv.venue.slug}
                position={[Number(mv.venue.latitude), Number(mv.venue.longitude)]}
                icon={icon}
              >
                <Popup maxWidth={340} minWidth={260}>
                  <button
                    type="button"
                    className="pop-venue-link"
                    onClick={() => onOpenVenue(mv.venue.slug)}
                  >
                    <strong>{mv.venue.name}</strong> →
                  </button>
                  <div className="popmeta">
                    {mv.venue.city}
                    {mv.distance_km !== undefined &&
                      ` · ${milesFromKm(mv.distance_km)} mi${exact ? "" : " (approx.)"}`}
                  </div>
                  {mv.venue.affiliations.map((a, i) => (
                    <div key={i} className="affil">
                      🏴 {a.team ? a.team.name : a.club} hub
                    </div>
                  ))}
                  {(() => {
                    // Cap the popup to a few screenings — a venue that shows every
                    // match would otherwise render a giant popup (which also makes
                    // Leaflet auto-pan off into the ocean). Past games are already
                    // filtered server-side by default (and revealed via "show
                    // past"), so we just take the first few here.
                    const shown = mv.screenings.slice(0, POPUP_SCREENINGS);
                    const more = mv.screenings.length - shown.length;
                    if (shown.length === 0) {
                      return <div className="popnone">No screenings</div>;
                    }
                    return (
                      <>
                        <div className="poplist">
                          {shown.map((s) => (
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
                        {more > 0 && (
                          <button
                            type="button"
                            className="pop-more"
                            onClick={() => onOpenVenue(mv.venue.slug)}
                          >
                            + {more} more screening{more === 1 ? "" : "s"} →
                          </button>
                        )}
                      </>
                    );
                  })()}
                </Popup>
              </Marker>
            ))}
          </MapContainer>
          <p className="maphint">
            {venues.length} venue{venues.length === 1 ? "" : "s"} with a matching screening · sorted
            by distance from {effective.label}
          </p>
        </>
      )}
    </div>
  );
}
