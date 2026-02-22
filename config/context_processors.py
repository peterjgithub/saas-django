"""
Global context processors — injected into every template render.
"""

from django.conf import settings


def site_context(request):
    """
    Inject site-wide template variables:

    - ``SITE_NAME``  — human-readable product name (from settings)
    - ``current_theme`` — active DaisyUI theme name; resolved from:
        1. Authenticated user's saved profile preference
        2. ``theme`` cookie (set by the client-side JS toggle)
        3. Fallback: ``"system"``
    """
    # Resolve theme: profile → cookie → fallback
    current_theme = "system"

    if request.user.is_authenticated:
        try:
            current_theme = request.user.profile.theme or "system"
        except AttributeError:
            pass
    else:
        current_theme = request.COOKIES.get("theme", "system")

    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "SaaS App"),
        "current_theme": current_theme,
    }
