import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { Suggestion } from "../types";

const MIN_LEN = 2;
const DEBOUNCE_MS = 150;

export function SearchBox({ onSelect }: { onSelect: (s: Suggestion) => void }) {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<Suggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const boxRef = useRef<HTMLDivElement>(null);

  // Debounced fetch with stale-response cancellation.
  useEffect(() => {
    const query = q.trim();
    if (query.length < MIN_LEN) {
      setItems([]);
      setOpen(false);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      api
        .search(query, controller.signal)
        .then((res) => {
          setItems(res);
          setOpen(true);
          setActive(-1);
        })
        .catch((e) => {
          if ((e as Error).name !== "AbortError") {
            setItems([]);
          }
        });
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [q]);

  // Close on outside click.
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  function choose(s: Suggestion) {
    onSelect(s);
    setQ("");
    setItems([]);
    setOpen(false);
    setActive(-1);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open || !items.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => (i + 1) % items.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => (i <= 0 ? items.length - 1 : i - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      choose(items[active >= 0 ? active : 0]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div className="searchbox" ref={boxRef}>
      <input
        type="search"
        value={q}
        placeholder="Search venues, teams, hubs…"
        aria-label="Search venues, teams, and supporter hubs"
        autoComplete="off"
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => items.length && setOpen(true)}
        onKeyDown={onKeyDown}
      />
      {open && (
        <ul className="search-results" role="listbox">
          {items.length === 0 ? (
            <li className="search-empty">No matches</li>
          ) : (
            items.map((s, i) => (
              <li
                key={`${s.type}:${"slug" in s.target ? s.target.slug : s.target.code}`}
                role="option"
                aria-selected={i === active}
                className={i === active ? "search-item active" : "search-item"}
                onMouseEnter={() => setActive(i)}
                onMouseDown={(e) => {
                  e.preventDefault(); // keep focus; fire before blur
                  choose(s);
                }}
              >
                <span className="si-label">{s.label}</span>
                <span className="si-sub">
                  {s.type === "team" ? "Team" : "Venue"} · {s.sublabel}
                </span>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
