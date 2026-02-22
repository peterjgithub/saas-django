# Mission Log — saas-django

> **Purpose:** Phase-by-phase build plan and running decisions log.
> Hard constraints (non-negotiable rules) live in `.clauderules`. This file is the _why_ and _what next_.

---

## Project Identity

| Field                  | Value                                           |
| ---------------------- | ----------------------------------------------- |
| Product                | Multi-tenant SaaS — Django 6                    |
| Stack                  | Python 3.14, Django >=6.0, PostgreSQL, uv, Ruff |
| Repo                   | https://github.com/peterjgithub/saas-django     |
| Settings module (dev)  | `config.settings.dev`                           |
| Settings module (prod) | `config.settings.prod`                          |
| Apps root              | `apps/`                                         |

---

## Architecture Decisions (ADRs)

| #   | Decision                                                                                        | Rationale                                                                                                                                                                                                                                                                                                                 |
| --- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `uv` as package manager                                                                         | Fast, lock-file first, no venv friction                                                                                                                                                                                                                                                                                   |
| 2   | Split settings base/dev/prod                                                                    | Clear env separation, no secrets in dev spill into prod                                                                                                                                                                                                                                                                   |
| 3   | `django-environ` for secrets                                                                    | 12-factor, `.env` never committed                                                                                                                                                                                                                                                                                         |
| 4   | `psycopg` (v3) for PostgreSQL                                                                   | Modern async-ready driver                                                                                                                                                                                                                                                                                                 |
| 5   | UUID primary keys on all models                                                                 | Avoids enumerable IDs, safe for multi-tenant                                                                                                                                                                                                                                                                              |
| 6   | `tenant_id` on all tenant-scoped models                                                         | Foundation for row-level security (RLS)                                                                                                                                                                                                                                                                                   |
| 7   | Soft deletes (`is_active`, `deleted_at`, `deleted_by`)                                          | Safe data recovery, audit trail, no hard deletes                                                                                                                                                                                                                                                                          |
| 8   | `created_by`/`updated_by` are standard in `TimeStampedAuditModel`; `User` is the sole exception | Circular risk is specific to `User` only (self-registration creates the UUID in the same transaction). Every other model's acting user is committed before the record is written — no circular risk. `User` omits these fields entirely.                                                                                  |
| 9   | Services/Selectors pattern                                                                      | Thin views, testable business logic                                                                                                                                                                                                                                                                                       |
| 10  | Ruff (DJ + S + B + E + F + I rules)                                                             | Single tool for lint + format + isort                                                                                                                                                                                                                                                                                     |
| 11  | Custom `User` model with `email` as `USERNAME_FIELD`                                            | Email-based auth from day one, no username field                                                                                                                                                                                                                                                                          |
| 12  | `UserProfile` as separate `OneToOneField` model                                                 | Keeps `User` minimal; profile fields never touch auth/registration forms                                                                                                                                                                                                                                                  |
| 13  | `display_name` nullable, auto-derived from email                                                | Friendly name without forcing input at registration                                                                                                                                                                                                                                                                       |
| 14  | Browser-detected locale/timezone on registration                                                | Best-effort UX, always user-overridable in profile                                                                                                                                                                                                                                                                        |
| 15  | Store UTC everywhere, display in user's local tz                                                | Single source of truth in DB; `UserProfile.timezone` drives display                                                                                                                                                                                                                                                       |
| 16  | `zoneinfo` (stdlib) for timezone conversion                                                     | No extra dependency; Python 3.9+ built-in                                                                                                                                                                                                                                                                                 |
| 17  | Tailwind CSS + DaisyUI (corporate/night themes)                                                 | Rapid, consistent UI with zero custom CSS overhead                                                                                                                                                                                                                                                                        |
| 18  | Follow-system as default theme                                                                  | Respects OS preference; stored in `localStorage`                                                                                                                                                                                                                                                                          |
| 19  | Anti-flash script in `<head>`                                                                   | Prevents white flash on dark-mode page load                                                                                                                                                                                                                                                                               |
| 20  | Bottom Nav / Full-Screen Overlay on mobile                                                      | Better UX than top-right hamburger                                                                                                                                                                                                                                                                                        |
| 21  | Navbar auth control = display_name dropdown                                                     | "Leave" replaced with named user + Profile/Logout menu                                                                                                                                                                                                                                                                    |
| 22  | I18N: `en-us` + `nl-be` + `fr-be`                                                               | Belgian Dutch and Belgian French as second and third locales from the start                                                                                                                                                                                                                                               |
| 23  | Stripe deferred to Phase 6                                                                      | Auth and UI foundations must be solid first                                                                                                                                                                                                                                                                               |
| 24  | Background task queue (Celery + Redis)                                                          | Required for Stripe webhooks; no blocking web requests                                                                                                                                                                                                                                                                    |
| 25  | Registration → profile page (not dashboard)                                                     | Forces intentional onboarding; profile gate ensures completeness before app access                                                                                                                                                                                                                                        |
| 26  | `ProfileCompleteMiddleware` + `profile_completed_at`                                            | Single flag drives the gate; exempt list keeps logout/health reachable; `next` param preserves intent                                                                                                                                                                                                                     |
| 27  | Two-step onboarding: Profile → Tenant                                                           | Separates personal setup from workspace setup; both can be skipped via session flag                                                                                                                                                                                                                                       |
| 28  | "Do this later" sets session flag, not DB flag                                                  | Avoids permanently marking a profile complete when the user skips; re-prompts next session                                                                                                                                                                                                                                |
| 29  | Reference data (Country/Language/Timezone/Currency) as DB models                                | FK references allow cross-filtering (e.g. languages for a country); data from `pycountry` + `zoneinfo`                                                                                                                                                                                                                    |
| 30  | `UserProfile` localisation fields use FK not CharField                                          | Referential integrity, consistent display names, and filterable dropdowns without duplication                                                                                                                                                                                                                             |
| 31  | Never hard-delete User or UserProfile                                                           | Silent cascade risk; `is_active = False` is the only safe deactivation path                                                                                                                                                                                                                                               |
| 32  | `marketing_emails` only — no `product_updates`                                                  | Single opt-in field sufficient for now; extend when explicit consent categories are needed                                                                                                                                                                                                                                |
| 33  | WCAG AA accessibility built in from day one                                                     | aria-invalid + aria-describedby on all forms; skip-link; focus trap in modals; 44px min targets                                                                                                                                                                                                                           |
| 34  | Membership on `UserProfile` directly, not a join table                                          | One user, one tenant — hard product constraint. `UserProfile.tenant` FK + `role` + `tenant_joined_at` + `tenant_revoked_at` replaces `TenantMembership` entirely. Simpler schema, no extra join, audit trail preserved via `tenant_revoked_at` + `is_active`. A user needing a different org must register a new account. |
| 35  | `Tenant` has only `organization` + UUID PK + base fields                                        | `name` was redundant with `organization`; `slug` deferred — UUID is sufficient for isolation until tenant-scoped URLs are needed                                                                                                                                                                                          |
| 36  | `UserProfile` roles: `admin` and `member` only                                                  | `admin` manages members, billing, and tenant settings; `member` = read access only. "Admin" reflects the permission set, not just creation history. Broader role granularity deferred to Phase 5+.                                                                                                                        |
| 37  | Audit actor fields (`deleted_by`, `created_by`, `updated_by`) use `UUIDField` not `ForeignKey`  | No FK constraint check on every write; no implicit index; no circular dependency on `User`; no JOIN overhead when reading audit data. Integrity enforced at the service layer. Add `db_index` per-model only if a query pattern warrants it.                                                                              |
| 38  | `<body>` is `h-screen overflow-hidden` (viewport-locked layout)                                 | Locks the entire layout to the viewport height so the sidebar never scrolls away when main content is long. Sidebar and main content each scroll independently via `overflow-y-auto` on their own containers.                                                                                                             |
| 39  | Profile link NOT in left sidebar — top-right dropdown only                                      | Sidebar contains: Dashboard (top) + Admin link pinned to bottom via `mt-auto` (staff only). Profile/Logout live exclusively in the `display_name` dropdown in the top-right navbar. Avoids duplicate navigation, keeps sidebar focused on app sections.                                                                   |
| 40  | Admin link pinned to sidebar bottom, `{% if user.is_staff %}` guard everywhere                  | Admin link shown in: left sidebar (bottom, `mt-auto` + `border-t`) and mobile overlay. NOT in the top-right dropdown. Only visible to users where `user.is_staff = True`.                                                                                                                                                 |
| 41  | `admin.site.site_url = "/dashboard/"` in `config/urls.py`                                       | Django admin's "View site" button redirects to `/dashboard/` instead of `/`. One-liner before `urlpatterns`; no custom `AdminSite` subclass needed.                                                                                                                                                                       |
| 42  | 3-state theme toggle: `corporate → night → system`                                              | Replaces the binary light/dark toggle. `"system"` reads `prefers-color-scheme` at runtime; stored as the logical pref in `localStorage` (never resolved). Cycle: `corporate → night → system → corporate …`.                                                                                                               |
| 43  | Server-side theme seed in anti-flash script for authenticated users                             | `{{ current_theme }}` (from `UserProfile.theme` via context processor) injected into the anti-flash `<script>`. Auth user's saved pref wins over any stale `localStorage` value so incognito / fresh browser gets the right theme on first paint. Unauthenticated: `localStorage` only.                                    |
| 44  | `POST /theme/set/` endpoint persists theme to `UserProfile` for authenticated users             | AJAX endpoint (`users:set_theme`). Called by the toggle JS on every click. Returns `{"ok": true, "theme": "..."}`. Unauthenticated requests return `200 ok` but make no DB write. `/theme/set/` is in `_ALWAYS_EXEMPT` so the profile gate never intercepts it.                                                           |

---

## Current File Structure

```
saas-django/
├── .clauderules              ← Hard constraints (rules file for Claude)
├── .github/
│   └── copilot-instructions.md  ← Copilot context summary
├── AGENTS.md                 ← This file (Mission Log)
├── .env                      ← Local secrets (git-ignored)
├── .env.example              ← Committed template
├── manage.py
├── pyproject.toml            ← uv + ruff config
├── uv.lock
├── templates/                ← ✅ Phase 2 — project-level templates
│   ├── base.html             ← DaisyUI shell: anti-flash, navbar, sidebar, bottom nav
│   ├── pages/
│   │   ├── home.html         ← public homepage
│   │   └── dashboard.html    ← authenticated dashboard placeholder
│   └── partials/             ← (reserved for future partials)
├── config/
│   ├── settings/
│   │   ├── base.py           ← Shared settings, reads .env
│   │   ├── dev.py            ← DEBUG=True, local DB
│   │   └── prod.py           ← Security hardening
│   ├── context_processors.py ← ✅ Phase 2 — injects SITE_NAME, current_theme
│   ├── urls.py               ← ✅ Phase 2 — wires /, /dashboard/, /health/, user stubs
│   ├── wsgi.py
│   └── asgi.py
└── apps/
    ├── core/                 ← ✅ Phase 1 — abstract base models + reference data
    │   ├── admin.py
    │   ├── apps.py
    │   ├── management/
    │   │   └── commands/
    │   │       └── load_reference_data.py
    │   ├── migrations/
    │   ├── models.py         ← TimeStampedAuditModel, TenantScopedModel, Country,
    │   │                        Language, Timezone, Currency
    │   ├── templatetags/     ← ✅ Phase 2
    │   │   └── tz_tags.py    ← localtime filter (UTC → user timezone)
    │   ├── tests/
    │   └── views.py
    ├── tenants/              ← ✅ Phase 1 — Tenant model
    │   ├── admin.py
    │   ├── apps.py
    │   ├── migrations/
    │   ├── models.py         ← Tenant(TimeStampedAuditModel)
    │   ├── tests/
    │   └── views.py
    ├── users/                ← ✅ Phase 1 — custom User + UserProfile + signal
    │   ├── admin.py
    │   ├── apps.py
    │   ├── forms.py          ← ✅ Phase 3 — LoginForm, RegisterForm, ProfileForm,
    │   │                        OnboardingStep1Form, TenantCreateForm, InviteMemberForm
    │   ├── middleware.py     ← ✅ Phase 3 — ProfileCompleteMiddleware
    │   ├── migrations/
    │   ├── models.py         ← User(AbstractUser), UserProfile(TimeStampedAuditModel)
    │   ├── services.py       ← ✅ Phase 3 — register_user, complete_profile,
    │   │                        create_tenant_for_user, invite_member, revoke_member,
    │   │                        reengage_member
    │   ├── signals.py        ← post_save → auto-create UserProfile
    │   ├── tests/
    │   │   ├── test_auth.py  ← ✅ Phase 3 — login, register, onboarding, profile tests
    │   │   ├── test_members.py ← ✅ Phase 3 — invite, revoke, re-engage tests
    │   │   └── test_models.py ← Phase 1 model tests
    │   ├── urls.py           ← ✅ Phase 3 — full auth URL patterns
    │   └── views.py          ← ✅ Phase 3 — login, logout, register, onboarding,
    │                            profile, members, account_revoked, password reset
    ├── pages/                ← ✅ Phase 2 — homepage, dashboard, health check
    │   ├── apps.py
    │   ├── migrations/
    │   ├── tests/
    │   ├── urls.py           ← pages:home, pages:dashboard
    │   └── views.py          ← home(), dashboard(), health()
    └── billing/              ← (Phase 6, deferred)
```

```
templates/
    ├── base.html             ← ✅ Phase 2 + Phase 3 polish — DaisyUI shell:
    │                            anti-flash, navbar (display_name dropdown — Profile+Logout only),
    │                            left sidebar (Dashboard + Admin-at-bottom for is_staff),
    │                            mobile overlay, h-screen body layout
    ├── pages/
    │   ├── home.html         ← public homepage
    │   └── dashboard.html    ← authenticated dashboard
    ├── partials/             ← (reserved for future partials)
    └── users/                ← ✅ Phase 3 — all auth + onboarding templates
        ├── login.html
        ├── register.html
        ├── onboarding_step1.html
        ├── onboarding_step2.html
        ├── profile.html
        ├── members.html
        ├── account_revoked.html
        ├── password_reset.html
        ├── password_reset_done.html
        ├── password_reset_confirm.html
        └── password_reset_complete.html
```

---

## Shared Base Model Convention

All major data models extend one of two abstract base classes (both defined in
`apps/core/models.py`). Choose the correct one — do not mix them.

### Category A — `TenantScopedModel` (tenant-scoped business data)

Extends `TimeStampedAuditModel` and adds `tenant_id`. Use for every business model
that belongs to a workspace: invoices, documents, tasks, etc.

```python
class TenantScopedModel(TimeStampedAuditModel):
    tenant_id  = models.UUIDField(db_index=True)
    class Meta:
        abstract = True
```

### Category B — `TimeStampedAuditModel` (non-tenant audited data)

Use for system-level models with no workspace scope: `UserProfile`, `Tenant`, and
any future system-wide record.

```python
class TimeStampedAuditModel(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField(null=True, blank=True)   # acting user UUID — no FK
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.UUIDField(null=True, blank=True)   # acting user UUID — no FK
    is_active  = models.BooleanField(default=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.UUIDField(null=True, blank=True)   # acting user UUID — no FK
    class Meta:
        abstract = True
```

### Category C — Reference / lookup tables

Plain `models.Model`. No soft-delete, no audit fields, no UUID PK. Applies to
`Country`, `Language`, `Timezone`, `Currency` — controlled vocabulary, loaded once.

### Exception: `User`

`User` extends `AbstractUser` only. It has `is_active` (from `AbstractUser`),
`deleted_at`, and `deleted_by` added directly — but **NO `created_by` or `updated_by`
ever**. Self-registration creates the UUID in the same transaction; there is no prior
actor to record. This is the **only** model in the codebase that omits these fields.

> **Hybrid integrity:** All actor fields (`created_by`, `updated_by`, `deleted_by`) use
> `UUIDField` — no FK constraint, no implicit index, no JOIN overhead. There is **no
> circular risk on any model except `User` itself.** For every other model the acting
> user's row is committed before the record being written. Integrity is enforced at the
> service layer (`request.user.pk` is always a valid UUID). Add `db_index` on an actor
> field only if a concrete query pattern warrants it.

---

## Phase Plan

### ✅ Phase 0 — Scaffold (DONE)

- [x] uv project init, Django 6 installed
- [x] Split settings (base / dev / prod)
- [x] PostgreSQL configured via `DATABASE_URL`
- [x] Ruff configured (DJ + S + B + E + F + I)
- [x] `.env` excluded from git, `.env.example` committed
- [x] `apps/` directory created
- [x] `.clauderules` + `AGENTS.md` wired to Claude + Copilot in VS Code
- [x] Pushed to GitHub

---

### ✅ Phase 1 — Foundation: Core App, Tenants & Users (DONE)

**Goal:** Establish the shared base model, tenant model, and email-based custom User — everything else depends on this.

#### 1a — Core app (shared primitives)

- [x] `uv run python manage.py startapp core` → move to `apps/core/`
- [x] Create `TimeStampedAuditModel` and `TenantScopedModel` abstract base classes in `apps/core/models.py`
      (see Shared Base Model Convention above)
- [x] Register `apps.core` in `INSTALLED_APPS`

#### 1b — Reference Data (ISO tables)

- [x] In `apps/core/models.py`: create `Country`, `Language`, `Timezone`, `Currency`
      models as specified in `.clauderules §5b`
- [x] `ManyToManyField` relationships:
  - `Language.countries` → `Country`
  - `Timezone.countries` → `Country`
  - `Currency.countries` → `Country`
- [x] Management command: `apps/core/management/commands/load_reference_data.py`
  - `uv add pycountry`
  - Loads all countries, languages, currencies from `pycountry`
  - Loads timezones from `zoneinfo.available_timezones()` with UTC offset calculation
  - Idempotent (`update_or_create`)
- [x] Run after migrations: `uv run python manage.py load_reference_data`
      → 249 countries, 7923 languages, 178 currencies, 598 timezones seeded;
      423 TZ↔Country, 249 Currency↔Country, 305 Language↔Country links
- [x] Tests: command creates records, FK filtering works (languages for Belgium, etc.)

#### 1c — Tenants

- [x] `apps/tenants/` — `Tenant` model only (no `TenantMembership`):
  - `id` — UUID PK
  - `organization` — `CharField(max_length=200)` — workspace / company name (required)
  - Extends `TimeStampedAuditModel` — Tenant IS the root; it has no `tenant_id` on itself
  - No `slug` — the UUID PK is the identifier; add a slug later if tenant-scoped URLs are needed
- [x] Admin registration
- [x] Tests: tenant creation, `organization` required

#### 1d — Custom User

- [x] `apps/users/` — `User(AbstractUser)`:
  - `USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = []`
  - Custom `UserManager` (`create_user`, `create_superuser`) using email
  - Extends `AbstractUser` directly — **NOT** `TimeStampedAuditModel`
  - Add `deleted_at` and `deleted_by` (UUIDField) directly on `User` (no `created_by`/`updated_by`)
  - **No `tenant` FK on `User`** — tenant membership lives on `UserProfile` (see Phase 1e)
- [x] Set `AUTH_USER_MODEL = "users.User"` in `config/settings/base.py`
- [x] Migrations (`makemigrations` → `migrate`)
- [x] `createsuperuser` (email-based) — done 2026-02-22
- [x] Admin registration — all models visible: Users, User profiles, Tenants, Countries,
      Currencies, Languages, Timezones
- [x] Tests: user creation, email uniqueness, superuser creation

#### 1e — UserProfile

> **Depends on 1b** (core reference tables must be migrated first) and **1d** (User model).

- [x] `UserProfile(TimeStampedAuditModel)` in `apps/users/models.py`:
  - `user` — `OneToOneField(User, related_name="profile")`
  - `display_name` — `CharField(max_length=100, blank=True, null=True)`
  - `language` — `ForeignKey("core.Language", null=True, blank=True, on_delete=SET_NULL)`
  - `timezone` — `ForeignKey("core.Timezone", null=True, blank=True, on_delete=SET_NULL)`
  - `country` — `ForeignKey("core.Country", null=True, blank=True, on_delete=SET_NULL)`
  - `currency` — `ForeignKey("core.Currency", null=True, blank=True, on_delete=SET_NULL)`
  - `theme` — `CharField` choices: `corporate` / `night` / `system`; default `system`
  - `marketing_emails` — `BooleanField(default=False)` — newsletters opt-in only
  - `profile_completed_at` — `DateTimeField(null=True, blank=True)` — `None` until the
    user saves the profile form for the first time; drives the onboarding gate
  - `tenant` — `ForeignKey("tenants.Tenant", null=True, blank=True, on_delete=SET_NULL)` —
    set once during onboarding/invitation; **never nulled out after assignment**
  - `role` — `CharField` choices: `admin` / `member`; blank when `tenant` is null
  - `tenant_joined_at` — `DateTimeField(null=True, blank=True)`
  - `tenant_revoked_at` — `DateTimeField(null=True, blank=True)` — set on revocation,
    cleared on re-engagement; `is_active=False` while revoked
- [x] **NEVER hard-delete a `UserProfile`.** Soft-delete only (`is_active = False`).
- [x] `post_save` signal on `User` → auto-create `UserProfile`
- [x] Auto-populate `display_name` from email:
  - Take local-part (left of `@`); if it contains `.`, take left of first `.`
  - e.g. `peter.janssens@acme.com` → `peter`
- [x] Accept hidden fields `tz_detect` and `lang_detect` on the registration form
      (populated via JS `Intl.DateTimeFormat().resolvedOptions().timeZone` and
      `navigator.language`) to pre-fill `timezone` and `language`
- [x] `UserProfile` is NEVER part of the registration form
- [x] Tests: profile auto-created, display_name derivation, signal idempotency,
      `profile_completed_at` is `None` on creation

---

### ✅ Phase 2 — UI Shell: Tailwind, DaisyUI & Base Templates (DONE)

**Goal:** All subsequent pages inherit a consistent, themed, accessible base layout.

- [x] Install Tailwind CSS + DaisyUI (via `django-tailwind` + CDN for dev — no npm build step)
- [x] Configure DaisyUI themes: `corporate` (light) + `night` (dark); default: follow system
- [x] Create `templates/base.html`:
  - Anti-flash `<script>` in `<head>` before any CSS
  - DaisyUI top navbar (desktop) and bottom navigation / full-screen overlay (mobile)
  - **Desktop navbar:** logo-left / nav-centre / controls-right
    - Controls: theme toggle, auth control
    - **Unauthenticated auth control:** "Get started" button → login page
    - **Authenticated auth control:** `display_name` (or email) as DaisyUI dropdown;
      items: "Profile" → `/profile/`, "Log out" → `/logout/`
  - **Mobile:** bottom nav + full-screen DaisyUI modal overlay (hamburger opens it)
  - `<nav>` tag; hamburger with `aria-label="Toggle menu"`
  - Left-side sidebar (authenticated only): "Dashboard" link; Admin link pinned to bottom
    for `is_staff` users only
- [x] Create `config/context_processors.py` → injects `SITE_NAME`, `current_theme` to all templates
- [x] Register context processor in `base.py` (`config.context_processors.site_context`)
- [x] `SITE_NAME` setting added to `base.py` (reads from env, default `"SaaS App"`)
- [x] Light/dark/system toggle: stores in `localStorage` key `theme`, applies `data-theme` on `<html>`
- [x] Create `apps/core/templatetags/tz_tags.py` — custom template filter
      `{{ value|localtime:tz }}` — accepts `core.Timezone` instance or IANA string
- [x] Semantic HTML: `<main id="main-content">`, `<header>`, `<footer>`, `<nav>`, `<section>`
- [x] **Skip-to-content link** as the first focusable element in `<body>`:
      `<a href="#main-content" class="sr-only focus:not-sr-only …">Skip to main content</a>`
- [x] `<html lang="{{ LANGUAGE_CODE }}">` — dynamic, not hardcoded
- [x] Health check endpoint: `GET /health/` → `{"status": "ok", "db": "ok"}` (503 if DB down)
- [x] `apps/pages/` — public homepage (`/`) + authenticated dashboard (`/dashboard/`)
- [x] `apps/users/urls.py` — stub URL patterns (`users:login`, `users:logout`, `users:profile`)
      so `base.html` `{% url %}` tags resolve before Phase 3 auth views are built
- [x] `config/urls.py` — wires `/`, `/dashboard/`, `/health/`, user stubs
- [x] Tests: health check 200 + JSON body, homepage 200 + base template, skip-link, context
      processor vars, theme from cookie, dashboard redirects anonymous, dashboard accessible
      when authenticated, `tz_tags` filter (IANA string, model instance, None, invalid zone)
- [x] 54 tests total (34 Phase 1 + 20 Phase 2), all passing; ruff clean

#### Post-Phase 2 fixes (committed after `6d25383`)

- [x] **Prettier protection** — `.prettierignore` lists `templates/`; `.vscode/settings.json`
      disables HTML format-on-save; rule added to `.clauderules` and `copilot-instructions.md`
- [x] **Pre-commit hook** — `scripts/pre-commit` (ruff + test suite) + `scripts/install-hooks.sh`;
      hook is a **symlink** (not a copy) so edits to `scripts/pre-commit` take effect immediately;
      uses `--keepdb` + `--exclude-tag=slow` for fast execution (~1.5 s)
- [x] **`@tag("slow")`** on `LoadReferenceDataCommandTest` + `ReferenceDataRelationshipTest`
      — excluded from pre-commit hook; still run with bare `uv run python manage.py test apps`
- [x] **DaisyUI 5 theme fix** — added `themes.css` CDN link (separate from `daisyui.css`);
      set `data-theme="corporate"` as HTML default so the anti-flash script has a fallback
- [x] **DaisyUI 5 dock fix** — `btm-nav` / `btm-nav-item` / `btm-nav-label` renamed to
      `dock` / _(direct child — no class)_ / `dock-label` in the mobile bottom nav
- [x] **Mobile theme toggle** — added sun/moon toggle button inside the mobile overlay modal;
      `applyTheme()` JS function syncs both desktop and mobile icons simultaneously
- [x] **43 fast tests passing** (11 slow tests excluded from hook); ruff clean

---

### ✅ Phase 3 — Auth UX: Login, Register, Onboarding & Profile (DONE)

**Goal:** Users can register, log in, complete a two-step onboarding gate, access the
dashboard, and manage preferences — all via email.

#### Login

- [x] Login view (`/login/`): email + password
  - **Failure** (wrong credentials): stay on the login form; display an inline
    `<div role="alert">` error message. Do NOT redirect anywhere.
  - **Cancel link** on the login page (or user presses Back): redirect to **homepage** (`/`).
  - **Success**: redirect to `?next` param, or `/dashboard/`

#### Registration

- [x] Register view (`/register/`):
  - Fields: email + password only
  - Hidden fields: `tz_detect`, `lang_detect` (populated via JS, see Phase 1d)
  - Success → skip email confirmation → auto-create `UserProfile` via signal →
    redirect to `/profile/complete/` with title **"Complete your profile"**

#### Logout

- [x] Logout (`/logout/`): clears session → redirect to homepage

#### Two-Step Onboarding Gate

- [x] **`ProfileCompleteMiddleware`** in `apps/users/middleware.py`:
  - Runs after `AuthenticationMiddleware` — add to `MIDDLEWARE` in `base.py`
  - Decision logic:
    1. `profile_completed_at IS NULL` **AND** `session["skip_profile_gate"]` is not `True`
       → redirect to `/profile/complete/?next=<url>`
    2. Else if `request.user.profile.tenant_id` is `None`
       → redirect to `/onboarding/create-tenant/?next=<url>`
    3. Else if `request.user.profile.is_active` is `False`
       → redirect to `/account/revoked/`
    4. Else: pass through
  - Exempt (never redirected): `/profile/complete/`, `/onboarding/create-tenant/`,
    `/account/revoked/`, `/logout/`, `/health/`, `settings.PROFILE_GATE_EXEMPT_URLS`

- [x] **Step 1 — Profile completion (`/profile/complete/`):**
  - Page title: **"Complete your profile"**
  - DaisyUI **steps** progress: `Profile → Workspace` (currently at step 1)
  - Inputs: `display_name`, `timezone` (from `core.Timezone` FK), avatar upload (optional)
  - Input style: `text-base` (16 px) to prevent mobile zoom
  - **"Do this later"** button: sets `request.session["skip_profile_gate"] = True`,
    redirects to `?next` (or `/onboarding/create-tenant/`)
  - On save: `profile_completed_at = now()` → redirect to Step 2
    (`/onboarding/create-tenant/`)

- [x] **Step 2 — Tenant creation (`/onboarding/create-tenant/`):**
  - Page title: **"Create your workspace"**
  - Subtitle: **"What is your organisation called?"**
  - DaisyUI **steps** progress: `Profile → Workspace` (currently at step 2)
  - Input: `organization` — labelled **"Organisation name"** (not "Workspace name")
  - On save: create `Tenant`, set `profile.tenant`, `profile.role = "admin"`,
    `profile.tenant_joined_at = now()` → redirect to `/dashboard/`
  - > **No "Do this later" on Step 2.** The session `skip_profile_gate` flag
    > already bypasses Step 1; Step 2 (workspace creation) is the minimum
    > requirement for the app to be usable and cannot be permanently skipped.
    > If the user closes the browser, the middleware will redirect them back
    > to `/onboarding/create-tenant/` on next login.

#### Dashboard

- [x] Dashboard view (`/dashboard/`): login required; displays
      "Welcome {display_name or email}"; unauthenticated → redirect to login;
      incomplete-profile gate redirects to `/profile/complete/` first

#### Full Profile Settings (`/profile/`)

- [x] Login required
- [x] Title: **"Profile"** (distinct from the onboarding `/profile/complete/` step)
- [x] Editable: `display_name`, `language`, `timezone`, `country`, `currency`, `theme`
- [x] Marketing section: `marketing_emails` opt-in
- [x] Subsequent saves: stay on `/profile/` with a success message
- [x] Theme change also updates `localStorage` key `theme`
- [x] Language change triggers Django locale switch + updates `localStorage` key `lang`
- [x] Timezone uses IANA tz selector (from `core.Timezone`)
- [x] Does NOT include email or password fields

#### Shared Auth UX rules

- [x] Auth forms: DaisyUI **hero** + split-screen (desktop); full-width `items-start` (mobile)
- [x] Correct HTML input types: `type="email"`, `type="password"`, `autocomplete` attributes
- [x] Left-side nav (authenticated): "Dashboard" link only (Profile is in the top-right dropdown)
- [x] Email backend: `console` for dev, configurable SMTP/SES for prod
- [x] Password reset flow (forgot password)
- [x] **DaisyUI 5 forms:** `form-control` is **removed** — use the new `fieldset` + `label`
      component syntax for all form fields. `label` now goes inside `fieldset`.
      See: https://daisyui.com/components/fieldset/ and https://daisyui.com/components/label/

#### Tenant Member Management (`/settings/members/`)

The user who completes Step 2 (workspace creation) becomes the `admin` of that tenant.
As admin they can invite other users and revoke access.

- [x] **Members page (`/settings/members/`):** `admin`-only; lists all `UserProfile`
      records where `profile.tenant == request.user.profile.tenant` (active + inactive)
- [x] **Invite member:** admin enters an email address → create/lookup `User` →
      set `profile.tenant`, `profile.role = "member"`, `profile.tenant_joined_at = now()`,
      `profile.is_active = True` → send invitation email (no Celery yet — use Django's
      `send_mail` synchronously in dev, configure SMTP for prod)
- [x] **Revoke access:** set `profile.is_active = False`, `profile.tenant_revoked_at = now()`,
      `profile.deleted_by = request.user.pk` — the `tenant` FK is **never cleared**
- [x] **Re-engage:** set `profile.is_active = True`, `profile.tenant_revoked_at = None`,
      `profile.deleted_by = None`, `profile.deleted_at = None`
- [x] **Guard:** only `role=admin` profiles can access `/settings/members/`; any other
      authenticated user hitting that URL gets a `403 Forbidden`
- [x] **Cannot self-revoke:** an admin cannot revoke themselves
      (prevents a workspace from becoming unmanageable)
- [x] **Second workspace:** a user wanting to join a different org must register a new
      account — enforced in the invite service (`profile.tenant is not None` → validation error)
- [x] Tests:
  - Admin can access members page; non-admin gets 403
  - Admin can invite a new email → profile.tenant set, profile.role = member
  - Admin can invite an existing user whose profile.tenant is null → profile updated
  - Admin cannot invite a user who already has a tenant set (different or same)
  - Admin can revoke a member → `is_active=False`, `tenant_revoked_at` set, member redirected
  - Admin cannot revoke themselves
  - Revoked member redirected by middleware to `/account/revoked/`
  - Admin can re-engage a revoked member → `is_active=True`, `tenant_revoked_at` cleared

#### Tests

- [x] Register → redirected to `/profile/complete/` with "Complete your profile" title
- [x] Login failure → stays on login form with inline error; no redirect
- [x] Login cancel link → redirects to homepage
- [x] Accessing `/dashboard/` with incomplete profile (no skip) → redirected to `/profile/complete/?next=/dashboard/`
- [x] "Do this later" sets session flag → subsequent requests pass Step 1 check
- [x] After Step 1 save → redirected to `/onboarding/create-tenant/`
- [x] After Step 2 save → redirected to `/dashboard/`
- [x] Accessing `/dashboard/` with complete profile and tenant → allowed through
- [x] `/logout/` and `/health/` never intercepted by gate
- [x] Revoked member (`is_active=False`) redirected to `/account/revoked/`
- [x] Full profile update (subsequent saves stay on `/profile/`)
- [x] Marketing opt-in toggle
- [x] Password reset
- [x] 96 tests total (54 Phase 1+2 + 42 Phase 3), all passing; ruff clean

#### Post-Phase 3 visual fixes (committed after `1dcce20`)

- [x] **Organisation copy** — onboarding step 2 subtitle changed to "What is your organisation
      called?"; field label changed to "Organisation name" (was "Workspace name");
      form `TenantCreateForm.organization` label updated to match
- [x] **Admin link in navigation** — `{% if user.is_staff %}` guard added;
      Admin link appears in: left sidebar (pinned to bottom with `mt-auto`), and mobile overlay;
      **not** in the top-right dropdown (dropdown contains Profile + Logout only)
- [x] **Django admin "View site" → `/dashboard/`** — `admin.site.site_url = "/dashboard/"`
      added to `config/urls.py` (one-liner before `urlpatterns`)
- [x] **Sidebar restructure** — Profile link removed from sidebar (it lives in the top-right
      dropdown); Admin link moved to bottom of sidebar using `mt-auto` + `border-t` separator;
      sidebar `<nav>` given `flex-1` so `mt-auto` works correctly
- [x] **Viewport-locked layout (`h-screen overflow-hidden`)** — `<body>` changed from
      `min-h-screen flex flex-col` to `h-screen flex flex-col overflow-hidden`;
      this locks the entire layout to the viewport so the sidebar never scrolls away
      when main content is long; sidebar and main content each scroll independently

#### Post-Phase 3 theme work (commits `f64004d`, `b7bc944`, `340295f`)

- [x] **3-state theme toggle** — replaced binary light/dark toggle with 3-state cycle:
      `corporate → night → system → corporate …`; added monitor icon for the system state;
      `"system"` resolves `prefers-color-scheme` at runtime — never stored as a resolved value
- [x] **Server-side theme seed** — `{{ current_theme }}` (from `UserProfile.theme` via
      context processor) injected into the anti-flash `<script>` for authenticated users;
      auth user's saved pref wins over any stale `localStorage` value on first paint (incognito,
      fresh browser); unauthenticated users continue to use `localStorage` only
- [x] **`POST /theme/set/`** — new AJAX endpoint (`users:set_theme`); saves `UserProfile.theme`
      for authenticated users on every toggle click; unauthenticated returns `200 ok` with no
      DB write; added to `_ALWAYS_EXEMPT` in `ProfileCompleteMiddleware`
- [x] **Profile page sync** — `profile_view` passes `saved_theme` to context; `profile.html`
      `extra_js` block syncs `localStorage` to the newly saved theme on page reload after save
- [x] **Django comment bug fix** — replaced all `{# #}` comments inside `<script>` blocks with
      `//` JS comments; replaced multi-line `{# #}` block comments adjacent to `<script>` tags
      (which render as literal visible text in the browser) with single-line `{# label #}` labels
- [x] **107 tests total** (96 Phase 1–3 + 11 new `SetThemeViewTest`), all passing; ruff clean

---

### 🔲 Phase 4 — I18N: US English + Belgian Dutch + Belgian French

**Goal:** All user-facing strings are translatable; language toggle works in navbar.

- [ ] `USE_I18N = True`, add `django.middleware.locale.LocaleMiddleware` to `MIDDLEWARE`
- [ ] Configure `LANGUAGES = [("en", "English"), ("nl", "Nederlands"), ("fr", "Français")]`
      in `base.py`
- [ ] Wrap all template strings in `{% trans %}` / `{% blocktrans %}`
- [ ] Wrap all Python strings in `_()` / `gettext_lazy()`
- [ ] Generate translation files:
  ```
  uv run python manage.py makemessages -l nl_BE
  uv run python manage.py makemessages -l fr_BE
  ```
- [ ] Translate all existing strings to `nl-be` and `fr-be`
- [ ] Language selector in navbar: stores choice in `localStorage` key `lang`, triggers `LANGUAGE_CODE` switch
- [ ] `<html>` tag carries `lang="{{ LANGUAGE_CODE }}"` — set via context/template, not hardcoded
- [ ] `uv run python manage.py compilemessages`
- [ ] Tests: language switch, translated strings render correctly for all three locales

---

### 🔲 Phase 5 — Core SaaS Feature(s)

> To be defined. Add feature specs here as the product takes shape.

---

### 🔲 Phase 6 — Billing (Deferred — do not start before Phase 5)

**Goal:** Tenants can subscribe to a plan and be billed via Stripe.

- [ ] Install Celery + Redis (`uv add celery redis`)
- [ ] Configure Celery in `config/celery.py`; tasks live in `apps/<name>/tasks.py`
- [ ] `apps/billing/` — `Plan`, `Subscription` models (`Plan` extends `TimeStampedAuditModel`; `Subscription` extends `TenantScopedModel`)
- [ ] Stripe SDK (`uv add stripe`)
- [ ] Checkout session creation (service layer)
- [ ] Stripe webhook handler (idempotent, processed via Celery task)
- [ ] Subscription status middleware (block access if inactive)
- [ ] Tests: plan assignment, webhook idempotency, Celery task execution

---

### 🔲 Phase 7 — Production Hardening

- [ ] CI pipeline: `uv sync` → ruff → tests (GitHub Actions)
- [ ] PostgreSQL RLS for tenant isolation
- [ ] Sentry / error tracking (`uv add sentry-sdk`)
- [ ] Structured JSON logging
- [ ] `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` from env
- [ ] Docker + `docker-compose.yml` for local parity
- [ ] Deployment config (Railway / Fly.io / other)

---

### 🔲 Phase 8 — Low Priority / Future

These are valid ideas — implement only after Phase 7 is complete:

- [ ] **Impersonation Tool** — admin can log in as any user (on-behalf support)
- [ ] **Audit Logs & Activity Feeds** — timestamped trail of user/tenant actions
- [ ] **Feature Flags** — soft-launch features to selected tenants/users only

---

## Running Decisions Log

| Date       | Decision                                                                                     | Outcome                                                                                                                                                                                 |
| ---------- | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-02-21 | Chose `psycopg` v3 over `psycopg2`                                                           | Async-ready, actively maintained                                                                                                                                                        |
| 2026-02-21 | `.clauderules` added for Claude in VS Code                                                   | Hard constraints enforced per-session                                                                                                                                                   |
| 2026-02-21 | Email as `USERNAME_FIELD`, no username                                                       | Simpler UX, consistent with SaaS expectations                                                                                                                                           |
| 2026-02-21 | Soft deletes on all major models                                                             | Safe recovery, audit trail, no data loss                                                                                                                                                |
| 2026-02-21 | `created_by`/`updated_by` are standard in `TimeStampedAuditModel`; `User` is sole exception  | Circular FK risk is `User`-only; every other model's acting user is committed first                                                                                                     |
| 2026-02-21 | `UserProfile` as separate `OneToOneField` model                                              | Keeps `User` minimal; profile fields never touch auth/registration forms                                                                                                                |
| 2026-02-21 | `display_name` nullable, derived from email                                                  | Friendly name without forcing input at registration                                                                                                                                     |
| 2026-02-21 | Store UTC, display in `UserProfile.timezone`                                                 | Single DB truth; `zoneinfo` for conversion                                                                                                                                              |
| 2026-02-21 | Navbar: display_name dropdown replaces "Leave"                                               | Named user with Profile + Logout dropdown menu                                                                                                                                          |
| 2026-02-21 | Tailwind + DaisyUI corporate/night, follow-system                                            | Consistent UI, zero-CSS-overhead, dark mode built-in                                                                                                                                    |
| 2026-02-21 | Stripe deferred to Phase 6                                                                   | Auth + UI shell are higher priority foundations                                                                                                                                         |
| 2026-02-21 | Celery + Redis for async (tied to Stripe)                                                    | No blocking web requests for billing events                                                                                                                                             |
| 2026-02-21 | Registration → profile (not dashboard)                                                       | Intentional onboarding; gate ensures profile is complete before app access                                                                                                              |
| 2026-02-21 | `profile_completed_at` drives completion gate                                                | Single nullable timestamp; middleware exempt list keeps /logout, /health reachable                                                                                                      |
| 2026-02-22 | Two-step onboarding: Profile → Tenant                                                        | Personal setup separated from workspace creation; skip session flag avoids nagging                                                                                                      |
| 2026-02-22 | Login failure stays on form (not redirect)                                                   | Redirect loses context; inline error with aria role="alert" is correct UX + a11y                                                                                                        |
| 2026-02-22 | Reference data models in core (Country/Lang/Tz/Currency)                                     | FK references allow filtered dropdowns (e.g. languages for Belgium); data from `pycountry`                                                                                              |
| 2026-02-22 | `product_updates` field removed                                                              | Single `marketing_emails` opt-in sufficient for Phase 1; extend when legally required                                                                                                   |
| 2026-02-22 | Added `fr-be` (Belgian French) locale                                                        | Belgium is bilingual; French speakers are a core audience                                                                                                                               |
| 2026-02-22 | WCAG AA accessibility built in from Phase 2                                                  | aria-invalid + aria-describedby on forms; skip-link; focus trap; 44px targets                                                                                                           |
| 2026-02-22 | Never hard-delete User or UserProfile                                                        | Silent cascade risk; `is_active = False` is the only safe deactivation path                                                                                                             |
| 2026-02-22 | `Tenant` fields: UUID PK + `organization` only                                               | `name` merged into `organization`; `slug` deferred — add when tenant-scoped URLs needed                                                                                                 |
| 2026-02-22 | `UserProfile` roles: `admin` + `member` only; no join table                                  | One user, one tenant (hard constraint); `admin` manages members, billing, settings; reflects permission set not creation history                                                        |
| 2026-02-22 | Owner can invite/revoke members via `/settings/members/`                                     | Tenant isolation requires membership management; soft-revoke via `is_active=False` + `tenant_revoked_at`; `tenant` FK never cleared                                                     |
| 2026-02-22 | Audit actor fields use `UUIDField` not `ForeignKey`                                          | Hybrid integrity: no FK constraint, no implicit index, no circular dep on `User`; service layer owns integrity; index per-model on demand                                               |
| 2026-02-22 | Three-category model taxonomy: `TenantScopedModel` / `TimeStampedAuditModel` / plain `Model` | Replaces single opt-in base. Circular risk is `User`-only; all other models get full audit trail in base class. `TenantScopedModel` extends `TimeStampedAuditModel` + adds `tenant_id`. |
| 2026-02-22 | Superuser created; admin verified                                                            | `/admin/` shows all expected sections: Auth & Authorization, Core (Countries/Currencies/Languages/Timezones), Tenants, Users (User profiles/Users). Phase 1 fully operational.          |
| 2026-02-22 | DaisyUI via CDN for dev; `django-tailwind` installed but no npm build step                   | Keeps dev stack lean; swap CDN for compiled output in Phase 7 prod hardening                                                                                                            |
| 2026-02-22 | `users:login`, `users:logout`, `users:profile` as `RedirectView` stubs in Phase 2            | Allows `base.html` `{% url %}` tags to resolve and tests to pass before Phase 3 auth views exist                                                                                        |
| 2026-02-22 | Theme toggle: `corporate` (light) ↔ `night` (dark); `system` resolves at render time via JS  | "system" stored in profile/cookie; JS reads `prefers-color-scheme` on page load to pick the actual DaisyUI theme — no server round-trip needed                                          |
| 2026-02-22 | DaisyUI 5 `themes.css` must be loaded separately from `daisyui.css`                          | `daisyui.css` CDN = component styles only; theme colour palettes are in `themes.css` — both links required in `base.html`                                                               |
| 2026-02-22 | `btm-nav` renamed to `dock` in DaisyUI 5                                                     | Full rename: `btm-nav` → `dock`, `btm-nav-sm` → `dock-sm`, `btm-nav-item` → removed (direct children styled automatically), `btm-nav-label` → `dock-label`                              |
| 2026-02-22 | `form-control` removed in DaisyUI 5                                                          | Use new `fieldset` + `label` component syntax for all form fields in Phase 3+; `form-control` no longer exists                                                                          |
| 2026-02-22 | Pre-commit hook uses `--keepdb --exclude-tag=slow`                                           | `--keepdb` avoids recreating `test_saas_db` on every commit; `--exclude-tag=slow` skips `load_reference_data` tests (~7 k language rows); hook runs in ~1.5 s                           |
| 2026-02-22 | Mobile theme toggle added to overlay menu                                                    | Same `applyTheme()` JS function syncs desktop + mobile icons; both buttons update simultaneously                                                                                        |
| 2026-02-22 | Admin link in navbar/sidebar shown only to `is_staff` users                                  | `{% if user.is_staff %}` guard in `base.html`; shown in desktop dropdown, left sidebar, and mobile overlay — only users with Django staff flag see it                                   |
| 2026-02-22 | Django admin "View site" redirects to `/dashboard/`                                          | `admin.site.site_url = "/dashboard/"` in `config/urls.py`; no custom `AdminSite` subclass needed — one-liner is sufficient                                                              |
| 2026-02-22 | Onboarding step 2 label: "Organisation name" not "Workspace name"                            | "Workspace" is an internal concept; users think in terms of their organisation; label and form field updated accordingly                                                                |
| 2026-02-22 | Admin link removed from top-right dropdown                                                   | Dropdown contains Profile + Logout only; Admin link lives in left sidebar (bottom) and mobile overlay — not in the user account menu                                                    |
| 2026-02-22 | Profile link removed from left sidebar                                                       | Profile lives in the top-right `display_name` dropdown; sidebar is for app navigation sections only (Dashboard, future modules, Admin at bottom for staff)                              |
| 2026-02-22 | `h-screen overflow-hidden` on `<body>` — viewport-locked layout                              | Sidebar stays visible regardless of main content length; each scroll container is independent; `min-h-screen` was the root cause of the sidebar Admin link disappearing on long pages   |
| 2026-02-22 | 3-state theme toggle: `corporate → night → system`                                           | Replaces binary light/dark toggle. `"system"` reads `prefers-color-scheme` at runtime; stored as the logical pref in `localStorage` (never resolved). Cycle: `corporate → night → system → corporate …`                   |
| 2026-02-22 | Server-side theme seed for authenticated users                                               | `{{ current_theme }}` from `UserProfile.theme` injected into anti-flash script; auth user's saved pref wins over stale `localStorage` on fresh browser/incognito. Unauthenticated: `localStorage` only.                    |
| 2026-02-22 | `POST /theme/set/` saves theme to `UserProfile` for authenticated users                      | AJAX endpoint (`users:set_theme`); called by toggle JS on every click; unauthenticated returns `200 ok` no DB write; exempt from `ProfileCompleteMiddleware` via `_ALWAYS_EXEMPT`                                           |
| 2026-02-22 | `{# #}` Django template comments must not appear inside or adjacent to `<script>` blocks    | Multi-line `{# #}` adjacent to `<script>` tags render as literal visible text; use `//` JS comments inside scripts and single-line `{# label #}` outside — rule added to `.clauderules`, `copilot-instructions.md`        |

---

## Useful Commands

```bash
# Dev server
uv run python manage.py runserver

# Migrations
uv run python manage.py makemigrations
uv run python manage.py migrate

# Create superuser (email-based)
uv run python manage.py createsuperuser

# Django shell
uv run python manage.py shell

# Lint + format (run after EVERY code change)
uv run ruff check --fix && uv run ruff format

# Tests
uv run python manage.py test apps

# Install git pre-commit hook (run once after cloning — prevents committing broken code)
bash scripts/install-hooks.sh

# Commit and push after each completed phase (tests passing, ruff clean)
git add -A && git commit -m "feat: Phase N — <short summary>" && git push

# I18N
uv run python manage.py makemessages -l nl_BE
uv run python manage.py makemessages -l fr_BE
uv run python manage.py compilemessages

# Seed ISO reference data (countries, languages, timezones, currencies)
uv run python manage.py load_reference_data

# Add dependency
uv add <package>

# Sync to lock file
uv sync
```
