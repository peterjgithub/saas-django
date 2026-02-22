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

| #   | Decision                                                                                             | Rationale                                                                                                                                                                                                                                    |
| --- | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `uv` as package manager                                                                              | Fast, lock-file first, no venv friction                                                                                                                                                                                                      |
| 2   | Split settings base/dev/prod                                                                         | Clear env separation, no secrets in dev spill into prod                                                                                                                                                                                      |
| 3   | `django-environ` for secrets                                                                         | 12-factor, `.env` never committed                                                                                                                                                                                                            |
| 4   | `psycopg` (v3) for PostgreSQL                                                                        | Modern async-ready driver                                                                                                                                                                                                                    |
| 5   | UUID primary keys on all models                                                                      | Avoids enumerable IDs, safe for multi-tenant                                                                                                                                                                                                 |
| 6   | `tenant_id` on all tenant-scoped models                                                              | Foundation for row-level security (RLS)                                                                                                                                                                                                      |
| 7   | Soft deletes (`is_active`, `deleted_at`, `deleted_by`)                                               | Safe data recovery, audit trail, no hard deletes                                                                                                                                                                                             |
| 8   | `created_by`/`updated_by` are standard in `TimeStampedAuditModel`; `User` is the sole exception      | Circular risk is specific to `User` only (self-registration creates the UUID in the same transaction). Every other model's acting user is committed before the record is written — no circular risk. `User` omits these fields entirely.     |
| 9   | Services/Selectors pattern                                                                           | Thin views, testable business logic                                                                                                                                                                                                          |
| 10  | Ruff (DJ + S + B + E + F + I rules)                                                                  | Single tool for lint + format + isort                                                                                                                                                                                                        |
| 11  | Custom `User` model with `email` as `USERNAME_FIELD`                                                 | Email-based auth from day one, no username field                                                                                                                                                                                             |
| 12  | `UserProfile` as separate `OneToOneField` model                                                      | Keeps `User` minimal; profile fields never touch auth/registration forms                                                                                                                                                                     |
| 13  | `display_name` nullable, auto-derived from email                                                     | Friendly name without forcing input at registration                                                                                                                                                                                          |
| 14  | Browser-detected locale/timezone on registration                                                     | Best-effort UX, always user-overridable in profile                                                                                                                                                                                           |
| 15  | Store UTC everywhere, display in user's local tz                                                     | Single source of truth in DB; `UserProfile.timezone` drives display                                                                                                                                                                          |
| 16  | `zoneinfo` (stdlib) for timezone conversion                                                          | No extra dependency; Python 3.9+ built-in                                                                                                                                                                                                    |
| 17  | Tailwind CSS + DaisyUI (corporate/night themes)                                                      | Rapid, consistent UI with zero custom CSS overhead                                                                                                                                                                                           |
| 18  | Follow-system as default theme                                                                       | Respects OS preference; stored in `localStorage`                                                                                                                                                                                             |
| 19  | Anti-flash script in `<head>`                                                                        | Prevents white flash on dark-mode page load                                                                                                                                                                                                  |
| 20  | Bottom Nav / Full-Screen Overlay on mobile                                                           | Better UX than top-right hamburger                                                                                                                                                                                                           |
| 21  | Navbar auth control = display_name dropdown                                                          | "Leave" replaced with named user + Profile/Logout menu                                                                                                                                                                                       |
| 22  | I18N: `en-us` + `nl-be` + `fr-be`                                                                    | Belgian Dutch and Belgian French as second and third locales from the start                                                                                                                                                                  |
| 23  | Stripe deferred to Phase 6                                                                           | Auth and UI foundations must be solid first                                                                                                                                                                                                  |
| 24  | Background task queue (Celery + Redis)                                                               | Required for Stripe webhooks; no blocking web requests                                                                                                                                                                                       |
| 25  | Registration → profile page (not dashboard)                                                          | Forces intentional onboarding; profile gate ensures completeness before app access                                                                                                                                                           |
| 26  | `ProfileCompleteMiddleware` + `profile_completed_at`                                                 | Single flag drives the gate; exempt list keeps logout/health reachable; `next` param preserves intent                                                                                                                                        |
| 27  | Two-step onboarding: Profile → Tenant                                                                | Separates personal setup from workspace setup; both can be skipped via session flag                                                                                                                                                          |
| 28  | "Do this later" sets session flag, not DB flag                                                       | Avoids permanently marking a profile complete when the user skips; re-prompts next session                                                                                                                                                   |
| 29  | Reference data (Country/Language/Timezone/Currency) as DB models                                     | FK references allow cross-filtering (e.g. languages for a country); data from `pycountry` + `zoneinfo`                                                                                                                                       |
| 30  | `UserProfile` localisation fields use FK not CharField                                               | Referential integrity, consistent display names, and filterable dropdowns without duplication                                                                                                                                                |
| 31  | Never hard-delete User or UserProfile                                                                | Silent cascade risk; `is_active = False` is the only safe deactivation path                                                                                                                                                                  |
| 32  | `marketing_emails` only — no `product_updates`                                                       | Single opt-in field sufficient for now; extend when explicit consent categories are needed                                                                                                                                                   |
| 33  | WCAG AA accessibility built in from day one                                                          | aria-invalid + aria-describedby on all forms; skip-link; focus trap in modals; 44px min targets                                                                                                                                              |
| 34  | `TenantMembership` join table instead of FK on `User`                                                | A user may belong to multiple workspaces; FK on User locks them to one and conflates identity with membership                                                                                                                                |
| 35  | `Tenant` has only `organization` + UUID PK + base fields                                             | `name` was redundant with `organization`; `slug` deferred — UUID is sufficient for isolation until tenant-scoped URLs are needed                                                                                                             |
| 36  | `TenantMembership` roles: `owner` and `member` only                                                  | `admin` role deferred — no concrete permission split yet; owner is the single privileged role; add granularity in Phase 5+ when real RBAC needs emerge                                                                                       |
| 37  | Audit actor fields (`deleted_by`, opt-in `created_by`/`updated_by`) use `UUIDField` not `ForeignKey` | No FK constraint check on every write; no implicit index; no circular dependency on `User`; no JOIN overhead when reading audit data. Integrity enforced at the service layer. Add `db_index` per-model only if a query pattern warrants it. |

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

Use for system-level models with no workspace scope: `UserProfile`, `TenantMembership`,
`Tenant` itself, and any future system-wide record.

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

### 🔲 Phase 1 — Foundation: Core App, Tenants & Users

**Goal:** Establish the shared base model, tenant model, and email-based custom User — everything else depends on this.

#### 1a — Core app (shared primitives)

- [ ] `uv run python manage.py startapp core` → move to `apps/core/`
- [ ] Create `TimeStampedAuditModel` and `TenantScopedModel` abstract base classes in `apps/core/models.py`
      (see Shared Base Model Convention above)
- [ ] Register `apps.core` in `INSTALLED_APPS`

#### 1b — Reference Data (ISO tables)

- [ ] In `apps/core/models.py`: create `Country`, `Language`, `Timezone`, `Currency`
      models as specified in `.clauderules §5b`
- [ ] `ManyToManyField` relationships:
  - `Language.countries` → `Country`
  - `Timezone.countries` → `Country`
  - `Currency.countries` → `Country`
- [ ] Management command: `apps/core/management/commands/load_reference_data.py`
  - `uv add pycountry`
  - Loads all countries, languages, currencies from `pycountry`
  - Loads timezones from `zoneinfo.available_timezones()` with UTC offset calculation
  - Idempotent (`update_or_create`)
- [ ] Run after migrations: `uv run python manage.py load_reference_data`
- [ ] Tests: command creates records, FK filtering works (languages for Belgium, etc.)

#### 1c — Tenants

- [ ] `apps/tenants/` — `Tenant` model:
  - `id` — UUID PK
  - `organization` — `CharField(max_length=200)` — workspace / company name (required)
  - Extends `TimeStampedAuditModel` — Tenant IS the root; it has no `tenant_id` on itself
  - No `slug` — the UUID PK is the identifier; add a slug later if tenant-scoped URLs are needed
- [ ] `TenantMembership` model — join table between `User` and `Tenant`:
  - Extends `TimeStampedAuditModel` (`created_by` = UUID of the inviting owner)
  - `tenant` — `ForeignKey(Tenant)`
  - `user` — `ForeignKey(settings.AUTH_USER_MODEL)`
  - `role` — `CharField` choices: `owner` / `member`; default `member`
    - `owner`: created the workspace; can invite/remove members and manage tenant settings
    - `member`: regular workspace member; no admin capabilities
    - > **No `admin` role at this stage** — `owner` is the single privileged role.
      > Add granular roles (e.g. `admin`, `billing`) only when a concrete permission
      > need arises (Phase 5+).
  - `joined_at` — `DateTimeField(auto_now_add=True)`
  - `is_active` — inherited from `TimeStampedAuditModel` — `False` = revoked, not deleted
  - Unique together: `(tenant, user)`
- [ ] Admin registration for both models
- [ ] Tests: tenant creation, membership creation, role assignment, uniqueness constraint,
      owner can invite member, non-owner cannot invite

#### 1d — Custom User

- [ ] `apps/users/` — `User(AbstractUser)`:
  - `USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = []`
  - Custom `UserManager` (`create_user`, `create_superuser`) using email
  - Extends `AbstractUser` directly — **NOT** `TimeStampedAuditModel`
  - Add `deleted_at` and `deleted_by` (UUIDField) directly on `User` (no `created_by`/`updated_by`)
  - **No `tenant` FK on `User`** — workspace membership goes through `TenantMembership`
    (see Phase 1c); a user may belong to multiple tenants in the future
- [ ] Set `AUTH_USER_MODEL = "users.User"` in `config/settings/base.py`
- [ ] Migrations (`makemigrations` → `migrate`)
- [ ] `createsuperuser` (email-based)
- [ ] Admin registration
- [ ] Tests: user creation, email uniqueness, superuser creation

#### 1e — UserProfile

> **Depends on 1b** (core reference tables must be migrated first) and **1d** (User model).

- [ ] `UserProfile(TimeStampedAuditModel)` in `apps/users/models.py`:
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
- [ ] **NEVER hard-delete a `UserProfile`.** Soft-delete only (`is_active = False`).
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
- [ ] Semantic HTML: `<main id="main-content">`, `<header>`, `<footer>`, `<nav>`, `<section>`
- [ ] **Skip-to-content link** as the first focusable element in `<body>` (visually hidden
      until focused): `<a href="#main-content" class="sr-only focus:not-sr-only …">Skip to main content</a>`
- [ ] `<html lang="{{ LANGUAGE_CODE }}">` — dynamic, not hardcoded
- [ ] Health check endpoint: `GET /health/` → `{"status": "ok", "db": "ok"}`
- [ ] `apps/pages/` — public homepage (`/`) with a minimal placeholder; used by
      the cancel-link on the login page and as the unauthenticated landing page
- [ ] Tests: health check 200, context processor injects vars, timezone filter,
      skip-link is first focusable element

---

### 🔲 Phase 3 — Auth UX: Login, Register, Onboarding & Profile

**Goal:** Users can register, log in, complete a two-step onboarding gate, access the
dashboard, and manage preferences — all via email.

#### Login

- [ ] Login view (`/login/`): email + password
  - **Failure** (wrong credentials): stay on the login form; display an inline
    `<div role="alert">` error message. Do NOT redirect anywhere.
  - **Cancel link** on the login page (or user presses Back): redirect to **homepage** (`/`).
  - **Success**: redirect to `?next` param, or `/dashboard/`

#### Registration

- [ ] Register view (`/register/`):
  - Fields: email + password only
  - Hidden fields: `tz_detect`, `lang_detect` (populated via JS, see Phase 1d)
  - Success → skip email confirmation → auto-create `UserProfile` via signal →
    redirect to `/profile/complete/` with title **"Complete your profile"**

#### Logout

- [ ] Logout (`/logout/`): clears session → redirect to homepage

#### Two-Step Onboarding Gate

- [ ] **`ProfileCompleteMiddleware`** in `apps/users/middleware.py`:
  - Runs after `AuthenticationMiddleware` — add to `MIDDLEWARE` in `base.py`
  - Decision logic:
    1. `profile_completed_at IS NULL` **AND** `session["skip_profile_gate"]` is not `True`
       → redirect to `/profile/complete/?next=<url>`
    2. Else if user has no active `TenantMembership` record
       → redirect to `/onboarding/create-tenant/?next=<url>`
    3. Else: pass through
  - Exempt (never redirected): `/profile/complete/`, `/onboarding/create-tenant/`,
    `/logout/`, `/health/`, `settings.PROFILE_GATE_EXEMPT_URLS`

- [ ] **Step 1 — Profile completion (`/profile/complete/`):**
  - Page title: **"Complete your profile"**
  - DaisyUI **steps** progress: `Profile → Workspace` (currently at step 1)
  - Inputs: `display_name`, `timezone` (from `core.Timezone` FK), avatar upload (optional)
  - Input style: `text-base` (16 px) to prevent mobile zoom
  - **"Do this later"** button: sets `request.session["skip_profile_gate"] = True`,
    redirects to `?next` (or `/onboarding/create-tenant/`)
  - On save: `profile_completed_at = now()` → redirect to Step 2
    (`/onboarding/create-tenant/`)

- [ ] **Step 2 — Tenant creation (`/onboarding/create-tenant/`):**
  - Page title: **"Create your workspace"**
  - DaisyUI **steps** progress: `Profile → Workspace` (currently at step 2)
  - Input: `organization` (company / workspace name)
  - On save: create `Tenant`, create `TenantMembership` with `role=owner` →
    redirect to `/dashboard/`
  - > **No "Do this later" on Step 2.** The session `skip_profile_gate` flag
    > already bypasses Step 1; Step 2 (workspace creation) is the minimum
    > requirement for the app to be usable and cannot be permanently skipped.
    > If the user closes the browser, the middleware will redirect them back
    > to `/onboarding/create-tenant/` on next login.

#### Dashboard

- [ ] Dashboard view (`/dashboard/`): login required; displays
      "Welcome {display_name or email}"; unauthenticated → redirect to login;
      incomplete-profile gate redirects to `/profile/complete/` first

#### Full Profile Settings (`/profile/`)

- [ ] Login required
- [ ] Title: **"Profile"** (distinct from the onboarding `/profile/complete/` step)
- [ ] Editable: `display_name`, `language`, `timezone`, `country`, `currency`, `theme`
- [ ] Marketing section: `marketing_emails` opt-in
- [ ] Subsequent saves: stay on `/profile/` with a success message
- [ ] Theme change also updates `localStorage` key `theme`
- [ ] Language change triggers Django locale switch + updates `localStorage` key `lang`
- [ ] Timezone uses IANA tz selector (from `core.Timezone`)
- [ ] Does NOT include email or password fields

#### Shared Auth UX rules

- [ ] Auth forms: DaisyUI **hero** + split-screen (desktop); full-width `items-start` (mobile)
- [ ] Correct HTML input types: `type="email"`, `type="password"`, `autocomplete` attributes
- [ ] Left-side nav (authenticated): "Dashboard" + "Profile" links
- [ ] Email backend: `console` for dev, configurable SMTP/SES for prod
- [ ] Password reset flow (forgot password)

#### Tenant Member Management (`/settings/members/`)

The user who completes Step 2 (workspace creation) becomes the `owner` of that tenant.
As owner they can invite other users and revoke access.

- [ ] **Members page (`/settings/members/`):** `owner`-only; lists all `TenantMembership`
      records for the current tenant (active + inactive)
- [ ] **Invite member:** owner enters an email address → create/lookup `User` →
      create `TenantMembership(role="member", is_active=True)` → send invitation email
      (queued via email backend; no Celery yet — use Django's `send_mail` synchronously
      in dev, configure SMTP for prod)
- [ ] **Revoke access:** owner sets `TenantMembership.is_active = False` for a member
      (soft-revoke — the membership record is kept for audit; the user loses access
      immediately because the middleware checks `is_active=True` memberships only)
- [ ] **Re-activate:** owner can set `is_active = True` again to restore access
- [ ] **Guard:** only `role=owner` members can access `/settings/members/`; any other
      authenticated user hitting that URL gets a `403 Forbidden`
- [ ] **Cannot self-revoke:** an owner cannot revoke their own membership
      (prevents a workspace from becoming ownerless)
- [ ] Tests:
  - Owner can access members page; non-owner gets 403
  - Owner can invite a new email → membership created
  - Owner can invite an existing user → membership created
  - Owner cannot invite a user who is already an active member
  - Owner can revoke a member → `is_active=False`, member loses access
  - Owner cannot revoke themselves
  - Revoked member redirected by middleware (no active `TenantMembership`)
  - Owner can re-activate a revoked member

#### Tests

- [ ] Register → redirected to `/profile/complete/` with "Complete your profile" title
- [ ] Login failure → stays on login form with inline error; no redirect
- [ ] Login cancel link → redirects to homepage
- [ ] Accessing `/dashboard/` with incomplete profile (no skip) → redirected to `/profile/complete/?next=/dashboard/`
- [ ] "Do this later" sets session flag → subsequent requests pass Step 1 check
- [ ] After Step 1 save → redirected to `/onboarding/create-tenant/`
- [ ] After Step 2 save → redirected to `/dashboard/`
- [ ] Accessing `/dashboard/` with complete profile and tenant → allowed through
- [ ] `/logout/` and `/health/` never intercepted by gate
- [ ] Full profile update (subsequent saves stay on `/profile/`)
- [ ] Marketing opt-in toggle
- [ ] Password reset

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
| ---------- | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --- | ---------- | --------------------------------------------- | ---------------------------------------------------- |
| 2026-02-21 | Chose `psycopg` v3 over `psycopg2`                                                           | Async-ready, actively maintained                                                                                                                                                        |
| 2026-02-21 | `.clauderules` added for Claude in VS Code                                                   | Hard constraints enforced per-session                                                                                                                                                   |
| 2026-02-21 | Email as `USERNAME_FIELD`, no username                                                       | Simpler UX, consistent with SaaS expectations                                                                                                                                           |
| 2026-02-21 | Soft deletes on all major models                                                             | Safe recovery, audit trail, no data loss                                                                                                                                                |
| 2026-02-21 | `created_by`/`updated_by` opt-in only                                                        | Circular FK risk on `User`; add per-model where needed                                                                                                                                  |     | 2026-02-21 | `UserProfile` as separate OneToOneField model | Keeps User minimal; profile never touches auth forms |
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
| 2026-02-22 | `TenantMembership` join table, no FK on `User`                                               | FK locks user to one workspace; join table allows multi-tenant membership and role tracking                                                                                             |
| 2026-02-22 | `Tenant` fields: UUID PK + `organization` only                                               | `name` merged into `organization`; `slug` deferred — add when tenant-scoped URLs needed                                                                                                 |
| 2026-02-22 | `TenantMembership` roles: `owner` + `member` only                                            | `admin` deferred; owner is sole privileged role; prevents premature RBAC complexity                                                                                                     |
| 2026-02-22 | Owner can invite/revoke members via `/settings/members/`                                     | Tenant isolation requires membership management; soft-revoke preserves audit trail                                                                                                      |
| 2026-02-22 | Audit actor fields use `UUIDField` not `ForeignKey`                                          | Hybrid integrity: no FK constraint, no implicit index, no circular dep on `User`; service layer owns integrity; index per-model on demand                                               |
| 2026-02-22 | Three-category model taxonomy: `TenantScopedModel` / `TimeStampedAuditModel` / plain `Model` | Replaces single opt-in base. Circular risk is `User`-only; all other models get full audit trail in base class. `TenantScopedModel` extends `TimeStampedAuditModel` + adds `tenant_id`. |

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
uv run python manage.py makemessages -l fr_BE
uv run python manage.py compilemessages

# Seed ISO reference data (countries, languages, timezones, currencies)
uv run python manage.py load_reference_data

# Add dependency
uv add <package>

# Sync to lock file
uv sync
```
