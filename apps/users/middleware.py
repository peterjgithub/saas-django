"""
ProfileCompleteMiddleware — two-step onboarding gate.

Runs after AuthenticationMiddleware.

Decision logic for authenticated users:
  1. profile_completed_at is None AND skip_profile_gate session flag not set
     → redirect to /profile/complete/?next=<current_url>
  2. profile.tenant_id is None
     → redirect to /onboarding/create-tenant/?next=<current_url>
  3. profile.is_active is False
     → redirect to /account/revoked/
  4. Otherwise: pass through.

Anonymous users and exempt URLs are always passed through.
"""

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

# URLs that are never intercepted by the gate.
_ALWAYS_EXEMPT = {
    "/profile/complete/",
    "/onboarding/create-tenant/",
    "/account/revoked/",
    "/logout/",
    "/health/",
    "/admin/",
    "/login/",
    "/register/",
    "/password-reset/",
    "/password-reset/done/",
    "/password-reset/confirm/",
    "/password-reset/complete/",
    "/theme/set/",
}


def _is_exempt(path: str) -> bool:
    if path in _ALWAYS_EXEMPT:
        return True
    # Allow any URL under /admin/
    if path.startswith("/admin/"):
        return True
    # Allow custom exempt list from settings
    extra: list[str] = getattr(settings, "PROFILE_GATE_EXEMPT_URLS", [])
    return any(path.startswith(url) for url in extra)


class ProfileCompleteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not _is_exempt(request.path):
            profile = getattr(request.user, "profile", None)
            if profile is not None:
                next_param = f"?next={request.path}"

                # Step 1 gate: profile not yet completed and not skipped
                if profile.profile_completed_at is None and not request.session.get(
                    "skip_profile_gate"
                ):
                    return redirect(reverse("users:profile_complete") + next_param)

                # Step 2 gate: no tenant assigned yet
                if profile.tenant_id is None:
                    return redirect(
                        reverse("users:onboarding_create_tenant") + next_param
                    )

                # Revocation gate
                if not profile.is_active:
                    return redirect(reverse("users:account_revoked"))

        return self.get_response(request)
