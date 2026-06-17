import { useEffect, useState } from "react";
import { api } from "../api";
import type { Filters, ScheduleDay } from "../types";
import { localDateLong } from "../format";
import { MatchGroupList } from "./MatchGroupList";

export function ScheduleView({
  filters,
  onOpenVenue,
}: {
  filters: Filters;
  onOpenVenue: (slug: string) => void;
}) {
  const [days, setDays] = useState<ScheduleDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .schedule(filters)
      .then((d) => {
        setDays(d.days);
        setError(null);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [filters]);

  if (loading) return <p className="status">Loading schedule…</p>;
  if (error) return <p className="status error">{error}</p>;
  if (!days.length) return <p className="status">No screenings match these filters.</p>;

  return (
    <div className="schedule">
      {days.map((day) => (
        <section key={day.date} className="day">
          <h2>{localDateLong(day.date)}</h2>
          <MatchGroupList screenings={day.screenings} onOpenVenue={onOpenVenue} />
        </section>
      ))}
    </div>
  );
}
