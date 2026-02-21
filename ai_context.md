# Project Context: Django SaaS (Modern Stack)

## Tech Stack

- **Package Manager:** `uv` (Strictly avoid `pip` or `venv` commands).
- **Language:** Python: >=3.12 (target 3.14)
- **Framework:** Django>= 6.0.x
- **Environment:** macOS (Local development)

## Critical Workflow Rules

1. **Dependency Management:** Always use `uv add <pkg>` for new libraries and `uv run python manage.py <cmd>` for Django tasks.
   uv sync
   lock file is source of truth
2. **Project Structure:** - Root: `saas-django/`
   - Settings: `config/settings.py`
   - Entry point: `manage.py`
3. **Coding Style:** - Use **Class-Based Views (CBVs)** for complex logic.
   - Use **Function-Based Views (FBVs)** for simple endpoints.
   - Follow **DRY** (Don't Repeat Yourself) principles.
4. **SaaS Architecture:** - Keep logic in `services.py` layers rather than bloated `models.py` or `views.py`.
   - Prefer `ruff` for linting/formatting.
   - "Ruff is configured in pyproject.toml with DJ and S rules enabled. Always run uv run ruff check --fix after generating new Django apps or models."

## Intent Consistency

- We are building a scalable SaaS.
- Prioritize security (CSRF, XSS, SQLi) and performance (database indexing).
- When asked to create a new feature, suggest a new Django "app" structure within the project.

## Example Command Patterns

- ✅ `uv run python manage.py migrate`
- ✅ `uv add django-environ`
- ❌ `pip install django-environ`

# Project Context: Django SaaS (Modern Stack)

## 1. Tech Stack

- **Package Manager:** `uv`
  - Never use `pip` or `venv` directly.
  - Lock file (`uv.lock`) is the single source of truth.
- **Language:** Python >=3.12 (target 3.14)
- **Framework:** Django >=6.0,<6.1
- **Database:** PostgreSQL (default assumption unless specified otherwise) Row-Level Security (RLS) will be added for tables that should guarantee tenant context only can be retrieved
- **Environment:** macOS (local development)

---

## 2. Dependency & Environment Workflow

### Installing Dependencies

- Add new dependency:
  ```
  uv add <package>
  ```
- Sync environment exactly to lock file:
  ```
  uv sync
  ```

### Running Commands

Always prefix Django or Python commands with:

```
uv run <command>
```

Examples:

- `uv run python manage.py migrate`
- `uv run python manage.py runserver`
- `uv run python manage.py makemigrations`
- `uv run ruff check --fix`

❌ Never use:

- `pip install`
- `python manage.py ...` (without `uv run`)
- manual virtualenv activation

---

## 3. Project Structure

Root: `saas-django/`

Recommended structure:

```
saas-django/
│
├── manage.py
├── pyproject.toml
├── uv.lock
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   └── urls.py
└── apps/
    └── <app_name>/
```

### Settings Rules

- Use environment variables for secrets.
- No secrets in git.
- Default settings module via:
  ```
  DJANGO_SETTINGS_MODULE=config.settings.dev
  ```

---

## 4. Coding Standards

### Views

- Use **Class-Based Views (CBVs)** for non-trivial logic.
- Use **Function-Based Views (FBVs)** for simple endpoints.
- Keep views thin.

### Business Logic

- Place domain/business logic in:
  - `services.py`
  - `selectors.py` (read/query logic)
- Avoid bloated `models.py` or `views.py`.

### Apps

When implementing a new feature:

- Prefer creating a new Django app inside `apps/` if it represents a clear domain boundary.
- Each app may contain:
  - `models.py`
  - `views.py`
  - `services.py`
  - `selectors.py`
  - `tasks.py`
  - `tests/`

---

## 5. SaaS Architecture Principles

- Design for multi-tenancy (assume tenant isolation via `tenant_id` unless specified otherwise).
- Always index:
  - `tenant_id`
  - frequently filtered fields.
- Avoid cross-tenant queries unless explicitly required.

---

## 6. Security Defaults

Must enforce in production:

- `SECURE_SSL_REDIRECT = True`
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- Proper `ALLOWED_HOSTS`
- Proper `CSRF_TRUSTED_ORIGINS`

Prevent:

- CSRF
- XSS
- SQL injection (always use ORM)

Never trust user input.

---

## 7. Database & Migrations

- Keep migrations small and incremental.
- Avoid large data migrations without rollback strategy.
- Review query performance for new features.
- Use proper database indexes.

---

## 8. Linting & Code Quality

- Ruff is configured in `pyproject.toml` with Django (DJ) and security (S) rules enabled.
- After generating models or apps, always run:

  ```
  uv run ruff check --fix
  ```

Optional but recommended:

- Add pre-commit hooks for ruff and secret detection.

---

## 9. Testing & Quality Gate

Minimum requirements:

- Every new feature must include tests.
- Use Django test runner or pytest-django.
- Run tests via:
  ```
  uv run python manage.py test
  ```

CI must:

- Run `uv sync`
- Run lint
- Run tests

---

## 10. Intent Consistency

We are building a scalable, production-grade SaaS.

Priorities:

1. Security
2. Maintainability
3. Performance
4. Clear domain boundaries

When asked to implement a feature:

- Suggest a proper app boundary.
- Avoid quick hacks.
- Optimize for long-term clarity.
