import type { Filters, Meta, Team } from "../types";

interface Props {
  filters: Filters;
  setFilter: <K extends keyof Filters>(key: K, value: Filters[K]) => void;
  clear: () => void;
  meta: Meta | null;
  teams: Team[];
}

// One control surface, bound to the shared filter set. Every view honors it.
export function FilterBar({ filters, setFilter, clear, meta, teams }: Props) {
  return (
    <div className="filterbar">
      <label>
        Team
        <select
          value={filters.team ?? ""}
          onChange={(e) => setFilter("team", e.target.value || undefined)}
        >
          <option value="">Any</option>
          {teams.map((t) => (
            <option key={t.fifa_code} value={t.fifa_code}>
              {t.flag_emoji} {t.name}
            </option>
          ))}
        </select>
      </label>

      <label>
        Team means
        <select
          value={filters.team_mode ?? "playing"}
          disabled={!filters.team}
          onChange={(e) => setFilter("team_mode", e.target.value as Filters["team_mode"])}
        >
          <option value="playing">…is playing</option>
          <option value="hub">…supporter hub</option>
        </select>
      </label>

      <label>
        Cost
        <select
          value={filters.cost ?? ""}
          onChange={(e) => setFilter("cost", (e.target.value || undefined) as Filters["cost"])}
        >
          <option value="">Any</option>
          <option value="free">Free</option>
          <option value="paid">Paid</option>
        </select>
      </label>

      <label>
        Setting
        <select
          value={filters.environment ?? ""}
          onChange={(e) =>
            setFilter("environment", (e.target.value || undefined) as Filters["environment"])
          }
        >
          <option value="">Any</option>
          <option value="indoor">Indoor</option>
          <option value="outdoor">Outdoor</option>
        </select>
      </label>

      <label>
        Venue type
        <select
          value={filters.venue_type ?? ""}
          onChange={(e) => setFilter("venue_type", e.target.value || undefined)}
        >
          <option value="">Any</option>
          {meta?.venue_types.map((v) => (
            <option key={v.value} value={v.value}>
              {v.label}
            </option>
          ))}
        </select>
      </label>

      <label>
        Region
        <select
          value={filters.region ?? ""}
          onChange={(e) => setFilter("region", e.target.value || undefined)}
        >
          <option value="">Any</option>
          {meta?.regions.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
      </label>

      <label className="check">
        <input
          type="checkbox"
          checked={!!filters.family_friendly}
          onChange={(e) => setFilter("family_friendly", e.target.checked)}
        />
        Family-friendly
      </label>

      <label className="check">
        <input
          type="checkbox"
          checked={!!filters.exclude_bars}
          onChange={(e) => setFilter("exclude_bars", e.target.checked)}
        />
        Exclude bars
      </label>

      <label className="check">
        <input
          type="checkbox"
          checked={!!filters.show_past}
          onChange={(e) => setFilter("show_past", e.target.checked)}
        />
        Show past games
      </label>

      <button className="clear" onClick={clear}>
        Clear
      </button>
    </div>
  );
}
