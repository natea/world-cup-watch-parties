import type { Match, Screening } from "../types";
import { costLabel, localDateShort, localTime } from "../format";

// Reused across schedule/team views and inside map popups. `venue` may be
// omitted (map popups already name the venue via the pin).
interface Props {
  match: Match;
  starts_at: string;
  cost_type: string;
  is_family_friendly: boolean;
  registration_required?: boolean;
  entry_guaranteed?: boolean;
  venueName?: string;
  venueSlug?: string;
  onOpenVenue?: (slug: string) => void;
  showDate?: boolean;
  source?: string;
  source_url?: string;
  needs_review?: boolean;
}

export function ScreeningCard(p: Props) {
  return (
    <div className="screening">
      <div className="screening-head">
        <span className="kickoff">
          {p.showDate && <span className="kickoff-date">{localDateShort(p.starts_at)} · </span>}
          {localTime(p.starts_at)}
        </span>
        <span className={`match-label ${p.match.is_resolved ? "" : "tbd"}`}>{p.match.label}</span>
      </div>
      {p.venueName &&
        (p.venueSlug && p.onOpenVenue ? (
          <button
            type="button"
            className="venue-name venue-link"
            onClick={() => p.onOpenVenue!(p.venueSlug!)}
          >
            {p.venueName}
          </button>
        ) : (
          <div className="venue-name">{p.venueName}</div>
        ))}
      <div className="badges">
        <span className="badge cost">{costLabel(p.cost_type)}</span>
        {p.is_family_friendly && <span className="badge ff">All ages</span>}
        {p.registration_required && <span className="badge">Registration</span>}
        {p.entry_guaranteed === false && <span className="badge warn">Entry not guaranteed</span>}
        {!p.match.is_resolved && <span className="badge tbd-badge">TBD matchup</span>}
      </div>
      {(p.source || p.needs_review) && (
        <div className="provenance">
          {p.source && (
            <span>
              Source:{" "}
              {p.source_url ? (
                <a href={p.source_url} target="_blank" rel="noreferrer">
                  {p.source}
                </a>
              ) : (
                p.source
              )}
            </span>
          )}
          {p.needs_review && <span className="review">⚠ needs review</span>}
        </div>
      )}
    </div>
  );
}

export function screeningCardProps(s: Screening) {
  return {
    match: s.match,
    starts_at: s.starts_at,
    cost_type: s.cost_type,
    is_family_friendly: s.is_family_friendly,
    registration_required: s.registration_required,
    entry_guaranteed: s.entry_guaranteed,
    source: s.source,
    source_url: s.source_url,
    needs_review: s.needs_review,
  };
}
