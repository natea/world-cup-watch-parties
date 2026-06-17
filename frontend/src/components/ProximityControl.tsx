import { useState } from "react";
import { api } from "../api";
import { getCurrentPosition } from "../native";
import type { Anchor } from "../types";

// Map-screen-only control: resolve a ZIP / address / device location into the
// map's distance anchor. The user's location is used only to anchor the request.
export function ProximityControl({
  anchor,
  onResolve,
}: {
  anchor: Anchor | null;
  onResolve: (a: Anchor | null) => void;
}) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const query = q.trim();
    if (!query) return;
    setBusy(true);
    setMsg(null);
    try {
      const isZip = /^\d{5}$/.test(query);
      const result = await api.geocode(isZip ? { zip: query } : { address: query });
      if (result) {
        onResolve(result);
        setQ("");
      } else {
        setMsg(
          isZip
            ? "That ZIP isn't in our Massachusetts list — try an address."
            : "Couldn't find that address — try a ZIP code.",
        );
      }
    } catch {
      setMsg("Location lookup failed — try again.");
    } finally {
      setBusy(false);
    }
  }

  async function useMyLocation() {
    setBusy(true);
    setMsg(null);
    try {
      // Native geolocation on device (proper permission flow); browser API on web.
      const { lat, lng } = await getCurrentPosition();
      onResolve({ lat, lng, label: "Your location", precision: "device" });
    } catch {
      setMsg("Couldn't get your location — enter a ZIP or address.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="proximity">
      <form className="prox-form" onSubmit={submit}>
        <input
          type="text"
          value={q}
          placeholder="ZIP or address — find watch parties near you"
          aria-label="ZIP code or address"
          onChange={(e) => setQ(e.target.value)}
        />
        <button type="submit" disabled={busy}>
          {busy ? "…" : "Go"}
        </button>
        <button type="button" className="prox-geo" onClick={useMyLocation} disabled={busy}>
          📍 Use my location
        </button>
      </form>
      {anchor && (
        <div className="prox-active">
          Near <strong>{anchor.label}</strong>
          {anchor.precision === "zip" && " (approx.)"}
          <button type="button" className="prox-clear" onClick={() => onResolve(null)}>
            clear
          </button>
        </div>
      )}
      {msg && <div className="prox-msg">{msg}</div>}
    </div>
  );
}
