# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Personal study-time tracker (Garmin-style weekly goals): Django 6 + DRF + Postgres
API, React 19 + Vite + Tailwind v4 + shadcn/ui SPA. Single user per account,
session auth, no external services.

`README.md` documents usage/deploy; `NOTES.md` is the design-decision log — read
it before changing timer, aggregation, goal or auto-close behavior, and append a
short section there when a non-obvious decision is made.

## Commands

Everything runs through Docker Compose (the only requirement):

```bash
docker compose up                  # db + backend (:8000) + frontend (:5173)
docker compose build backend       # only after changing backend/pyproject.toml
```

Backend (inside the container, or from `backend/` on the host if `uv` is
installed — the compose Postgres publishes 5432):

```bash
docker compose exec backend uv run pytest
docker compose exec backend uv run pytest tracker/tests/test_services.py::TestStreak::test_name
docker compose exec backend uv run python manage.py makemigrations
docker compose exec backend uv run python manage.py createsuperuser
```

Frontend (`frontend/`):

```bash
npm run lint      # oxlint
npm run build     # tsc -b && vite build — the only typecheck gate
```

CI (`.github/workflows/ci.yml`) runs only the backend pytest suite against a
Postgres service container.

## Architecture

**Layering (backend).** `views.py` is thin: parse via a serializer, call a
service, map exceptions to status codes (`ValueError` → 400, `TimerError` → 409,
`LookupError` → 404). All business logic lives in `services.py` and takes `user`
as the first argument and an explicit `now`/`today` — only views call
`timezone.now()` / `timezone.localdate()`, so logic tests need no mocks. Keep new
logic in services, not views or models.

**Metric registry, not schema.** `settings.METRICS` is a dict of metric configs
with two kinds: `session` (duration + weekly goal + streak, e.g. `estudio`) and
`measurement` (point value on a date, e.g. `peso`). Rows reference the metric by
text key, so adding a metric = one dict entry + frontend UI, zero migrations.
`tracker/metrics.py` provides the typed accessors (`get_session_metric` /
`get_measurement_metric` also enforce the kind).

**Lazy timer finalization — no cron, no workers.** `ActiveTimer` persists
`started_at` / `accumulated_seconds` / `running_since`; elapsed time is computed
from timestamps, never ticked. Every view that can observe a timer calls
`services.finalize_expired_timer(...)` first, so an abandoned session is closed
on the next request from whatever data was persisted. Planned sessions close at
exactly the planned duration after `TIMER_GRACE_SECONDS`; no-limit sessions close
after two unanswered `reminder_interval_seconds` intervals, truncated to the last
*confirmed interaction* (mutating actions only — a GET never confirms). Auto-closed
rows keep `close_reason` / `estimated_duration_seconds` / `idle_threshold_seconds`
and stay `needs_review` (derived, not a column) until repaired via
`POST /api/sessions/<id>/review/`. Mutating a timer past its deadline closes it
and returns 409 — the client refetches into the review banner — except
`extend`, which deliberately skips finalization.

**Day attribution.** Sessions store one `date` (the start day) but aggregate
through `services.day_segments`, which splits a timed session at local midnight
proportionally to wall-clock time (pauses are spread evenly; the rounding
remainder goes to the last day). Consequence: `daily_minutes` and `_week_seconds`
aggregate in Python, not SQL, and the 1440-minute daily cap uses the exact same
computation as aggregation. Durations are stored in seconds and summed in seconds
— divide by 60 only at the end.

**Weeks are ISO (Monday-start)** everywhere. `WeeklyGoal(metric, week_start,
minutes)` snapshots the goal per week, so raising the goal never retroactively
breaks earned streaks.

**Auth.** Django's native session auth; login/logout/password pages are
server-rendered templates in `backend/templates/`. The SPA uses the session
cookie + `X-CSRFToken`; `frontend/src/lib/api.ts` redirects to
`/accounts/login/` on 401/403. Every model has a `user` FK and uniqueness
constraints are per-user; views always filter by `request.user`.

**Frontend.** `src/lib/api.ts` is the single typed API client (all fetches go
through its `request` helper). `src/pages/` holds the routes — `/`, `/history`,
`/weight`, `/settings` plus `/training`, `/training/:slug`,
`/training/:slug/phase/:phaseId` and `/training/day/:dayId`. The Spanish paths
the app used to serve (`/historial`, `/peso`, `/ajustes`, `/entrenamiento`,
`/entrenamiento/dia/:dayId`) stay in `App.tsx` as redirects so old bookmarks
keep working; do not add new ones. `src/components/ui/` is shadcn. Accent
theming: `src/lib/theme.ts` sets `data-accent` on `<html>`, values live in
`index.css`; the backend only stores which accent was picked. Browser
notifications (`src/lib/notify.ts`) are reinforcement only — data correctness
never depends on them.

**Serving.** Dev: Vite proxies `/api`, `/accounts`, `/admin`, `/static` to Django
(`OHARA_API_ORIGIN` inside compose). Prod: one image (`Dockerfile` target `prod`)
builds the SPA, serves it via WhiteNoise + a Django catch-all route, and runs
migrations on boot. Settings split: `base.py` (shared, DB from `DATABASE_URL`),
`dev.py` (manage.py/compose default), `prod.py` (wsgi/asgi default, requires
`OHARA_SECRET_KEY`).

## Conventions

- Code, comments, docstrings, commit messages **and URL paths / query params**
  in **English**; user-facing UI copy in **Spanish** (with an English
  translation). The UI language is an i18n concern only — routes never change
  with it, so a Spanish path buys nothing.
- i18n has two layers: frontend dictionaries in `src/lib/i18n.ts` (es default,
  en), backend errors via `gettext` with the Spanish catalog in
  `backend/locale/` — API messages follow the client's `Accept-Language`.
  After editing `django.po`, `compilemessages` runs automatically on container
  start.
- Tunable constants (limits, grace periods, defaults, metric registry) belong in
  `config/settings/base.py`, not inline in services.
- Backend tests live in `backend/tracker/tests/` split by concern (services, api,
  measurements, users); the shared fixtures `user`/`client`/`other_user`/
  `other_client` are in `conftest.py`. Cross-user isolation is expected to be
  covered for new endpoints. There is no frontend test suite.
- Charts use recharts v3: for per-bar adornments use a custom `shape` on `Bar`,
  not `LabelList` (see NOTES.md).


## Training module — where the context lives

`Ohara Training Module/` sits at the repo root but is **gitignored**. It holds
the implementation plan, the data design and the extracted programs.

**Start with `Ohara Training Module/04_claude_code/execution-plan.md`.**

### Hard rule: never read the program JSON files

`Ohara Training Module/02_extracted/*.json` total ~868,000 tokens.
`male-method-1.json` alone is ~283,000.

- For **structure**: read `02_extracted/SCHEMA.md` (~1,800 tokens).
- For **specific values**: run `jq` and print only the result.
  Never use `Read` on those files.

### Hard rule: nothing in that folder gets committed

The JSON files are paid training programs and the repo is public. If a `git add`
picks them up, that's a bug. The folder is in `.gitignore` and stays there.

### Current scope: phases 1 to 5

`exercisedb_next_session/` is **out of scope**: a separate session, later. The MVP ships
without reference images. Do not read it or implement it.

### Continuity across phases

One phase per session. At the end of each, update
`Ohara Training Module/04_claude_code/PROGRESS.md`. At the start of the next,
read it first. `/clear` between phases, not `/compact`.
Full protocol in `04_claude_code/CONTINUITY.md`.

### Documents, in reading order

| File (under `Ohara Training Module/`) | When |
|---|---|
| `04_claude_code/execution-plan.md` | Always first: phases, traps, criteria |
| `04_claude_code/PROGRESS.md` | Starting any phase after the first |
| `03_design/data-model.md` | Before writing models |
| `02_extracted/SCHEMA.md` | Before writing the loader |
| `04_claude_code/CONTINUITY.md` | What to read per phase, how to compact |
| `04_claude_code/deployment-and-data.md` | When touching deploy, migrations or media |
| `03_design/hierarchy-options.md` | Only if questioning the hierarchy |
| `exercisedb_next_session/` | **Never during these phases** |