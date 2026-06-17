#!/usr/bin/env python3
"""Generate rights-free category-illustration fallbacks, one per VenueType.

These are honest, generic icons on a soft tile — deliberately NOT photographic,
so a fallback never implies it's a real photo of the venue. Used by the API
serializer (and the frontend) whenever a venue has no licensed place photo.

Produces (into frontend/public/venue-fallbacks/), for each venue_type value:
  - <type>.svg   the authored illustration
  - <type>.png   a rendered raster (1200x800) for <img> consumption

Run:  python3 scripts/make_venue_fallbacks.py
Requires `rsvg-convert` for the PNG step.

The venue_type list mirrors events.models.VenueType; keep them in sync.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "public" / "venue-fallbacks"

W, H = 1200, 800
INK = "#0b1220"
WHITE = "#f8fafc"

# Each venue type: a background gradient pair, an accent, and an inline glyph
# (drawn in a 0 0 100 100 coordinate space, centered on the tile).
VENUE_TYPES = [
    "bar", "brewery", "restaurant", "plaza", "park", "community",
    "hotel", "entertainment", "market", "waterfront", "university", "stadium",
]

PALETTE: dict[str, tuple[str, str, str]] = {
    "bar":           ("#1e293b", "#0f172a", "#fbbf24"),
    "brewery":       ("#3b2f1e", "#1c1505", "#f59e0b"),
    "restaurant":    ("#3b1e2a", "#1c0a12", "#fb7185"),
    "plaza":         ("#13314a", "#0a1c2e", "#38bdf8"),
    "park":          ("#13402a", "#072014", "#34d399"),
    "community":     ("#2a2a3b", "#13131c", "#a78bfa"),
    "hotel":         ("#2a2436", "#150f1f", "#c084fc"),
    "entertainment": ("#3b1340", "#1c0820", "#e879f9"),
    "market":        ("#3b2d13", "#1c1505", "#facc15"),
    "waterfront":    ("#0f3340", "#05181f", "#22d3ee"),
    "university":    ("#1e2a3b", "#0a131f", "#60a5fa"),
    "stadium":       ("#16341e", "#07180c", "#4ade80"),
}

# Glyphs in a 100x100 box. Simple geometric line/shape icons (stroke=accent).
GLYPHS: dict[str, str] = {
    "bar": '<path d="M28 28 H72 L56 52 V72 H64 M56 72 H48" /><line x1="50" y1="52" x2="50" y2="72"/>',
    "brewery": '<rect x="34" y="30" width="26" height="42" rx="3"/><path d="M60 38 H68 a6 6 0 0 1 6 6 v8 a6 6 0 0 1 -6 6 H60"/><line x1="34" y1="42" x2="60" y2="42"/>',
    "restaurant": '<path d="M40 26 V52 a6 6 0 0 0 12 0 V26 M46 52 V74"/><path d="M62 26 q-6 4 -6 14 q0 8 6 10 V74"/>',
    "plaza": '<rect x="26" y="62" width="48" height="6"/><path d="M50 24 L74 62 H26 Z"/><circle cx="50" cy="48" r="5"/>',
    "park": '<path d="M50 28 L66 58 H34 Z"/><path d="M50 40 L62 62 H38 Z"/><line x1="50" y1="58" x2="50" y2="74"/>',
    "community": '<path d="M30 50 L50 32 L70 50"/><rect x="36" y="50" width="28" height="22"/><rect x="46" y="58" width="8" height="14"/>',
    "hotel": '<rect x="32" y="30" width="36" height="42"/><line x1="40" y1="40" x2="44" y2="40"/><line x1="56" y1="40" x2="60" y2="40"/><line x1="40" y1="52" x2="44" y2="52"/><line x1="56" y1="52" x2="60" y2="52"/><rect x="46" y="62" width="8" height="10"/>',
    "entertainment": '<circle cx="50" cy="44" r="18"/><circle cx="44" cy="40" r="2.5" fill="currentColor"/><circle cx="56" cy="40" r="2.5" fill="currentColor"/><circle cx="48" cy="50" r="2.5" fill="currentColor"/><line x1="50" y1="62" x2="50" y2="74"/>',
    "market": '<path d="M30 40 H70 L66 70 H34 Z"/><path d="M30 40 L34 30 H66 L70 40"/><line x1="50" y1="40" x2="50" y2="70"/>',
    "waterfront": '<path d="M30 60 q5 -6 10 0 t10 0 t10 0 t10 0"/><path d="M30 70 q5 -6 10 0 t10 0 t10 0 t10 0"/><path d="M50 30 V52 H40 Z"/><line x1="50" y1="30" x2="62" y2="52" /><line x1="40" y1="52" x2="62" y2="52"/>',
    "university": '<path d="M28 44 L50 34 L72 44 L50 54 Z"/><path d="M38 49 V62 q12 8 24 0 V49"/>',
    "stadium": '<ellipse cx="50" cy="50" rx="24" ry="14"/><ellipse cx="50" cy="50" rx="12" ry="7"/><line x1="26" y1="50" x2="74" y2="50"/>',
}

LABELS: dict[str, str] = {
    "bar": "Bar / pub",
    "brewery": "Brewery / taproom",
    "restaurant": "Restaurant",
    "plaza": "Public plaza",
    "park": "Park / outdoor",
    "community": "Community space",
    "hotel": "Hotel",
    "entertainment": "Entertainment",
    "market": "Food hall / market",
    "waterfront": "Waterfront",
    "university": "University",
    "stadium": "Stadium",
}


def tile_svg(vtype: str) -> str:
    c1, c2, accent = PALETTE[vtype]
    glyph = GLYPHS[vtype]
    label = LABELS.get(vtype, vtype.title())
    font = "'Helvetica Neue', Helvetica, Arial, sans-serif"
    # Center a 360x360 glyph box on the tile.
    gx, gy, gsize = (W - 360) / 2, (H - 420) / 2, 360
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{label} (illustration)">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{c1}"/>
      <stop offset="1" stop-color="{c2}"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#bg)"/>
  <svg x="{gx:.0f}" y="{gy:.0f}" width="{gsize}" height="{gsize}" viewBox="0 0 100 100">
    <g fill="none" stroke="{accent}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" color="{accent}">
      {glyph}
    </g>
  </svg>
  <text x="{W//2}" y="{H-150}" text-anchor="middle" font-family="{font}" font-size="46" font-weight="700" fill="{WHITE}">{label}</text>
  <text x="{W//2}" y="{H-104}" text-anchor="middle" font-family="{font}" font-size="26" font-weight="400" fill="#8aa0bd">Illustration · not a photo of this venue</text>
</svg>
'''


def rsvg(svg_path: Path, png_path: Path, w: int, h: int) -> None:
    subprocess.run(
        ["rsvg-convert", "-w", str(w), "-h", str(h), "-o", str(png_path), str(svg_path)],
        check=True,
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for vtype in VENUE_TYPES:
        svg_path = OUT / f"{vtype}.svg"
        svg_path.write_text(tile_svg(vtype))
        rsvg(svg_path, OUT / f"{vtype}.png", W, H)
    print(f"Wrote {len(VENUE_TYPES)} venue-type fallbacks (svg+png) to {OUT}")


if __name__ == "__main__":
    main()
