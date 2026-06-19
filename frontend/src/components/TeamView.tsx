import { useEffect, useState } from "react";
import { api } from "../api";
import type { Filters, Screening, Team } from "../types";
import { ScreeningCard, screeningCardProps } from "./ScreeningCard";
import { MatchGroupList } from "./MatchGroupList";

// The "alliance" view. The two senses of team are kept visibly distinct:
//   • where my team is PLAYING  (matches featuring the team)
//   • my team's SUPPORTER HUBS  (venues affiliated with the team)
export function TeamView({
  filters,
  teams,
  setFilter,
  onOpenVenue,
}: {
  filters: Filters;
  teams: Team[];
  setFilter: <K extends keyof Filters>(key: K, value: Filters[K]) => void;
  onOpenVenue: (slug: string) => void;
}) {
  const [playing, setPlaying] = useState<Screening[]>([]);
  const [hubs, setHubs] = useState<Screening[]>([]);
  const team = filters.team;

  useEffect(() => {
    if (!team) {
      setPlaying([]);
      setHubs([]);
      return;
    }
    // Query both senses, regardless of the global team_mode, so the view can
    // show them side by side.
    const playFilters = { ...filters, team_mode: "playing" as const };
    const hubFilters = { ...filters, team_mode: "hub" as const };
    api.screenings(playFilters).then((d) => setPlaying(d.screenings));
    api.screenings(hubFilters).then((d) => setHubs(d.screenings));
  }, [team, JSON.stringify(filters)]);

  if (!team) {
    return (
      <div className="teampick">
        <p>Pick a team to follow:</p>
        <div className="teamchips">
          {teams.map((t) => (
            <button key={t.fifa_code} onClick={() => setFilter("team", t.fifa_code)}>
              {t.flag_emoji} {t.name}
            </button>
          ))}
        </div>
      </div>
    );
  }

  const selected = teams.find((t) => t.fifa_code === team);

  return (
    <div className="teamview">
      <h2>
        {selected?.flag_emoji} Following {selected?.name ?? team}
      </h2>
      <div className="twocol">
        <section>
          <h3>Where {selected?.name ?? team} is playing</h3>
          {playing.length ? (
            <MatchGroupList screenings={playing} onOpenVenue={onOpenVenue} showDate />
          ) : (
            <p className="status">No screenings of this team's matches match the filters.</p>
          )}
        </section>
        <section>
          <h3>{selected?.name ?? team} supporter hubs</h3>
          {hubs.length ? (
            <div className="cards">
              {hubs.map((s) => (
                <ScreeningCard
                  key={s.id}
                  venueName={s.venue.name}
                  venueSlug={s.venue.slug}
                  onOpenVenue={onOpenVenue}
                  showDate
                  {...screeningCardProps(s)}
                />
              ))}
            </div>
          ) : (
            <p className="status">
              No Massachusetts supporter hub for {selected?.name ?? team}. Only a handful of
              nations (e.g. USA, Scotland, Brazil, France) have a dedicated local hub. The “playing”
              list shows every venue airing their matches.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
