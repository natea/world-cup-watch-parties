<!-- Implemented ahead of this retroactive proposal; all boxes reflect work already on disk. -->

## 1. Production dependencies

- [x] 1.1 Add `gunicorn` and `whitenoise` to `pyproject.toml` dependencies; regenerate `uv.lock`
- [x] 1.2 Keep the PostgreSQL driver in the existing `postgres` optional extra (installed at build, not in dev)

## 2. Production-ready settings (dev-safe)

- [x] 2.1 Append `RENDER_EXTERNAL_HOSTNAME` to `ALLOWED_HOSTS`; build `CSRF_TRUSTED_ORIGINS` from env + the Render host
- [x] 2.2 Add WhiteNoise middleware after `SecurityMiddleware`; set `STATIC_ROOT`
- [x] 2.3 Use WhiteNoise `CompressedManifestStaticFilesStorage` only when `not DEBUG` (dev keeps default storage — no `collectstatic`, no manifest errors)
- [x] 2.4 Guard HTTPS hardening behind `not DEBUG`: `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`, secure session/CSRF cookies, HSTS

## 3. Build step

- [x] 3.1 Add executable `build.sh`: `uv sync --frozen --extra postgres` → `collectstatic --no-input` → `migrate` → `loadreferencedata` → `importwatchparties data/watch_parties.json`

## 4. Blueprint

- [x] 4.1 `render.yaml`: `worldcup-api` web service (gunicorn bound to `$PORT`), env (`DATABASE_URL` from DB, generated `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, CORS/CSRF origins, `PYTHON_VERSION`)
- [x] 4.2 `render.yaml`: `worldcup-web` static site — `rootDir: frontend`, build composes `VITE_API_BASE` from the API host via `fromService`, `staticPublishPath: ./dist`, SPA rewrite, custom domain `worldcup.stagehopper.app`
- [x] 4.3 `render.yaml`: `worldcup-db` PostgreSQL database

## 5. DNS helper

- [x] 5.1 Add `scripts/cf-dns.sh` using the Cloudflare REST API (Zone:Read + DNS:Edit) to create/update the custom-domain CNAME, DNS-only by default

## 6. Verification & docs

- [x] 6.1 `manage.py check` clean in dev; `check --deploy` clean with `DEBUG=false`
- [x] 6.2 Full pytest suite passes (21 tests); `runserver` boots on SQLite
- [x] 6.3 Frontend builds with the prod API base inlined into the bundle
- [x] 6.4 Add `staticfiles/` to `.gitignore`; add a Deployment section to `README.md`
