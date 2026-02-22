"""
Views for the pages app.

- home      → public landing page (/)
- dashboard → authenticated dashboard (/dashboard/)
- health    → machine-readable health check (/health/)
"""

import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _


def home(request):
    """Public homepage — unauthenticated landing page."""
    return render(request, "pages/home.html", {"page_title": _("Welcome")})


@login_required
def dashboard(request):
    """Authenticated dashboard — placeholder for Phase 3+."""
    return render(request, "pages/dashboard.html", {"page_title": _("Dashboard")})


def health(request):
    """
    Machine-readable health check.

    Returns HTTP 200 when the application and database are reachable,
    or HTTP 503 when the database is unavailable.

    Response: ``{"status": "ok", "db": "ok"}``
    """
    db_status = "ok"
    http_status = 200

    try:
        from django.db import connection

        connection.ensure_connection()
    except Exception:  # noqa: BLE001
        db_status = "error"
        http_status = 503

    overall = "ok" if http_status == 200 else "error"
    payload = json.dumps({"status": overall, "db": db_status})
    return HttpResponse(payload, content_type="application/json", status=http_status)
