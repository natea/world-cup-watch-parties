import type { Match, Screening } from "../types";
import { costLabel, localDateShort, localTime } from "../format";

// DRY listing: group screenings by game, show the matchup once as a header,
// then list the venues showing it beneath. Used by the schedule and the team
// view's "playing" column, where many venues show the same match.

const STAGE_LABELS: Record<string, string> = {
  group: "Group stage",
  r32: "Round of 32",
  r16: "Round of 16",
  qf: "Quarterfinal",
  sf: "Semifinal",
  third: "Third place",
  final: "Final",
};

function matchKey(s: Screening): string {
  // Same teams at the same time = same game.
  return s.match.fifa_match_number != null
    ? `m${s.match.fifa_match_number}`
    : `${s.match.label}|${s.match.kickoff}`;
}

function stageText(match: Match): string {
  if (match.stage === "group") return match.group ? `Group ${match.group}` : "Group stage";
  return STAGE_LABELS[match.stage] ?? match.stage;
}

interface Group {
  match: Match;
  screenings: Screening[];
}

export function MatchGroupList({
  screenings,
  onOpenVenue,
  showDate = false,
}: {
  screenings: Screening[];
  onOpenVenue: (slug: string) => void;
  showDate?: boolean;
}) {
  const groups = new Map<string, Group>();
  for (const s of screenings) {
    const key = matchKey(s);
    if (!groups.has(key)) groups.set(key, { match: s.match, screenings: [] });
    groups.get(key)!.screenings.push(s);
  }
  const ordered = [...groups.values()].sort((a, b) =>
    a.match.kickoff.localeCompare(b.match.kickoff),
  );

  return (
    <div className="match-groups">
      {ordered.map((g) => (
        <section key={matchKey(g.screenings[0])} className="match-group">
          <header className="mg-head">
            <span className="mg-time">
              {showDate && <span className="kickoff-date">{localDateShort(g.match.kickoff)} · </span>}
              {localTime(g.match.kickoff)}
            </span>
            <span className={`mg-label ${g.match.is_resolved ? "" : "tbd"}`}>{g.match.label}</span>
            <span className="mg-stage">{stageText(g.match)}</span>
            {!g.match.is_resolved && <span className="badge tbd-badge">TBD</span>}
          </header>

          <ul className="venue-rows">
            {g.screenings.map((s) => (
              <li key={s.id} className="venue-row">
                <div className="vr-left">
                  <button
                    type="button"
                    className="venue-name venue-link"
                    onClick={() => onOpenVenue(s.venue.slug)}
                  >
                    {s.venue.name}
                  </button>
                  <span className="vr-city">{s.venue.city}</span>
                </div>
                <div className={`vr-badges${costLabel(s.cost_type).includes("·") ? " stack-cost" : ""}`}>
                  <span className="badge cost">{costLabel(s.cost_type)}</span>
                  {s.is_family_friendly && <span className="badge ff">All ages</span>}
                  {s.registration_required && <span className="badge">Registration</span>}
                  {s.entry_guaranteed === false && (
                    <span className="badge warn">Entry not guaranteed</span>
                  )}
                  {s.needs_review && <span className="badge warn">review</span>}
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
