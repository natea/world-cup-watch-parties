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
import { useTheme } from "./useTheme";
import type { Suggestion } from "./types";
import "./App.css";

const TABS = [
  { id: "schedule", label: "Schedule" },
  { id: "map", label: "Map" },
  { id: "team", label: "By team" },
];

// Short, friendly "fixtures updated <when>" label. Returns null for missing/bad input.
function fixturesUpdatedLabel(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return null;
  const diffMs = Date.now() - then.getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return then.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function App() {
  const { filters, setFilter, clear, view, setView, venue, openVenue, closeVenue, anchor, setLocation } =
    useFilters();

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
  const { theme, toggle } = useTheme();
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
          <button
            type="button"
            className="theme-toggle"
            onClick={toggle}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
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
            {view === "map" && (
              <MapView
                filters={filters}
                onOpenVenue={openVenue}
                anchor={anchor}
                setLocation={setLocation}
              />
            )}
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
        <p className="footer-credit">
          WorldCup Watcher is a production of{" "}
          <a href="https://stagehopper.app" target="_blank" rel="noreferrer">
            StageHopper
          </a>
          , Events That Bring People Together.
        </p>
        {fixturesUpdatedLabel(meta?.fixtures_refreshed_at) && (
          <p className="footer-freshness">
            Fixtures updated {fixturesUpdatedLabel(meta?.fixtures_refreshed_at)}
          </p>
        )}
      </footer>
    </div>
  );
}
