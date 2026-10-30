# Security policy

## Reporting a vulnerability

Please **don't open a public issue** for security problems. Use GitHub's
[private vulnerability reporting](https://github.com/ArpitThakur7/Job-Prediction/security/advisories/new)
instead. You'll get a reply within 7 days, and a fix or a plan within 30.

Include what you found, how to reproduce it, and what an attacker could do with it.

## What this project protects

The app runs on your own machine and handles personal data: your resume, contact
details, job applications, and API keys for LLM providers.

| Part | Listens on | Protection |
|------|-----------|------------|
| Salvo engine | `127.0.0.1:4173` | Loopback only. Rejects requests whose `Host` isn't a loopback name (DNS rebinding) and requests from any browser origin not in `SALVO_ALLOWED_ORIGINS` (default: the local frontend). No stack traces in responses; request bodies capped at 2 MB. |
| Prediction API | `127.0.0.1:8000` | CORS limited to configured origins; JWT auth on user routes. |
| Frontend | `localhost:3000` | No secrets in the browser bundle. |

Tailored resumes and cover letters pass through a truth guard **before** they are
rendered: claims, employers, skills and numbers that don't appear in your master
resume or project bank are removed.

## Keeping secrets out of the repo

- Real values live in `.env` (git-ignored). `.env.example` lists the names only.
- `pre-commit install` enables gitleaks, which blocks commits containing keys or tokens.
- CI runs gitleaks, `pip-audit`, `npm audit`, and CodeQL on every push.

## Supported versions

Only the latest release on `main` receives security fixes.
