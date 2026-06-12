## Work log

### 2026-06-12 — Security scan (SSRF fix)

Checked: shell/command injection (no `subprocess`/`os.system`/`eval`/`exec`/`pickle`/`yaml.load`
anywhere in the repo), hardcoded secrets/API keys (none found — all loaded via `.env`/`backend/config.py`,
and `app.py` refuses to start in production with a default `SECRET_KEY`), path traversal in file
upload/download/share routes (`app.py`, `backend/routes/waypoints.py`, `backend/routes/logbook/import_.py`),
SQL injection (all queries are parameterized via SQLAlchemy `text()` with bound params), and
insecure defaults (CORS, TLS verification, weak hashing — `werkzeug` password hashing and
`secrets`/`uuid4` are used correctly for tokens).

**Fixed:** SSRF (CWE-918) in the GlideLog "eChronometraż" connector. Any logged-in user could set
an arbitrary `base_url` on a connector via `POST/PUT /logbook/api/connectors[...]`. For `type:
"echrono"`, `EchronoConnector` (`backend/services/connectors/echrono.py`) uses that `base_url`
verbatim to build outbound `httpx` requests (including the user's stored login/password, with
`follow_redirects=True` on the flights fetch), reachable via `/api/connectors/<id>/test` and
`/api/connectors/<id>/sync`. This let any authenticated user make the server send credentialed
HTTP requests to arbitrary hosts (internal services, cloud metadata endpoints, etc.) and observe
the result via the test/sync response or imported flight data.

Fix: added `_validate_base_url()` in `backend/routes/logbook/connectors.py`, enforced in both
`create_connector` and `update_connector` — `base_url` must be `https://` and the hostname must be
`echronometraz.pl` or a subdomain of it (the only domain `EchronoConnector` is designed to talk to).
Invalid values now get a 400 instead of being stored.

**Leave alone:**
- `CORS(app)` in `app.py` is the flask-cors default (no `supports_credentials`), so it doesn't
  expose session-authenticated responses cross-origin — not worth tightening without a concrete
  requirement.
- `email_service.py` interpolates `display_name` into HTML emails unescaped, but the recipient is
  always the account owner (self-XSS in their own inbox) — low severity, not addressed here.
- Other connector types (`leonardo`, `weglide`, `seeyou`, `manual`) don't read `base_url` at all,
  so they weren't in scope for this fix.
