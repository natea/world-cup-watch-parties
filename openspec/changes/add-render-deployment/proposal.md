## Why

The app ran only locally (Django `runserver` + Vite dev server on SQLite). There was no path to a hosted, shareable deployment. We want it live at a real URL (`worldcup.stagehopper.app`) on Render.com, on PostgreSQL — which also activates the DB-level family-friendly filter that only runs on Postgres — **without breaking the zero-setup local SQLite workflow** that the README and test suite depend on.

This change was implemented first and is captured here retroactively so the deployment story lives in the spec, not just in commit history.

## What Changes

- Add a **`render.yaml` Blueprint** provisioning three resources: a Django web service (`worldcup-api`, gunicorn) on its default `onrender.com` URL, a Vite static site (`worldcup-web`) served over Render's CDN at the custom domain `worldcup.stagehopper.app`, and a managed **PostgreSQL** database (`worldcup-db`).
- Add **`build.sh`** (the API build step): `uv sync --extra postgres` → `collectstatic` → `migrate` → idempotent seed (`loadreferencedata` + `importwatchparties`), so the database comes up populated on every deploy.
- Make **`config/settings.py` production-ready, all guarded behind `if not DEBUG`** so local dev is untouched: trust `RENDER_EXTERNAL_HOSTNAME` in `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`, serve static assets via WhiteNoise (manifest storage only in prod), and enable HTTPS hardening (SSL redirect, secure cookies, HSTS, proxy SSL header for Render's TLS-terminating proxy).
- Wire the **frontend API base at build time**: the static site reads `VITE_API_BASE` from the API service's host via `fromService`, baking the production API URL into the bundle.
- Add **prod dependencies** `gunicorn` + `whitenoise` (harmless in dev); install the PostgreSQL driver via the existing `postgres` extra at build.
- Add **`scripts/cf-dns.sh`**, a Cloudflare REST API helper to point `worldcup.stagehopper.app` at the Render target (wrangler cannot manage DNS).

## Capabilities

### New Capabilities
- `deployment`: deploying the app to Render.com via an infrastructure-as-code Blueprint (API web service + static site + PostgreSQL), with a production-hardened Django configuration that preserves the local SQLite dev path, and a Cloudflare DNS helper for the custom domain.

## Impact

- **New files:** `render.yaml`, `build.sh`, `scripts/cf-dns.sh`.
- **Edited:** `config/settings.py` (prod-guarded hardening, WhiteNoise, Render host); `pyproject.toml` + `uv.lock` (gunicorn, whitenoise); `.gitignore` (`staticfiles/`); `README.md` (Deployment section).
- **Hosting topology:** frontend at `worldcup.stagehopper.app` (Cloudflare CNAME → Render static site), API at `worldcup-api.onrender.com`, Postgres internal via `DATABASE_URL`.
- **Local dev unchanged:** `runserver` on SQLite, `manage.py check`, and the full pytest suite (21 tests) all pass; no `collectstatic` required locally.
- **Prerequisites:** a GitHub repo connected to Render; a Cloudflare API token (Zone:Read + DNS:Edit) to run the DNS helper; the Render CNAME target is known only after the static site's custom domain is added.
