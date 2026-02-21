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

| #   | Decision                                                | Rationale                                                                                             |
| --- | ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 1   | `uv` as package manager                                 | Fast, lock-file first, no venv friction                                                               |
| 2   | Split settings base/dev/prod                            | Clear env separation, no secrets in dev spill into prod                                               |
| 3   | `django-environ` for secrets                            | 12-factor, `.env` never committed                                                                     |
| 4   | `psycopg` (v3) for PostgreSQL                           | Modern async-ready driver                                                                             |
| 5   | UUID primary keys on all models                         | Avoids enumerable IDs, safe for multi-tenant                                                          |
| 6   | `tenant_id` on all tenant-scoped models                 | Foundation for row-level security (RLS)                                                               |
| 7   | Soft deletes (`is_active`, `deleted_at`, `deleted_by`)  | Safe data recovery, audit trail, no hard deletes                                                      |
| 8   | `created_by`/`updated_by` are opt-in, not in base model | Circular FK risk on `User` itself; adds migration noise; add only where attribution genuinely matters |
| 9   | Services/Selectors pattern                              | Thin views, testable business logic                                                                   |
| 10  | Ruff (DJ + S + B + E + F + I rules)                     | Single tool for lint + format + isort                                                                 |
| 11  | Custom `User` model with `email` as `USERNAME_FIELD`    | Email-based auth from day one, no username field                                                      |
| 12  | `UserProfile` as separate `OneToOneField` model         | Keeps `User` minimal; profile fields never touch auth/registration forms                              |
| 13  | `display_name` nullable, auto-derived from email        | Friendly name without forcing input at registration                                                   |
| 14  | Browser-detected locale/timezone on registration        | Best-effort UX, always user-overridable in profile                                                    |
| 15  | Store UTC everywhere, display in user's local tz        | Single source of truth in DB; `UserProfile.timezone` drives display                                   |
| 16  | `zoneinfo` (stdlib) for timezone conversion             | No extra dependency; Python 3.9+ built-in                                                             |
| 17  | Tailwind CSS + DaisyUI (corporate/night themes)         | Rapid, consistent UI with zero custom CSS overhead                                                    |
| 18  | Follow-system as default theme                          | Respects OS preference; stored in `localStorage`                                                      |
| 19  | Anti-flash script in `<head>`                           | Prevents white flash on dark-mode page load                                                           |
| 20  | Bottom Nav / Full-Screen Overlay on mobile              | Better UX than top-right hamburger                                                                    |
| 21  | Navbar auth control = display_name dropdown             | "Leave" replaced with named user + Profile/Logout menu                                                |
| 22  | I18N: `en-us` + `nl-be`                                 | Belgian Dutch as second locale from the start                                                         |
| 23  | Stripe deferred to Phase 6                              | Auth and UI foundations must be solid first                                                           |
| 24  | Background task queue (Celery + Redis)                  | Required for Stripe webhooks; no blocking web requests                                                |
| 25  | Registration → profile page (not dashboard)             | Forces intentional onboarding; profile gate ensures completeness before app access                    |
| 26  | `ProfileCompleteMiddleware` + `profile_completed_at`    | Single flag drives the gate; exempt list keeps logout/health reachable; `next` param preserves intent |

---

## Current File Structure

```
saas-django/
├── .clauderules              ← Hard constraints (rules file for Claude)
├── .github/
│   └── copilot-instructions.md  ← Copilot context summary
├── ai_context.md             ← This file (Mission Log)
├── .env                      ← Local secrets (git-ignored)
├── .env.example              ← Committed template
├── manage.py
├── pyproject.toml            ← uv + ruff config
├── uv.lock
├── config/
│   ├── settings/
│   │   ├── base.py           ← Shared settings, reads .env
│   │   ├── dev.py            ← DEBUG=True, local DB
│   │   └── prod.py           ← Security hardening
│   ├── context_processors.py ← (to be created) SITE_NAME, current_theme
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── apps/
    ├── core/                 ← (to be created) health check, shared base model
    ├── tenants/              ← (Phase 1)
    ├── users/                ← (Phase 1) custom User model
    ├── pages/                ← (Phase 2) homepage, dashboard
    └── billing/              ← (Phase 6, deferred)
```

---

## Shared Base Model Convention

All major data models must extend `TimeStampedSoftDeleteModel` (to be created in `apps/core/models.py`):

```python
class TimeStampedSoftDeleteModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active  = models.BooleanField(default=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+"
    )
    class Meta:
        abstract = True
```

> `is_active` is the field all live queries filter on — it gets the index.
> `deleted_at` and `deleted_by` are audit-only fields; querying them is rare and
> full-scan-acceptable. The `deleted_by` FK gets an implicit index from Django anyway.

> **`created_by` / `updated_by` are NOT in the base model.** They are opt-in, added
> only on models where attribution genuinely matters (e.g. `Document`, `Invoice`).
> This avoids circular FK dependencies — especially on `User` itself — and keeps
> migrations clean. Document the decision with a comment on each opt-in model.

---

## Phase Plan

### ✅ Phase 0 — Scaffold (DONE)

- [x] uv project init, Django 6 installed
- [x] Split settings (base / dev / prod)
- [x] PostgreSQL configured via `DATABASE_URL`
- [x] Ruff configured (DJ + S + B + E + F + I)
- [x] `.env` excluded from git, `.env.example` committed
- [x] `apps/` directory created
- [x] `.clauderules` + `ai_context.md` wired to Claude + Copilot in VS Code
- [x] Pushed to GitHub

---

### 🔲 Phase 1 — Foundation: Core App, Tenants & Users

**Goal:** Establish the shared base model, tenant model, and email-based custom User — everything else depends on this.

#### 1a — Core app (shared primitives)

- [ ] `uv run python manage.py startapp core` → move to `apps/core/`
- [ ] Create `TimeStampedSoftDeleteModel` abstract base in `apps/core/models.py`
- [ ] Register `apps.core` in `INSTALLED_APPS`

#### 1b — Tenants

- [ ] `apps/tenants/` — `Tenant` model: UUID PK, name, slug, `created_at`, `updated_at`
- [ ] `Tenant` extends `TimeStampedSoftDeleteModel`
- [ ] Admin registration
- [ ] Tests: tenant creation, slug uniqueness

#### 1c — Custom User

- [ ] `apps/users/` — `User(AbstractUser)`:
  - `USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = []`
  - Custom `UserManager` (`create_user`, `create_superuser`) using email
  - `tenant = models.ForeignKey(Tenant, ...)`
  - Extends `TimeStampedSoftDeleteModel`
- [ ] Set `AUTH_USER_MODEL = "users.User"` in `config/settings/base.py`
- [ ] Migrations (`makemigrations` → `migrate`)
- [ ] `createsuperuser` (email-based)
- [ ] Admin registration
- [ ] Tests: user creation, email uniqueness, tenant link, superuser creation

#### 1d — UserProfile

- [ ] `UserProfile(TimeStampedSoftDeleteModel)` in `apps/users/models.py`:
  - `user` — `OneToOneField(User, related_name="profile")`
  - `display_name` — `CharField(max_length=100, blank=True, null=True)`
  - `language` — `CharField` (IANA language tag, default `"en"`)
  - `timezone` — `CharField` (IANA tz, default `"UTC"`)
  - `country` — `CharField(max_length=2)` (ISO 3166-1 alpha-2)
  - `currency` — `CharField(max_length=3, default="EUR")` (ISO 4217)
  - `theme` — `CharField` choices: `corporate` / `night` / `system`; default `system`
  - `marketing_emails` — `BooleanField(default=False)`
  - `product_updates` — `BooleanField(default=False)`
  - `profile_completed_at` — `DateTimeField(null=True, blank=True)` — `None` until the
    user saves the profile form for the first time; drives the profile completion gate
- [ ] `post_save` signal on `User` → auto-create `UserProfile`
- [ ] Auto-populate `display_name` from email:
  - Take local-part (left of `@`); if it contains `.`, take left of first `.`
  - e.g. `peter.janssens@acme.com` → `peter`
- [ ] Accept hidden fields `tz_detect` and `lang_detect` on the registration form
      (populated via JS `Intl.DateTimeFormat().resolvedOptions().timeZone` and
      `navigator.language`) to pre-fill `timezone` and `language`
- [ ] `UserProfile` is NEVER part of the registration form
- [ ] Tests: profile auto-created, display_name derivation, signal idempotency,
      `profile_completed_at` is `None` on creation

---

### 🔲 Phase 2 — UI Shell: Tailwind, DaisyUI & Base Templates

**Goal:** All subsequent pages inherit a consistent, themed, accessible base layout.

- [ ] Install Tailwind CSS + DaisyUI (via `django-tailwind` or direct CDN for dev)
- [ ] Configure DaisyUI themes: `corporate` (light) + `night` (dark); default: follow system
- [ ] Create `templates/base.html`:
  - Anti-flash `<script>` in `<head>` before any CSS (see `.clauderules §9`)
  - DaisyUI top navbar (desktop) and bottom navigation / full-screen overlay (mobile)
  - **Desktop navbar:** logo-left / nav-centre / controls-right
    - Controls: language selector, theme toggle, auth control
    - **Unauthenticated auth control:** "Get started" button → login page
    - **Authenticated auth control:** `display_name` (or email local-part) as DaisyUI
      dropdown; items: "Profile" → `/profile/`, "Logout" → `/logout/`
  - **Mobile:** bottom nav / overlay — same options including Profile + Logout in user section
  - `<nav>` tag; hamburger with `aria-label="Toggle menu"`
  - Left-side menu (authenticated only): initially "Dashboard"
- [ ] Create `config/context_processors.py` → injects `SITE_NAME`, `current_theme` to all templates
- [ ] Register context processor in `base.py`
- [ ] Light/dark/system toggle: stores in `localStorage` key `theme`, applies `data-theme` on `<html>`
- [ ] Create `apps/core/templatetags/tz_tags.py` — custom template filter
      `{{ value|localtime:request.user.profile.timezone }}` for UTC→local conversion
- [ ] Skeleton components on form loads and theme switch
- [ ] Semantic HTML: `<main>`, `<header>`, `<footer>`, `<nav>`, `<section>`
- [ ] Health check endpoint: `GET /health/` → `{"status": "ok", "db": "ok"}`
- [ ] Tests: health check 200, context processor injects vars, timezone filter

---

### 🔲 Phase 3 — Auth UX: Login, Register, Dashboard & Profile

**Goal:** Users can register, log in, complete their profile via a gate, access the dashboard, and manage preferences — all via email.

- [ ] `apps/pages/` — public homepage (`/`) displaying "Home"
- [ ] Login view (`/login/`): email + password; failure → redirect to homepage
- [ ] Register view (`/register/`):
  - Fields: email + password only
  - Hidden fields: `tz_detect`, `lang_detect` (populated via JS, see Phase 1d)
  - Success → skip email confirmation → auto-create profile → **redirect to `/profile/`**
    with page title **"Complete your profile"**
- [ ] Logout (`/logout/`): clears session → redirect to homepage
- [ ] **`ProfileCompleteMiddleware`** in `apps/users/middleware.py`:
  - Runs after `AuthenticationMiddleware` — add to `MIDDLEWARE` in `base.py`
  - Authenticated user + `profile_completed_at` is `None` → redirect to
    `/profile/?next=<original_url>` with title **"Complete your profile"**
  - Exempt from the gate: `/profile/`, `/logout/`, `/health/`, and any URL in
    `settings.PROFILE_GATE_EXEMPT_URLS`
  - On first successful profile save: set `profile_completed_at = now()`,
    redirect to `?next` param (default `/dashboard/`)
- [ ] Dashboard view (`/dashboard/`): login required; displays "Welcome {display_name or email}";
      unauthenticated → redirect to login; incomplete profile → gate redirects to profile first
- [ ] **Profile page (`/profile/`):** login required
  - Title: **"Complete your profile"** when `profile_completed_at` is `None`;
    **"Profile"** otherwise
  - Editable: `display_name`, `language`, `timezone`, `country`, `currency`, `theme`
  - Marketing section: `marketing_emails` opt-in, `product_updates` opt-in
  - On first save: sets `profile_completed_at = now()` → redirects to `?next` or `/dashboard/`
  - Subsequent saves: stays on `/profile/` with a success message
  - Theme change also updates `localStorage` key `theme`
  - Language change also triggers Django locale switch + updates `localStorage` key `lang`
  - Timezone uses IANA tz selector
  - Does NOT include email or password fields
- [ ] Auth forms: DaisyUI **hero** + split-screen (desktop); full-width `items-start` (mobile)
      Use correct HTML input types: `type="email"`, `type="password"`, `autocomplete` attributes
- [ ] Left-side nav (authenticated): "Dashboard" + "Profile" links
- [ ] Email backend: `console` for dev, configurable SMTP/SES for prod
- [ ] Password reset flow (forgot password)
- [ ] Tests:
  - Register → redirected to profile with "Complete your profile" title
  - Accessing `/dashboard/` with incomplete profile → redirected to `/profile/?next=/dashboard/`
  - After first profile save → redirected to `/dashboard/`
  - Accessing `/dashboard/` with complete profile → allowed through
  - `/logout/` and `/health/` never intercepted by gate
  - Login success + failure redirects
  - Profile update (subsequent saves stay on profile page)
  - Marketing prefs toggle
  - Password reset

---

### 🔲 Phase 4 — I18N: US English + Belgian Dutch

**Goal:** All user-facing strings are translatable; language toggle works in navbar.

- [ ] `USE_I18N = True`, add `django.middleware.locale.LocaleMiddleware` to `MIDDLEWARE`
- [ ] Configure `LANGUAGES = [("en", "English"), ("nl", "Nederlands")]` in `base.py`
- [ ] Wrap all template strings in `{% trans %}` / `{% blocktrans %}`
- [ ] Wrap all Python strings in `_()` / `gettext_lazy()`
- [ ] Generate translation files: `uv run python manage.py makemessages -l nl_BE`
- [ ] Translate all existing strings to `nl-be`
- [ ] Language selector in navbar: stores choice in `localStorage` key `lang`, triggers `LANGUAGE_CODE` switch
- [ ] `uv run python manage.py compilemessages`
- [ ] Tests: language switch, translated strings render correctly

---

### 🔲 Phase 5 — Core SaaS Feature(s)

> To be defined. Add feature specs here as the product takes shape.

---

### 🔲 Phase 6 — Billing (Deferred — do not start before Phase 5)

**Goal:** Tenants can subscribe to a plan and be billed via Stripe.

- [ ] Install Celery + Redis (`uv add celery redis`)
- [ ] Configure Celery in `config/celery.py`; tasks live in `apps/<name>/tasks.py`
- [ ] `apps/billing/` — `Plan`, `Subscription` models (extend `TimeStampedSoftDeleteModel`)
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

| Date       | Decision                                          | Outcome                                                                            |
| ---------- | ------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 2026-02-21 | Chose `psycopg` v3 over `psycopg2`                | Async-ready, actively maintained                                                   |
| 2026-02-21 | `.clauderules` added for Claude in VS Code        | Hard constraints enforced per-session                                              |
| 2026-02-21 | Email as `USERNAME_FIELD`, no username            | Simpler UX, consistent with SaaS expectations                                      |
| 2026-02-21 | Soft deletes on all major models                  | Safe recovery, audit trail, no data loss                                           |
| 2026-02-21 | `created_by`/`updated_by` opt-in only             | Circular FK risk on `User`; add per-model where needed                             |
| 2026-02-21 | `UserProfile` as separate OneToOneField model     | Keeps User minimal; profile never touches auth forms                               |
| 2026-02-21 | `display_name` nullable, derived from email       | Friendly name without forcing input at registration                                |
| 2026-02-21 | Store UTC, display in `UserProfile.timezone`      | Single DB truth; `zoneinfo` for conversion                                         |
| 2026-02-21 | Navbar: display_name dropdown replaces "Leave"    | Named user with Profile + Logout dropdown menu                                     |
| 2026-02-21 | Tailwind + DaisyUI corporate/night, follow-system | Consistent UI, zero-CSS-overhead, dark mode built-in                               |
| 2026-02-21 | Stripe deferred to Phase 6                        | Auth + UI shell are higher priority foundations                                    |
| 2026-02-21 | Celery + Redis for async (tied to Stripe)         | No blocking web requests for billing events                                        |
| 2026-02-21 | Registration → profile (not dashboard)            | Intentional onboarding; gate ensures profile is complete before app access         |
| 2026-02-21 | `profile_completed_at` drives completion gate     | Single nullable timestamp; middleware exempt list keeps /logout, /health reachable |

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

# Lint + format
uv run ruff check --fix && uv run ruff format

# Tests
uv run python manage.py test

# I18N
uv run python manage.py makemessages -l nl_BE
uv run python manage.py compilemessages

# Add dependency
uv add <package>

# Sync to lock file
uv sync
```
