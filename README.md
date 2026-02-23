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
| UI          | Tailwind CSS + DaisyUI 5            |
| I18N        | English (en-us) · Dutch (nl-be) · French (fr-be) |

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

# Install the pre-commit hook (runs ruff + fast tests before every commit)
bash scripts/install-hooks.sh

# Start the dev server
uv run python manage.py runserver
```

Visit <http://127.0.0.1:8000/> for the homepage or <http://127.0.0.1:8000/admin/> for the Django admin.

## Project layout

```
apps/
  core/      — abstract base models (TimeStampedAuditModel, TenantScopedModel)
               + ISO reference data (Country, Language, Timezone, Currency)
               + templatetags (localtime filter, flag_emoji filter)
  tenants/   — Tenant model (workspace root, logo upload)
  users/     — custom User (email login, UUID PK) + UserProfile + signal
               forms, middleware (ProfileCompleteMiddleware), services, selectors,
               views (login, register, onboarding, profile, settings, invite accept),
               url patterns, tests
  pages/     — public homepage, authenticated dashboard, health-check endpoint
config/
  settings/  — base / dev / prod split
  context_processors.py — SITE_NAME, current_theme injected into all templates
locale/
  nl_BE/     — Belgian Dutch translations
  fr_BE/     — Belgian French translations
templates/
  base.html  — DaisyUI shell: anti-flash, navbar, sidebar, bottom nav (mobile)
  users/     — auth, onboarding, profile, settings, invite email templates
  pages/     — homepage, dashboard
```

## Key conventions

- `uv add <pkg>` — never `pip install`
- `uv run <cmd>` — never bare `python manage.py …`
- PostgreSQL only — never SQLite
- UUID PKs on every model; `tenant_id` on every tenant-scoped model
- Soft deletes (`is_active`, `deleted_at`, `deleted_by`) — never hard-delete `User` or `UserProfile`
- All audit actor fields (`created_by`, `updated_by`, `deleted_by`) are `UUIDField`, not FK
- Business logic in `services.py` / `selectors.py` — thin views
- DaisyUI 5 (`form-control` removed — use `fieldset` + `label`)
- `<body>` is `h-screen flex flex-col overflow-hidden` (viewport-locked layout)

See `.clauderules` for the full list of non-negotiable constraints and `AGENTS.md` for the phase plan and ADRs.

## Development commands

```bash
uv run ruff check --fix && uv run ruff format   # lint + format (run after every change)
uv run python manage.py test apps               # full test suite (168 tests)
uv run python manage.py test apps --keepdb --exclude-tag=slow  # fast subset (~17 s)
uv run python manage.py makemigrations          # generate migrations
uv run python manage.py migrate                 # apply migrations
uv run python manage.py load_reference_data     # re-seed ISO data (idempotent)
uv run python manage.py makemessages -l nl_BE   # extract strings for nl_BE
uv run python manage.py makemessages -l fr_BE   # extract strings for fr_BE
uv run python manage.py compilemessages         # compile all .po → .mo
```

## Progress

| Phase | Description                                    | Status      |
| ----- | ---------------------------------------------- | ----------- |
| 0     | Scaffold (uv, settings, Ruff, DB)              | ✅ Done     |
| 1     | Core models, Tenants, Users                    | ✅ Done     |
| 2     | UI Shell (Tailwind + DaisyUI)                  | ✅ Done     |
| 3     | Auth UX (login, register, onboarding, profile) | ✅ Done     |
| 4     | I18N (en-us, nl-be, fr-be)                     | ✅ Done     |
| 5     | Organisation Settings (members, invite, logo)  | ✅ Done     |
| 6     | Billing (Stripe + Celery)                      | 🔲 Deferred |
| 7     | Production hardening                           | 🔲 Deferred |
| 8     | Low priority / future (impersonation, etc.)    | 🔲 Deferred |
