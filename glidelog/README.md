# GlideLog

Standalone flight-logbook service. Runs as its own container on **port 5001**
but shares the GlidePlan PostgreSQL database and login session.

## How it relates to the main GlidePlan app

- **Database** — shares the same PostgreSQL instance (`postgres_gliding`). The
  logbook tables and `users`/`languages` columns are created by migrations
  `026`–`037`, which live here *and* in the main app against a common
  `schema_migrations` ledger, so applying them is idempotent.
- **Authentication** — GlideLog has **its own login/registration popup** and
  authenticates users directly against the shared `users` table (same schema,
  same `SECRET_KEY`, same email-verification flow as GlidePlan). Visitors are
  no longer redirected to `GLIDEPLAN_URL` to log in. A session created here is
  interchangeable with one created by GlidePlan, since both sign the cookie
  with the same key.
- **i18n** — GlideLog serves its own `/api/i18n/*` endpoints (backed by the
  shared `languages`/`translations` tables) so the UI translates without
  depending on the main app being reachable from the browser.

## Configuration

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | **Must match GlidePlan** — signs the shared session cookie. |
| `DATABASE_URL` | Points at the shared PostgreSQL database. |
| `GLIDEPLAN_URL` | Public URL of the main app, for cross-app navigation links only ("Back to GlidePlan"). |
| `RESEND_API_KEY` / `RESEND_FROM_ADDRESS` | Resend config for sending account-verification codes (share with GlidePlan). |
| `SESSION_COOKIE_DOMAIN` | Set to a shared parent domain (e.g. `.glideplan.org`) only when the two apps are on different subdomains. |
| `GLIDELOG_SCHEDULER_ENABLED` | `0` to disable the daily background flight sync. |

## Running

Via docker-compose from the repo root (starts DB, main app, and GlideLog):

```sh
docker compose up --build glidelog
```

GlideLog is then available at <http://localhost:5001> (redirects to
`/logbook/dashboard`). Unauthenticated visitors get GlideLog's own
login/registration popup — no need to visit the main app first.

Locally without Docker:

```sh
cd glidelog
pip install -r requirements.txt
SECRET_KEY=<same-as-glideplan> \
DATABASE_URL=postgresql://glideplan:changeme_secure_password@localhost:5434/gliding_forecast \
GLIDEPLAN_URL=http://localhost:5000 \
python app.py
```
