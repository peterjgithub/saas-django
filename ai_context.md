# Mission Log — saas-django

> **Purpose:** Phase-by-phase build plan and running decisions log.
> Hard constraints live in `.clauderules`. This file is the *why* and *what next*.

---

## Project Identity

| Field | Value |
|---|---|
| Product | Multi-tenant SaaS — Django 6 |
| Stack | Python 3.14, Django >=6.0, PostgreSQL, uv, Ruff |
| Repo | https://github.com/peterjgithub/saas-django |
| Settings module (dev) | `config.settings.dev` |
| Settings module (prod) | `config.settings.prod` |
| Apps root | `apps/` |

---

## Architecture Decisions (ADRs)

| # | Decision | Rationale |
|---|---|---|
| 1 | `uv` as package manager | Fast, lock-file first, no venv friction |
| 2 | Split settings base/dev/prod | Clear env separation, no secrets in dev spill into prod |
| 3 | `django-environ` for secrets | 12-factor, `.env` never committed |
| 4 | `psycopg` (v3) for PostgreSQL | Modern async-ready driver |
| 5 | UUID primary keys on all models | Avoids enumerable IDs, safe for multi-tenant |
| 6 | `tenant_id` on all tenant-scoped models | Foundation for row-level security (RLS) |
| 7 | Services/Selectors pattern | Thin views, testable business logic |
| 8 | Ruff (DJ + S + B + E + F + I rules) | Single tool for lint + format + isort |

---

## Current Structure

```
saas-django/
├── .clauderules          ← Hard constraints for Claude
├── ai_context.md         ← This file (Mission Log)
├── .env                  ← Local secrets (git-ignored)
├── .env.example          ← Template committed to git
├── manage.py
├── pyproject.toml        ← uv + ruff config
├── uv.lock
├── config/
│   ├── settings/
│   │   ├── base.py       ← Shared settings, reads .env
│   │   ├── dev.py        ← DEBUG=True, local DB
│   │   └── prod.py       ← Security hardening
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── apps/                 ← All Django apps live here
```

---

## Phase Plan

### ✅ Phase 0 — Scaffold (DONE)
- [x] uv project init
- [x] Django 6 installed
- [x] Split settings (base / dev / prod)
- [x] PostgreSQL configured via `DATABASE_URL`
- [x] Ruff configured
- [x] `.env` excluded from git
- [x] `apps/` directory created
- [x] Pushed to GitHub

---

### 🔲 Phase 1 — Auth & Tenancy Foundation
Goal: Every subsequent feature can assume a logged-in user that belongs to a tenant.

- [ ] Create `apps/tenants/` — `Tenant` model (UUID PK, name, slug, created_at)
- [ ] Create `apps/users/` — custom `User` model extending `AbstractUser`, linked to `Tenant`
- [ ] `AUTH_USER_MODEL = "users.User"` in `base.py`
- [ ] Initial migrations
- [ ] Basic Django admin registration for both models
- [ ] Tests: tenant creation, user creation, tenant isolation check

---

### 🔲 Phase 2 — Authentication UX
Goal: Users can register, log in, log out, and reset their password.

- [ ] Choose auth approach: `django-allauth` (recommended) or custom
- [ ] Login / logout / register views
- [ ] Password reset flow
- [ ] Email backend configured (console for dev, SMTP/SES for prod)
- [ ] Tests: registration, login, password reset

---

### 🔲 Phase 3 — Subscription & Billing
Goal: Tenants can subscribe to a plan and be billed.

- [ ] Create `apps/billing/` — `Plan`, `Subscription` models
- [ ] Stripe integration (or chosen provider)
- [ ] Webhook handler (idempotent)
- [ ] Subscription status middleware (block access if inactive)
- [ ] Tests: plan assignment, webhook handling

---

### 🔲 Phase 4 — Core SaaS Feature(s)
> To be defined. Add feature specs here as the product takes shape.

---

### 🔲 Phase 5 — Production Hardening
- [ ] CI pipeline: `uv sync` → ruff → tests
- [ ] PostgreSQL RLS for tenant isolation
- [ ] Sentry / error tracking
- [ ] Logging to structured JSON
- [ ] Health check endpoint
- [ ] `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` from env
- [ ] Docker / deployment config

---

## Running Decisions Log

| Date | Decision | Outcome |
|---|---|---|
| 2026-02-21 | Chose `psycopg` v3 over `psycopg2` | Async-ready, actively maintained |
| 2026-02-21 | `.clauderules` added for Claude in VS Code | Hard constraints enforced per-session |

---

## Useful Commands

```bash
# Run dev server
uv run python manage.py runserver

# Make and apply migrations
uv run python manage.py makemigrations
uv run python manage.py migrate

# Open Django shell
uv run python manage.py shell

# Lint + format
uv run ruff check --fix && uv run ruff format

# Run tests
uv run python manage.py test

# Add a dependency
uv add <package>

# Sync environment to lock file
uv sync
```
