"""
Generate an Excalidraw ER diagram of the watch-party DB schema (diagrams-as-code)
plus a faithful PNG preview rendered from the exact same coordinate model, so the
layout can be quality-checked without a live canvas.
"""
import json, random, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

random.seed(7)

# ---- entity model: key columns only (FK/M2M/UQ annotated) ----
ENTITIES = {
    "team": {
        "title": "Team", "color": "#a5d8ff", "x": 40, "y": 360,
        "fields": ["name", "fifa_code  (unique)", "fifa_rank", "group", "confederation"],
    },
    "match": {
        "title": "Match", "color": "#ffec99", "x": 470, "y": 40,
        "fields": ["fifa_match_number  (unique)", "stage", "kickoff  (UTC)", "host_stadium",
                   "home_team \u2192 Team  (FK, null)", "away_team \u2192 Team  (FK, null)",
                   "home/away_placeholder", "bracket_slot"],
    },
    "venue": {
        "title": "Venue", "color": "#b2f2bb", "x": 470, "y": 560,
        "fields": ["name", "slug  (unique)", "venue_type", "environment {in/out/mixed}",
                   "city / region", "latitude / longitude", "serves_alcohol",
                   "default_min_age", "evening_min_age", "evening_cutoff", "capacity"],
    },
    "screening": {
        "title": "Screening   \u2605 atomic unit", "color": "#ffc9c9", "x": 980, "y": 300,
        "fields": ["venue \u2192 Venue  (FK)", "match \u2192 Match  (FK)", "starts_at",
                   "cost_type {enum}", "registration_required", "entry_guaranteed",
                   "age_override", "is_generated", "UQ(venue, match, starts_at)"],
    },
    "affiliation": {
        "title": "VenueAffiliation", "color": "#eebefa", "x": 40, "y": 760,
        "fields": ["venue \u2192 Venue  (FK)", "affiliation_type", "team \u2192 Team  (FK, null)",
                   "club", "valid_from / valid_to"],
    },
    "policy": {
        "title": "ScreeningPolicy", "color": "#eebefa", "x": 980, "y": 760,
        "fields": ["venue \u2192 Venue  (FK)", "policy_type {all/by_team/specific}",
                   "teams \u2194 Team  (M2M)", "matches \u2194 Match  (M2M)", "default_cost_type"],
    },
}

CHAR_W, LINE_H, TITLE_H, PAD = 7.6, 21, 30, 16
for e in ENTITIES.values():
    longest = max([e["title"]] + e["fields"], key=len)
    e["w"] = max(250, int(len(longest) * CHAR_W) + 28)
    e["h"] = TITLE_H + len(e["fields"]) * LINE_H + PAD

def cx(e): return e["x"] + e["w"] / 2
def cy(e): return e["y"] + e["h"] / 2

# ---- edges: (src, dst, label, style)  style in {fk, fk_null, m2m, spine} ----
# points routed manually (absolute coords) to avoid crossing boxes.
def anchor(e, side):
    if side == "L": return (e["x"], cy(e))
    if side == "R": return (e["x"] + e["w"], cy(e))
    if side == "T": return (cx(e), e["y"])
    if side == "B": return (cx(e), e["y"] + e["h"])

E = ENTITIES
EDGES = [
    # the spine: Screening joins Venue + Match
    ("screening", "match", "FK  *..1", "spine",
     [anchor(E["screening"], "T"), (cx(E["screening"]), 200), (anchor(E["match"], "R")[0] + 0, 200), anchor(E["match"], "R")]),
    ("screening", "venue", "FK  *..1", "spine",
     [anchor(E["screening"], "B"), (cx(E["screening"]), cy(E["venue"])), anchor(E["venue"], "R")]),
    # Match -> Team (home/away, nullable)
    ("match", "team", "home/away FK (null)", "fk_null",
     [anchor(E["match"], "L"), (cx(E["team"]), anchor(E["match"], "L")[1]), anchor(E["team"], "T")]),
    # VenueAffiliation -> Venue, Team
    ("affiliation", "venue", "FK *..1", "fk",
     [anchor(E["affiliation"], "R"), (cx(E["venue"]) - 0, anchor(E["affiliation"], "R")[1]), anchor(E["venue"], "B")]),
    ("affiliation", "team", "FK (null)", "fk_null",
     [anchor(E["affiliation"], "T"), anchor(E["team"], "B")]),
    # ScreeningPolicy -> Venue (FK) and M2M to Team, Match
    ("policy", "venue", "FK *..1", "fk",
     [anchor(E["policy"], "L"), (cx(E["venue"]) + 0, anchor(E["policy"], "L")[1]), anchor(E["venue"], "B")[0:1] + (anchor(E["venue"],"B")[1],) and anchor(E["venue"], "B")]),
    ("policy", "match", "M2M", "m2m",
     [anchor(E["policy"], "R"), (E["policy"]["x"] + E["policy"]["w"] + 80, cy(E["policy"])),
      (E["policy"]["x"] + E["policy"]["w"] + 80, 80), (anchor(E["match"], "R")[0], 80), anchor(E["match"], "R")]),
    ("policy", "team", "M2M", "m2m",
     [anchor(E["policy"], "B"), (cx(E["policy"]), E["policy"]["y"] + E["policy"]["h"] + 70),
      (cx(E["team"]), E["policy"]["y"] + E["policy"]["h"] + 70), (cx(E["team"]), E["team"]["y"] + E["team"]["h"]),
      anchor(E["team"], "B")]),
]

STYLE = {
    "spine":   {"color": "#e03131", "width": 3,   "dash": (None, None)},
    "fk":      {"color": "#1971c2", "width": 2,   "dash": (None, None)},
    "fk_null": {"color": "#1971c2", "width": 2,   "dash": (6, 4)},
    "m2m":     {"color": "#9c36b5", "width": 2,   "dash": (2, 4)},
}

# =====================================================================
# 1) PNG preview via matplotlib (faithful to the same coords/routes)
# =====================================================================
MAXX = max(e["x"] + e["w"] for e in E.values()) + 120
MAXY = max(e["y"] + e["h"] for e in E.values()) + 120
fig, ax = plt.subplots(figsize=(MAXX / 80, MAXY / 80), dpi=110)
def fy(y): return MAXY - y  # flip y for matplotlib

for key, e in E.items():
    box = FancyBboxPatch((e["x"], fy(e["y"] + e["h"])), e["w"], e["h"],
                         boxstyle="round,pad=2,rounding_size=10",
                         linewidth=1.6, edgecolor="#1e1e1e", facecolor=e["color"], zorder=2)
    ax.add_patch(box)
    ax.text(e["x"] + 14, fy(e["y"] + 8), e["title"], fontsize=12.5, fontweight="bold",
            va="top", ha="left", zorder=3)
    ax.plot([e["x"] + 8, e["x"] + e["w"] - 8], [fy(e["y"] + TITLE_H - 4)] * 2,
            color="#1e1e1e", lw=0.8, zorder=3)
    for i, f in enumerate(e["fields"]):
        ax.text(e["x"] + 14, fy(e["y"] + TITLE_H + 4 + i * LINE_H), f,
                fontsize=9.2, va="top", ha="left", zorder=3, family="DejaVu Sans")

for src, dst, label, style, pts in EDGES:
    st = STYLE[style]
    xs = [p[0] for p in pts]; ys = [fy(p[1]) for p in pts]
    dash = "solid" if st["dash"][0] is None else (0, st["dash"])
    ax.add_line(Line2D(xs[:-1] + [xs[-1]], ys[:-1] + [ys[-1]], color=st["color"],
                       lw=st["width"], linestyle=dash, zorder=1, solid_capstyle="round"))
    ax.add_patch(FancyArrowPatch((xs[-2], ys[-2]), (xs[-1], ys[-1]),
                 arrowstyle="-|>", mutation_scale=16, color=st["color"], lw=st["width"], zorder=4))
    mid = pts[len(pts) // 2]
    ax.text(mid[0], fy(mid[1]) + 6, label, fontsize=8.4, color=st["color"],
            ha="center", va="bottom", zorder=5,
            bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.85))

legend = [Line2D([0], [0], color="#e03131", lw=3, label="Screening spine (join)"),
          Line2D([0], [0], color="#1971c2", lw=2, label="ForeignKey"),
          Line2D([0], [0], color="#1971c2", lw=2, ls="--", label="ForeignKey (nullable)"),
          Line2D([0], [0], color="#9c36b5", lw=2, ls=":", label="ManyToMany")]
ax.legend(handles=legend, loc="upper left", fontsize=9, framealpha=0.95)
ax.set_title("Watch-Party Finder — Database Schema (ER)", fontsize=15, fontweight="bold")
ax.set_xlim(0, MAXX); ax.set_ylim(0, MAXY); ax.axis("off")
plt.tight_layout()
plt.savefig("schema_preview.png", bbox_inches="tight", facecolor="white")
print("wrote schema_preview.png")

# =====================================================================
# 2) .excalidraw file (openable / importable)
# =====================================================================
def rid(): return "".join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(12))
def nonce(): return random.randint(10**8, 10**9)

elements = []
box_ids = {}
for key, e in E.items():
    bid = rid()
    box_ids[key] = bid
    text = e["title"] + "\n" + "\u2500" * 14 + "\n" + "\n".join(e["fields"])
    tid = rid()
    elements.append({
        "id": bid, "type": "rectangle", "x": e["x"], "y": e["y"], "width": e["w"], "height": e["h"],
        "angle": 0, "strokeColor": "#1e1e1e", "backgroundColor": e["color"], "fillStyle": "solid",
        "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0, "opacity": 100, "groupIds": [],
        "frameId": None, "roundness": {"type": 3}, "seed": nonce(), "version": 1, "versionNonce": nonce(),
        "isDeleted": False, "boundElements": [{"type": "text", "id": tid}], "updated": 1, "link": None, "locked": False,
    })
    elements.append({
        "id": tid, "type": "text", "x": e["x"] + 12, "y": e["y"] + 10, "width": e["w"] - 24, "height": e["h"] - 20,
        "angle": 0, "strokeColor": "#1e1e1e", "backgroundColor": "transparent", "fillStyle": "solid",
        "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0, "opacity": 100, "groupIds": [],
        "frameId": None, "roundness": None, "seed": nonce(), "version": 1, "versionNonce": nonce(),
        "isDeleted": False, "boundElements": None, "updated": 1, "link": None, "locked": False,
        "fontSize": 14, "fontFamily": 3, "text": text, "textAlign": "left", "verticalAlign": "top",
        "containerId": bid, "originalText": text, "lineHeight": 1.4,
    })

for src, dst, label, style, pts in EDGES:
    st = STYLE[style]
    aid = rid()
    x0, y0 = pts[0]
    rel = [[p[0] - x0, p[1] - y0] for p in pts]
    elements[0]  # noqa
    arrow = {
        "id": aid, "type": "arrow", "x": x0, "y": y0,
        "width": max(abs(p[0] - x0) for p in pts), "height": max(abs(p[1] - y0) for p in pts),
        "angle": 0, "strokeColor": st["color"], "backgroundColor": "transparent", "fillStyle": "solid",
        "strokeWidth": st["width"], "strokeStyle": ("solid" if style in ("spine", "fk") else "dashed"),
        "roughness": 0, "opacity": 100, "groupIds": [], "frameId": None, "roundness": {"type": 2},
        "seed": nonce(), "version": 1, "versionNonce": nonce(), "isDeleted": False,
        "boundElements": None, "updated": 1, "link": None, "locked": False,
        "points": rel, "lastCommittedPoint": None,
        "startBinding": {"elementId": box_ids[src], "focus": 0, "gap": 6},
        "endBinding": {"elementId": box_ids[dst], "focus": 0, "gap": 6},
        "startArrowhead": None, "endArrowhead": "arrow",
    }
    elements.append(arrow)
    # bound label on the arrow
    lid = rid()
    arrow["boundElements"] = [{"type": "text", "id": lid}]
    mid = pts[len(pts) // 2]
    elements.append({
        "id": lid, "type": "text", "x": mid[0] - len(label) * 4, "y": mid[1] - 9,
        "width": len(label) * 8, "height": 18, "angle": 0, "strokeColor": st["color"],
        "backgroundColor": "transparent", "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
        "roughness": 0, "opacity": 100, "groupIds": [], "frameId": None, "roundness": None,
        "seed": nonce(), "version": 1, "versionNonce": nonce(), "isDeleted": False, "boundElements": None,
        "updated": 1, "link": None, "locked": False, "fontSize": 13, "fontFamily": 3, "text": label,
        "textAlign": "center", "verticalAlign": "middle", "containerId": aid, "originalText": label,
        "lineHeight": 1.25,
    })

doc = {"type": "excalidraw", "version": 2, "source": "https://excalidraw.com",
       "elements": elements,
       "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"}, "files": {}}
with open("watch_party_schema.excalidraw", "w") as f:
    json.dump(doc, f, indent=2)
# validate it parses
json.load(open("watch_party_schema.excalidraw"))
print(f"wrote watch_party_schema.excalidraw ({len(elements)} elements, valid JSON)")
