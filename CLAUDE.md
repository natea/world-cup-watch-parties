# CLAUDE.md — WorldCup Watcher

Guidance for Claude Code working in this repo.

## What this is

Massachusetts World Cup 2026 watch-party finder.

- **Backend:** Django + DRF (the `events/` app), deployed on Render. See [`README.md`](README.md).
- **Frontend:** React + Vite + TypeScript (`frontend/`).
- **Mobile:** Capacitor wraps the web build into native **iOS/Android** apps
  (`frontend/ios`, `frontend/android`). App ID: `app.stagehopper.worldcup`. See
  the "Mobile app (Capacitor)" section of the README.
- **Specs & plans:** `openspec/` (spec-driven changes; archived ones in
  `openspec/changes/archive/`, the living baseline in `openspec/specs/`).

## App Store / iOS submission

When the task involves **App Store submission, App Store Connect, TestFlight, or
iOS release / signing**, follow **[`docs/APPLE_APP_STORE.md`](docs/APPLE_APP_STORE.md)** —
it covers driving App Store Connect via `asc-mcp` and the archive/upload steps.
Also lean on the Apple-platform `axiom-*` skills and the Xcode MCP registered in
`.mcp.json` for native build/run/preview.

## Conventions

- Work on a branch and open a PR; don't commit straight to `main`.
- Before merging, run the backend tests (`uv run pytest`) and the frontend build
  (`cd frontend && bun run build`); for native changes, `bunx cap sync` + an
  Xcode/simulator build.
