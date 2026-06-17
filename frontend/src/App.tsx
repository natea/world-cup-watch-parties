import { useEffect, useState } from "react";
import { api } from "./api";
import { useFilters } from "./useFilters";
import type { Meta, Team } from "./types";
import { FilterBar } from "./components/FilterBar";
import { ScheduleView } from "./components/ScheduleView";
import { MapView } from "./components/MapView";
import { TeamView } from "./components/TeamView";
import { VenueDetail } from "./components/VenueDetail";
import { SearchBox } from "./components/SearchBox";
import type { Suggestion } from "./types";
import "./App.css";

const TABS = [
  { id: "schedule", label: "Schedule" },
  { id: "map", label: "Map" },
  { id: "team", label: "By team" },
];

export default function App() {
  const { filters, setFilter, clear, view, setView, venue, openVenue, closeVenue } = useFilters();

  // Switching tabs should leave any open venue detail and show the tab's view.
  const selectTab = (id: string) => {
    closeVenue();
    setView(id);
  };

  // Route a chosen search suggestion into the existing view/filter state.
  const onSearchSelect = (s: Suggestion) => {
    if (s.target.kind === "venue") {
      openVenue(s.target.slug);
    } else {
      closeVenue();
      setFilter("team", s.target.code);
      setView("team");
    }
  };
  const [meta, setMeta] = useState<Meta | null>(null);
  const [teams, setTeams] = useState<Team[]>([]);

  useEffect(() => {
    api.meta().then(setMeta).catch(() => undefined);
    api
      .teams()
      .then((d) => setTeams(d.teams))
      .catch(() => undefined);
  }, []);

  return (
    <div className="app">
      <header>
        <h1>
          ⚽ WorldCup Watcher <span className="brand-sub">· Massachusetts 2026</span>
        </h1>
        <div className="header-row">
          <nav className="tabs">
            {TABS.map((t) => (
              <button
                key={t.id}
                className={view === t.id ? "tab active" : "tab"}
                onClick={() => selectTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </nav>
          <SearchBox onSelect={onSearchSelect} />
        </div>
      </header>

      {!venue && (
        <FilterBar filters={filters} setFilter={setFilter} clear={clear} meta={meta} teams={teams} />
      )}

      <main>
        {venue ? (
          <VenueDetail slug={venue} onBack={closeVenue} />
        ) : (
          <>
            {view === "schedule" && <ScheduleView filters={filters} onOpenVenue={openVenue} />}
            {view === "map" && <MapView filters={filters} onOpenVenue={openVenue} />}
            {view === "team" && (
              <TeamView
                filters={filters}
                teams={teams}
                setFilter={setFilter}
                onOpenVenue={openVenue}
              />
            )}
          </>
        )}
      </main>

      <footer>
        Data is a seed sample · times shown in Massachusetts local time · a finder, not a ticketing
        site.
      </footer>
    </div>
  );
}
