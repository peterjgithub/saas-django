# Copilot Instructions — saas-django

This project has two authoritative context files. Read both before generating any code.

## Hard Constraints → `.clauderules`

All non-negotiable rules (package manager, DB, UUID PKs, app structure, security) are
in `.clauderules` at the project root. Always follow them.

## Mission Log → `ai_context.md`

The phase plan, ADRs, current structure, and running decisions are in `ai_context.md`.
Use it to understand _where we are_ and _what comes next_.

---

Key rules summary (full detail in `.clauderules`):

- `uv add <pkg>` — never `pip install`
- `uv run <cmd>` — never bare `python manage.py ...`
- PostgreSQL only — never SQLite
- UUID PKs on every model
- `tenant_id` on every tenant-scoped model
- Soft deletes on all major models: `is_active`, `deleted_at`, `deleted_by`
- Custom `User` model: `AbstractUser`, `USERNAME_FIELD = "email"`, custom `UserManager`
- After first User migration: run `createsuperuser`
- Apps live in `apps/<name>/`, business logic in `services.py` / `selectors.py`
- Tailwind + DaisyUI (`corporate` light / `night` dark), follow-system default
- Anti-flash script in `<head>` of `base.html` before any CSS
- Login failure → homepage; registration success → dashboard (no email confirmation)
- I18N: `en-us` + `nl-be`; wrap all strings in `{% trans %}` / `_()`
- Stripe and Celery deferred to Phase 6 — do not add earlier
- Run `uv run ruff check --fix && uv run ruff format` after every code change
- Every feature needs tests under `apps/<name>/tests/`
- Every feature needs tests under `apps/<name>/tests/`
