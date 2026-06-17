#!/usr/bin/env python3
"""Generate brand assets for the watch-party finder.

Produces (into frontend/public/):
  - favicon.svg        a stylized soccer ball
  - og-image.svg/.png  a 1200x630 social-share card (Open Graph / Twitter)
  - apple-touch-icon.png  180x180 soccer ball on a dark tile

Run:  python3 scripts/make_social_assets.py
Requires `rsvg-convert` for the PNG steps (favicon/OG stay SVG-authored).
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "frontend" / "public"

INK = "#0b1220"      # near-black app background
BLUE = "#3b82f6"     # active-tab accent
WHITE = "#f8fafc"


def pentagon(cx: float, cy: float, r: float, rot_deg: float) -> str:
    """Points string for a regular pentagon, one vertex at rot_deg."""
    pts = []
    for k in range(5):
        a = math.radians(rot_deg + 72 * k)
        pts.append(f"{cx + r * math.cos(a):.2f},{cy + r * math.sin(a):.2f}")
    return " ".join(pts)


def soccer_ball(size: int = 64, stroke: float = 2.0) -> str:
    """A clean stylized soccer ball: white ball, central + 5 rim pentagons."""
    c = size / 2
    R = c - stroke                      # ball radius
    rp = R * 0.30                       # pentagon size
    rim_r = R * 0.64                    # rim pentagons sit between center and edge
    central = pentagon(c, c, rp, -90)   # pointing up
    rims = []
    seams = []
    for k in range(5):
        ang = -54 + 72 * k              # edge-mid directions of central pentagon
        a = math.radians(ang)
        rx, ry = c + rim_r * math.cos(a), c + rim_r * math.sin(a)
        rims.append(pentagon(rx, ry, rp, ang))  # a vertex points outward (classic ball)
    for k in range(5):                  # seams: central vertices out to the rim
        a = math.radians(-90 + 72 * k)
        vx, vy = c + rp * math.cos(a), c + rp * math.sin(a)
        ex, ey = c + R * math.cos(a), c + R * math.sin(a)
        seams.append(f'<line x1="{vx:.2f}" y1="{vy:.2f}" x2="{ex:.2f}" y2="{ey:.2f}"/>')
    patches = "".join(f'<polygon points="{p}"/>' for p in [central, *rims])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">
  <defs><clipPath id="ball"><circle cx="{c}" cy="{c}" r="{R}"/></clipPath></defs>
  <circle cx="{c}" cy="{c}" r="{R}" fill="{WHITE}" stroke="{INK}" stroke-width="{stroke}"/>
  <g clip-path="url(#ball)" fill="{INK}">{patches}</g>
  <g clip-path="url(#ball)" stroke="{INK}" stroke-width="{stroke*0.6:.2f}" fill="none">{"".join(seams)}</g>
  <circle cx="{c}" cy="{c}" r="{R}" fill="none" stroke="{INK}" stroke-width="{stroke}"/>
</svg>
'''


def og_image(w: int = 1200, h: int = 630) -> str:
    ball = 150
    bx, by = 150, 150
    # Embed the soccer ball as a nested <svg> so it scales cleanly.
    ball_svg = soccer_ball(64, 2.0).replace(
        'width="64" height="64"',
        f'x="{bx}" y="{by}" width="{ball}" height="{ball}"')
    font = "'Helvetica Neue', Helvetica, Arial, sans-serif"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0b1220"/>
      <stop offset="1" stop-color="#101c33"/>
    </linearGradient>
  </defs>
  <rect width="{w}" height="{h}" fill="url(#bg)"/>
  <!-- faint pitch motif on the right -->
  <g stroke="#1e2c47" stroke-width="3" fill="none" opacity="0.8">
    <circle cx="{w-150}" cy="{h//2}" r="150"/>
    <line x1="{w-150}" y1="60" x2="{w-150}" y2="{h-60}"/>
  </g>
  {ball_svg}
  <text x="150" y="360" font-family="{font}" font-size="84" font-weight="800" fill="{WHITE}">MA World Cup 2026</text>
  <text x="150" y="450" font-family="{font}" font-size="64" font-weight="800" fill="{BLUE}">Watch-Party Finder</text>
  <text x="152" y="518" font-family="{font}" font-size="33" font-weight="400" fill="#9fb3d1">Where to watch every match across Massachusetts.</text>
  <text x="152" y="562" font-family="{font}" font-size="27" font-weight="500" fill="#6b7f9e">Schedule &#183; Map &#183; By team</text>
  <text x="152" y="600" font-family="{font}" font-size="29" font-weight="700" fill="{WHITE}" opacity="0.85">worldcup.stagehopper.app</text>
</svg>
'''


def rsvg(svg_path: Path, png_path: Path, w: int, h: int) -> None:
    subprocess.run(
        ["rsvg-convert", "-w", str(w), "-h", str(h), "-o", str(png_path), str(svg_path)],
        check=True,
    )


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "favicon.svg").write_text(soccer_ball(64))
    og = PUBLIC / "og-image.svg"
    og.write_text(og_image())
    rsvg(og, PUBLIC / "og-image.png", 1200, 630)
    rsvg(PUBLIC / "favicon.svg", PUBLIC / "apple-touch-icon.png", 180, 180)
    og.unlink()  # keep only the rendered PNG for OG
    print("Wrote favicon.svg, og-image.png, apple-touch-icon.png to", PUBLIC)


if __name__ == "__main__":
    main()
