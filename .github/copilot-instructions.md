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
- **NO `tenant` FK on `User`** — workspace membership goes through `UserProfile` only
- `UserProfile` roles: `admin` and `member` only — no `owner` role; `admin` manages members, billing, and tenant settings
- Soft deletes on all major models: `is_active`, `deleted_at`, `deleted_by`
- `deleted_by` / `created_by` / `updated_by` are **`UUIDField`** (not `ForeignKey`) — no FK constraint, no implicit index; resolve to a `User` in the service layer
- **Three model categories — always use the correct base class:**
  - **`TenantScopedModel`** (Category A) — all tenant-scoped business data (invoices, docs, etc.);
    extends `TimeStampedAuditModel` and adds `tenant_id` (UUID, indexed)
  - **`TimeStampedAuditModel`** (Category B) — non-tenant audited data (`UserProfile`,
    `Tenant`); full audit trail: `created_by`, `updated_by`, `deleted_by`, `created_at`, `updated_at`, `is_active`, `deleted_at` — all standard, not opt-in
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
- Workspace creator gets `role="admin"` on their `UserProfile` — can invite/revoke members at `/settings/users/`
- Admin cannot self-revoke; revoking sets `UserProfile.is_active = False` + `tenant_revoked_at = now()` (soft-revoke); `tenant` FK is never cleared
- I18N: `en-us` + `nl-be` + `fr-be`; wrap all strings in `trans` template tag / `_()`
- Locale directories are `locale/nl/` and `locale/fr/` (intentionally empty neutral bases) + `locale/nl_BE/` and `locale/fr_BE/` (Belgian overrides — all project translations); `LANGUAGES` codes `"nl-be"`/`"fr-be"` trigger Django's `nl_BE → nl` fallback chain automatically
- **I18N — language persistence:** Django 4+ uses a cookie (`django_language`) — `LANGUAGE_SESSION_KEY` no longer exists. `LocaleMiddleware` reads the cookie. Language is switched via Django's built-in `set_language` view at `/i18n/setlang/`.
- **`django.template.context_processors.i18n` is required** — without it `{{ LANGUAGE_CODE }}` always resolves to the static `settings.LANGUAGE_CODE` ("en") instead of the active per-request language.
- **Language selector in navbar:** flag emoji + 2-letter lowercase code (`🇬🇧 en` / `🇧🇪 nl` / `🇧🇪 fr`); POST forms to `set_language`; active language bold in dropdown. Language is **not** in the profile form — navbar only.
- `<html lang="LANGUAGE_CODE">` — use the context variable, never hardcode a language
- WCAG AA: `aria-invalid`, `aria-describedby`, skip-to-content link, focus trap in modals, 44px min touch targets
- Stripe and Celery deferred to Phase 6 — do not add earlier
- Run `uv run ruff check --fix && uv run ruff format` after every code change
- Every feature needs tests under `apps/<name>/tests/`
- **NEVER let Prettier format `templates/`** — it breaks Django template tags (`TemplateSyntaxError`); `.prettierignore` lists `templates/` and `.vscode/settings.json` disables HTML format-on-save — do not remove either
- **NEVER put Django template comments inside or adjacent to script blocks** — the hash-brace comment syntax adjacent to script tags renders as literal visible text in the browser; use JS line comments (`//`) inside scripts instead
- **DaisyUI 5 — we are on DaisyUI 5:**
  - `form-control` is **removed** — use the new `fieldset` + `label` component syntax. `label` goes inside `fieldset`. See: https://daisyui.com/components/fieldset/
  - `btm-nav` renamed to `dock`; direct children styled automatically (no `btm-nav-item`); `btm-nav-label` → `dock-label`
  - `themes.css` must be loaded separately from `daisyui.css` (CDN dev setup)
- **`<body>` must be `h-screen flex flex-col overflow-hidden`** — never `min-h-screen`; this viewport-locks the layout so the sidebar never scrolls away when main content is long; sidebar and main each scroll independently via `overflow-y-auto`
- **Left sidebar:** Dashboard at top; Admin link pinned to bottom via `mt-auto` + `border-t` — only shown to `is_staff` users; Profile link is **NOT** in the sidebar (it lives in the top-right `display_name` dropdown only)
- **Top-right dropdown (authenticated):** `display_name` → Profile + Logout **only** — Admin link is **not** in this dropdown
- `admin.site.site_url = "/dashboard/"` set in `config/urls.py` (one-liner before `urlpatterns`) — no custom `AdminSite` subclass needed
- **Theme toggle:** 3-state cycle `corporate → night → system`; `localStorage` key `theme` always stores the logical pref; for authenticated users the current theme (from `UserProfile.theme`) is injected server-side into the anti-flash script so a fresh browser/incognito gets the right theme on first paint; `POST /theme/set/` (`users:set_theme`) persists preference to DB for authenticated users
- **Profile form fields:** `display_name`, `timezone`, `country`, `theme`, `marketing_emails` — language is switched via the navbar, **not** the profile form; `currency` is **not** on `UserProfile` (it belongs on `Tenant`, deferred to Phase 6)
- **Onboarding step 1 fields:** `display_name` (optional), `timezone` (optional), `country` (optional) — no language field, no avatar upload
- **`except (A, B):` tuple syntax always — this rule has been violated multiple times, check every `except` you write.**
  `except A, B:` is Python 2 syntax that is STILL VALID in Python 3 but silently catches only `A` and binds `B` as the exception variable — a silent logic bug that ruff does not catch.
  ✅ `except (ValueError, TypeError):` — ❌ `except ValueError, TypeError:`
- **After completing each phase** (tests passing, ruff clean): `git add -A && git commit -m "feat: Phase N — <summary>" && git push` — do not wait to be asked
- **Always propose before changing.** Before any non-trivial edit (refactor, architecture change, multi-file change), present a summary of what will change and why, and wait for explicit approval. Trivial single-line fixes may be applied directly.
- **English only in all documentation and instructions.** All code comments, docstrings, `.md` files, commit messages, and AI instruction files must be in English. The product UI is translated; the codebase is English-only.
- **Language prefix in URLs (`i18n_patterns`) deferred — add only when a public CMS is introduced.** All current routes are auth-gated SaaS pages with no SEO value; cookie-based locale (`django_language`) is sufficient. When a headless CMS or public marketing section is added, wrap those routes in `i18n_patterns` (with `prefix_default_language=False`) and add `hreflang` tags. App routes stay prefix-free.
- **`deactivate_member` delegates to `revoke_member`** — they are identical; two names exist only for UI label clarity (Settings UI uses "Deactivate"; legacy endpoint uses "Revoke"). All validation logic lives in `revoke_member` only.
- **Invite email accept flow:** `InviteTokenGenerator` (subclass of `PasswordResetTokenGenerator`) issues a signed URL `/invite/accept/<uidb64>/<token>/`; token invalidates on password change; invited user sets password on accept page, gets logged in, redirected to `/profile/`; exempt from `ProfileCompleteMiddleware` via `/invite/` prefix.
