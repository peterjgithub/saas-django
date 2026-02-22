# saas-django

A multi-tenant SaaS starter built with Django 6, PostgreSQL, and `uv`.

## Stack

| Layer       | Technology                          |
| ----------- | ----------------------------------- |
| Language    | Python 3.14                         |
| Framework   | Django ≥ 6.0                        |
| Database    | PostgreSQL (psycopg v3)             |
| Package mgr | `uv`                                |
| Linting     | Ruff (DJ + S + B + E + F + I rules) |
| UI          | Tailwind CSS + DaisyUI (Phase 2+)   |

## Quick start

```bash
# Install dependencies
uv sync

# Copy env template and fill in values
cp .env.example .env

# Apply migrations
uv run python manage.py migrate

# Seed ISO reference data (countries, languages, timezones, currencies)
uv run python manage.py load_reference_data

# Create a superuser
uv run python manage.py createsuperuser

# Start the dev server
uv run python manage.py runserver
```

Visit <http://127.0.0.1:8000/admin/> to verify the admin console.

## Project layout

```
apps/
  core/      — abstract base models (TimeStampedAuditModel, TenantScopedModel)
               + ISO reference data (Country, Language, Timezone, Currency)
  tenants/   — Tenant model (workspace root)
  users/     — custom User (email login, UUID PK) + UserProfile + signal
config/
  settings/  — base / dev / prod split
```

## Key conventions

- `uv add <pkg>` — never `pip install`
- `uv run <cmd>` — never bare `python manage.py …`
- PostgreSQL only — never SQLite
- UUID PKs on every model
- Soft deletes (`is_active`, `deleted_at`, `deleted_by`) — never hard-delete `User` or `UserProfile`
- All audit actor fields (`created_by`, `updated_by`, `deleted_by`) are `UUIDField`, not FK

See `.clauderules` for the full list of non-negotiable constraints and `AGENTS.md` for the phase plan and ADRs.

## Development commands

```bash
uv run ruff check --fix && uv run ruff format   # lint + format
uv run python manage.py test apps               # run all tests
uv run python manage.py makemigrations          # generate migrations
uv run python manage.py load_reference_data     # re-seed ISO data (idempotent)
```

## Progress

| Phase | Description                           | Status      |
| ----- | ------------------------------------- | ----------- |
| 0     | Scaffold (uv, settings, Ruff, DB)     | ✅ Done     |
| 1     | Core models, Tenants, Users           | ✅ Done     |
| 2     | UI Shell (Tailwind + DaisyUI)         | ✅ Done     |
| 3     | Auth UX (login, register, onboarding) | 🔲 Next     |
| 4     | I18N (en-us, nl-be, fr-be)            | 🔲 Planned  |
| 5     | Core SaaS features                    | 🔲 TBD      |
| 6     | Billing (Stripe + Celery)             | 🔲 Deferred |
| 7     | Production hardening                  | 🔲 Deferred |
