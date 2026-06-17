import { useEffect, useState } from "react";
import { api, fallbackImageUrl } from "../api";
import type { Screening, Venue } from "../types";
import { googleMapsUrl } from "../format";
import { ScreeningCard, screeningCardProps } from "./ScreeningCard";

const VENUE_TYPE_LABELS: Record<string, string> = {
  bar: "Bar / pub",
  brewery: "Brewery / taproom",
  restaurant: "Restaurant",
  plaza: "Public plaza / fan festival",
  park: "Park / outdoor space",
  community: "Municipal / community space",
  hotel: "Hotel",
  entertainment: "Entertainment",
  market: "Food hall / market",
  waterfront: "Waterfront / boat",
  university: "University",
  stadium: "Stadium",
};

const ENV_LABELS: Record<string, string> = {
  indoor: "Indoor",
  outdoor: "Outdoor",
  mixed: "Indoor & outdoor",
};

export function VenueDetail({ slug, onBack }: { slug: string; onBack: () => void }) {
  const [venue, setVenue] = useState<Venue | null>(null);
  const [screenings, setScreenings] = useState<Screening[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .venue(slug)
      .then((d) => {
        setVenue(d.venue);
        setScreenings(d.screenings);
        setError(null);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [slug]);

  return (
    <div className="venue-detail">
      <button className="back" onClick={onBack}>
        ← Back
      </button>

      {loading && <p className="status">Loading venue…</p>}
      {error && <p className="status error">{error}</p>}

      {venue && (
        <>
          <figure className="vd-image">
            <img
              src={venue.image.url}
              alt={
                venue.image.source === "fallback"
                  ? `${venue.name} (category illustration)`
                  : venue.name
              }
              loading="lazy"
              onError={(e) => {
                // On any photo-proxy/load error, swap to the category fallback
                // so the detail view always shows something honest.
                const img = e.currentTarget;
                const fb = fallbackImageUrl(venue.venue_type);
                if (img.src !== window.location.origin + fb && !img.src.endsWith(fb)) {
                  img.src = fb;
                }
              }}
            />
            {venue.image.attribution && (
              <figcaption className="vd-image-credit">{venue.image.attribution}</figcaption>
            )}
          </figure>

          <div className="vd-head">
            <h2>{venue.name}</h2>
            {venue.needs_review && <span className="badge warn">needs review</span>}
          </div>

          <p className="vd-sub">
            {VENUE_TYPE_LABELS[venue.venue_type] ?? venue.venue_type} ·{" "}
            {ENV_LABELS[venue.environment] ?? venue.environment}
            {venue.capacity ? ` · capacity ${venue.capacity.toLocaleString()}` : ""}
          </p>

          <div className="vd-meta">
            {(venue.address || venue.city) && (
              <div>
                📍{" "}
                <a href={googleMapsUrl(venue)} target="_blank" rel="noreferrer">
                  {[venue.address, venue.city].filter(Boolean).join(", ")} — open in Google Maps ↗
                </a>
              </div>
            )}
            {venue.website && (
              <div>
                🔗{" "}
                <a href={venue.website} target="_blank" rel="noreferrer">
                  {venue.website}
                </a>
              </div>
            )}
            <div className="vd-flags">
              <span className="badge">{venue.serves_alcohol ? "Serves alcohol" : "No alcohol"}</span>
              {venue.has_food && <span className="badge">Food</span>}
            </div>
          </div>

          {venue.affiliations.length > 0 && (
            <div className="vd-affils">
              <h3>Supporter hub for</h3>
              {venue.affiliations.map((a, i) => (
                <span key={i} className="badge affil-badge">
                  {a.team ? `${a.team.flag_emoji} ${a.team.name}` : `⚽ ${a.club}`}
                  {a.note ? ` — ${a.note}` : ""}
                </span>
              ))}
            </div>
          )}

          {venue.notes && <p className="vd-notes">{venue.notes}</p>}

          <h3>
            Screenings{" "}
            <span className="muted">
              ({screenings.length})
            </span>
          </h3>
          {screenings.length ? (
            <div className="cards">
              {screenings.map((s) => (
                <ScreeningCard key={s.id} showDate {...screeningCardProps(s)} />
              ))}
            </div>
          ) : (
            <p className="status">
              No screenings yet (this venue may show matches not in the loaded fixture list).
            </p>
          )}

          <p className="vd-provenance">
            {venue.source && (
              <>
                Source:{" "}
                {venue.source_url ? (
                  <a href={venue.source_url} target="_blank" rel="noreferrer">
                    {venue.source}
                  </a>
                ) : (
                  venue.source
                )}{" "}
                ·{" "}
              </>
            )}
            Last updated {new Date(venue.updated_at).toLocaleDateString("en-US")}
          </p>
        </>
      )}
    </div>
  );
}
