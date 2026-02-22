# Copilot Instructions — saas-django

This project has two authoritative context files. Read both before generating any code.

## Hard Constraints → `.clauderules`

All non-negotiable rules (package manager, DB, UUID PKs, app structure, security) are
in `.clauderules` at the project root. Always follow them.

## Mission Log → `AGENTS.md`

The phase plan, ADRs, current structure, and running decisions are in `AGENTS.md`.
Use it to understand _where we are_ and _what comes next_.

---

Key rules summary (full detail in `.clauderules`):

- `uv add <pkg>` — never `pip install`
- `uv run <cmd>` — never bare `python manage.py ...`
- PostgreSQL only — never SQLite
- UUID PKs on every model
- `tenant_id` on every tenant-scoped model
- **NO `tenant` FK on `User`** — workspace membership goes through `TenantMembership` join table only
- `TenantMembership` roles: `owner` and `member` only — no `admin` role yet
- Soft deletes on all major models: `is_active`, `deleted_at`, `deleted_by`
- `deleted_by` / `created_by` / `updated_by` are **`UUIDField`** (not `ForeignKey`) — no FK constraint, no implicit index; resolve to a `User` in the service layer
- **Three model categories — always use the correct base class:**
  - **`TenantScopedModel`** (Category A) — all tenant-scoped business data (invoices, docs, etc.);
    extends `TimeStampedAuditModel` and adds `tenant_id` (UUID, indexed)
  - **`TimeStampedAuditModel`** (Category B) — non-tenant audited data (`UserProfile`,
    `TenantMembership`, `Tenant`); full audit trail: `created_by`, `updated_by`, `deleted_by`,
    `created_at`, `updated_at`, `is_active`, `deleted_at` — all standard, not opt-in
  - **Plain `models.Model`** (Category C) — reference/lookup tables only (`Country`, `Language`,
    `Timezone`, `Currency`); no soft-delete, no audit fields
  - **`User` is the sole exception** — extends `AbstractUser` only; has `deleted_at` / `deleted_by`
    but **NO `created_by` / `updated_by` ever** (self-registration circular risk)
- **NEVER hard-delete a `User` or `UserProfile`** — set `is_active = False` only
- Custom `User` model: `AbstractUser`, `USERNAME_FIELD = "email"`, custom `UserManager`
- After first User migration: run `createsuperuser`
- Apps live in `apps/<name>/`, business logic in `services.py` / `selectors.py`
- Reference data (Country, Language, Timezone, Currency) live in `apps/core/` as DB models
  loaded from `pycountry`; `UserProfile` uses FK references to them, not CharFields
- Tailwind + DaisyUI (`corporate` light / `night` dark), follow-system default
- Anti-flash script in `<head>` of `base.html` before any CSS
- Login **failure** → stay on login form with inline error (NOT redirect)
- Login **cancel** link → redirect to homepage
- Registration success → `/profile/complete/` (two-step onboarding: profile → tenant)
- "Do this later" sets `session["skip_profile_gate"]` — does NOT permanently complete profile
- Step 2 (workspace creation) cannot be skipped — minimum requirement for app access
- Workspace creator gets `TenantMembership(role="owner")` — can invite/revoke members at `/settings/members/`
- Owner cannot self-revoke; revoking sets `TenantMembership.is_active = False` (soft-revoke)
- I18N: `en-us` + `nl-be` + `fr-be`; wrap all strings in `{% trans %}` / `_()`
- `<html lang="{{ LANGUAGE_CODE }}">` — never hardcoded
- WCAG AA: `aria-invalid`, `aria-describedby`, skip-to-content link, focus trap in modals, 44px min touch targets
- Stripe and Celery deferred to Phase 6 — do not add earlier
- Run `uv run ruff check --fix && uv run ruff format` after every code change
- Every feature needs tests under `apps/<name>/tests/`
