## Context

The codebase was already env-driven for the database (`DATABASE_URL` → Postgres, else SQLite) and for hosts/CORS, but had no production server, no static-file strategy, no HTTPS hardening, and no hosting definition. The constraint that shaped every decision: **production must not regress local zero-setup dev** (SQLite, `runserver`, no `collectstatic`, plain HTTP).

## Goals / Non-Goals

- **Goals:** one-command reproducible provisioning (Blueprint); populated DB on deploy; production-grade Django security; a CDN-served SPA pointed at the right API; a repeatable DNS step.
- **Non-goals:** CI/CD pipelines, autoscaling/paid tiers, zero-downtime migrations, serving the SPA from Django, and automating the Render deploy itself (done once via the dashboard).

## Decisions

### Two services + managed Postgres, not a monolith
The React app is deployed as a Render **static site** (global CDN, free TLS) separate from the Django **web service**, rather than serving the built SPA through Django. Keeps the frontend on a CDN and the backend lean. Trade-off: cross-origin calls, so CORS/CSRF must name the frontend origin explicitly (`CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`).

### API URL baked at build time via `fromService`
Vite inlines env vars at build, so the API base must be known when the static site builds. The Blueprint pulls the API service's host (`fromService: { property: host }`) into `API_HOST`, and the build command composes `VITE_API_BASE="https://$API_HOST/api"`. Avoids hardcoding the onrender URL and survives service-name resolution.

### All production behavior guarded behind `if not DEBUG`
WhiteNoise's `CompressedManifestStaticFilesStorage`, SSL redirect, secure cookies, HSTS, and the proxy SSL header are applied only when `DEBUG` is false. In dev, Django's default static storage serves admin/DRF assets straight from source — no `collectstatic`, no "Missing staticfiles manifest entry" errors, plain-HTTP localhost. This is the single most important decision for honoring the non-goal of regressing dev.

### Render's TLS-terminating proxy
Render terminates TLS at its edge and forwards `X-Forwarded-Proto`. `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` lets Django recognize secure requests so `SECURE_SSL_REDIRECT` doesn't loop. `RENDER_EXTERNAL_HOSTNAME` (injected by Render) is appended to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` so the default onrender URL works with no hardcoding.

### Idempotent seeding in the build step
`build.sh` runs `loadreferencedata` + `importwatchparties` on every deploy. Both upsert by natural key (already idempotent), so re-running is safe and guarantees a populated DB without a separate one-off job.

### DNS via Cloudflare REST API, not wrangler
`wrangler` has no DNS commands and its OAuth token lacks a DNS scope. `scripts/cf-dns.sh` calls the Cloudflare API with a Zone:Read + DNS:Edit token to create/update the CNAME, defaulting to DNS-only (grey-cloud) since Render manages the certificate. The record can only be finalized once Render reveals the custom-domain target.

## Risks / Trade-offs

- **Free tier** spins the API down when idle → cold starts; acceptable for a demo, upgrade later.
- **Undocumented service-name → host** resolution: mitigated by `fromService` rather than a literal URL.
- **Cloudflare proxy + Render TLS**: starting DNS-only avoids cert-validation races; proxying can be enabled later with SSL mode "Full".
- **Seeding on every deploy** adds build time; bounded by the small fixture size and idempotency.

## Migration Plan

1. Push repo to GitHub; set `repo:` in `render.yaml` (or connect in dashboard).
2. Render → New → Blueprint → apply (provisions all three resources, runs `build.sh`).
3. Add custom domain to `worldcup-web`; read the CNAME target Render shows.
4. Run `scripts/cf-dns.sh <target>` with a DNS-scoped Cloudflare token.

## Open Questions

- Whether to later proxy the domain through Cloudflare (caching/WAF) once TLS is verified.
- Whether to move seeding out of `build.sh` into a one-time job if the fixture set grows.
