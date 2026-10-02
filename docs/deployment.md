# Deployment Guidelines

CertAuth is production-ready, but requires standard operational configuration before public exposure.

## 1. Flask Configuration
Never run Flask with `debug=True` in production. CertAuth is configured to look for the `FLASK_ENV` environment variable.
```bash
export FLASK_ENV=production
```

## 2. Web Server Gateway Interface (WSGI)
Do not use the built-in Flask development server in production. Use a production WSGI server like `gunicorn` or `uWSGI`:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```
*(Use 4 worker processes. Adjust based on CPU availability).*

## 3. Reverse Proxy (Nginx / Apache)
Place Nginx or Apache in front of Gunicorn to handle SSL/TLS termination, serve static files (CSS/JS/Images), and protect against DDoS.

## 4. Dependencies & Security
- Keep `GEMINI_API_KEY` entirely out of version control.
- Ensure the `uploads/` directory has strict permissions to prevent executable file uploads or directory traversal attacks. CertAuth enforces extension checks, but OS-level permissions provide defense-in-depth.
- The `blockchain.json` and `certificates.db` should be mounted on persistent, backed-up storage volumes.
- **Authentication secrets at rest.** Email-verification and password-reset tokens are only ever stored as SHA-256 hashes, and TOTP recovery codes are stored the same way, so the database contains no usable bearer tokens. TOTP *secrets* are the exception: they are stored in plaintext in `users.totp_secret`, because the project has no key-management dependency (no `cryptography`, KMS or secret store) and a hand-rolled cipher would be weaker than the honest limitation. Treat `certificates.db` as sensitive material: restrict filesystem/backup access accordingly, and move to column-level encryption (or a KMS) before database read access can be considered non-sensitive.
- **Authentication email links.** `AUTH_BASE_URL` must be set to the canonical HTTPS origin; verification and reset links are always built from it and never from the request `Host` header. If it is missing or not HTTPS, the application logs a warning and sends no email (it does not fall back to an untrusted host).
- **Rate limiting storage.** Authentication endpoints are rate limited in-process (`memory://`). With multiple workers, configure a shared limiter backend (e.g. Redis) so per-account limits such as the second-factor throttle are enforced globally.

## 5. Logging Hygiene
CertAuth uses `logging` instead of `print()`. In production, redirect the stdout logs to a centralized logging system (e.g., ELK stack, Datadog, or AWS CloudWatch) to monitor extraction failure rates, API rate limits, and tamper alerts.
