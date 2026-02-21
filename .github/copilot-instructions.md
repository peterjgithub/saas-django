# Copilot Instructions — saas-django

This project has two authoritative context files. Read both before generating any code.

## Hard Constraints → `.clauderules`
All non-negotiable rules (package manager, DB, UUID PKs, app structure, security) are
in `.clauderules` at the project root. Always follow them.

## Mission Log → `ai_context.md`
The phase plan, ADRs, current structure, and running decisions are in `ai_context.md`.
Use it to understand *where we are* and *what comes next*.

---

Key rules summary (full detail in `.clauderules`):

- `uv add <pkg>` — never `pip install`
- `uv run <cmd>` — never bare `python manage.py ...`
- PostgreSQL only — never SQLite
- UUID PKs on every model
- `tenant_id` on every tenant-scoped model
- Apps live in `apps/<name>/`, business logic in `services.py` / `selectors.py`
- Run `uv run ruff check --fix && uv run ruff format` after every code change
- Every feature needs tests under `apps/<name>/tests/`
