"""
Views for the users app — Phase 3.

- login_view            GET/POST /login/
- register_view         GET/POST /register/
- logout_view           POST     /logout/
- profile_complete_view GET/POST /profile/complete/
- onboarding_tenant     GET/POST /onboarding/create-tenant/
- profile_view          GET/POST /profile/
- account_revoked_view  GET      /account/revoked/
- members_view          GET      /settings/members/
- invite_member_view    POST     /settings/members/invite/
- revoke_member_view    POST     /settings/members/revoke/<uuid>/
- reengage_member_view  POST     /settings/members/reengage/<uuid>/
"""

import uuid

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.users.forms import (
    InviteMemberForm,
    LoginForm,
    ProfileCompleteForm,
    ProfileSettingsForm,
    RegisterForm,
    TenantCreateForm,
)
from apps.users.models import UserProfile
from apps.users.services import (
    authenticate_user,
    complete_profile,
    create_tenant_for_profile,
    invite_member,
    reengage_member,
    register_user,
    revoke_member,
)

# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def login_view(request):
    """
    GET  → render login form
    POST → authenticate; on failure stay on form with inline error (no redirect)
    """
    if request.user.is_authenticated:
        return redirect("pages:dashboard")

    next_url = request.GET.get("next") or request.POST.get("next") or "/dashboard/"
    error = None

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate_user(
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
            )
            if user is not None and user.is_active:
                login(request, user)
                if next_url.startswith("/") and not next_url.startswith("//"):
                    return redirect(next_url)
                return redirect("pages:dashboard")
            else:
                error = _("Incorrect email or password. Please try again.")
    else:
        form = LoginForm()

    return render(
        request,
        "users/login.html",
        {"form": form, "error": error, "next": next_url},
    )


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


def register_view(request):
    """
    GET  → render registration form
    POST → create user, auto-login, redirect to /profile/complete/
    """
    if request.user.is_authenticated:
        return redirect("pages:dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = register_user(
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                tz_detect=form.cleaned_data.get("tz_detect", ""),
                lang_detect=form.cleaned_data.get("lang_detect", ""),
            )
            login(request, user)
            return redirect("users:profile_complete")
    else:
        form = RegisterForm()

    return render(request, "users/register.html", {"form": form})


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


@require_POST
def logout_view(request):
    """POST only — clears session, redirects to homepage."""
    logout(request)
    return redirect("pages:home")


# ---------------------------------------------------------------------------
# Onboarding — Step 1: Complete profile
# ---------------------------------------------------------------------------


@login_required
def profile_complete_view(request):
    """
    Step 1 of onboarding.

    'Do this later' → set session skip flag, redirect to step 2.
    Save → set profile_completed_at, redirect to step 2.
    """
    profile = request.user.profile
    next_url = request.GET.get("next") or request.POST.get("next", "")

    if request.method == "POST":
        if "skip" in request.POST:
            request.session["skip_profile_gate"] = True
            return redirect("users:onboarding_create_tenant")

        form = ProfileCompleteForm(request.POST, instance=profile)
        if form.is_valid():
            complete_profile(
                profile=profile,
                display_name=form.cleaned_data.get("display_name", ""),
                timezone_obj=form.cleaned_data.get("timezone"),
            )
            return redirect("users:onboarding_create_tenant")
    else:
        form = ProfileCompleteForm(instance=profile)

    return render(
        request,
        "users/onboarding_step1.html",
        {"form": form, "next": next_url},
    )


# ---------------------------------------------------------------------------
# Onboarding — Step 2: Create workspace
# ---------------------------------------------------------------------------


@login_required
def onboarding_tenant_view(request):
    """
    Step 2 of onboarding — cannot be skipped.

    Save → create Tenant, assign profile as admin, redirect to dashboard.
    """
    profile = request.user.profile

    if profile.tenant_id is not None:
        return redirect("pages:dashboard")

    if request.method == "POST":
        form = TenantCreateForm(request.POST)
        if form.is_valid():
            create_tenant_for_profile(
                profile=profile,
                organization=form.cleaned_data["organization"],
            )
            return redirect("pages:dashboard")
    else:
        form = TenantCreateForm()

    return render(request, "users/onboarding_step2.html", {"form": form})


# ---------------------------------------------------------------------------
# Full profile settings
# ---------------------------------------------------------------------------


@login_required
def profile_view(request):
    """Full profile preferences — stays on page with success message on save."""
    profile = request.user.profile

    if request.method == "POST":
        form = ProfileSettingsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _("Your profile has been updated."))
            return redirect("users:profile")
    else:
        form = ProfileSettingsForm(instance=profile)

    return render(
        request, "users/profile.html", {"form": form, "saved_theme": profile.theme}
    )


# ---------------------------------------------------------------------------
# Account revoked
# ---------------------------------------------------------------------------


def account_revoked_view(request):
    """Shown when the user's profile.is_active is False (revoked from tenant)."""
    return render(request, "users/account_revoked.html", {})


# ---------------------------------------------------------------------------
# Member management — admin only
# ---------------------------------------------------------------------------


def _require_admin(request):
    """Return the admin profile or raise PermissionDenied."""
    if not request.user.is_authenticated:
        raise Http404
    profile = request.user.profile
    if profile.role != "admin" or not profile.tenant_id:
        raise PermissionDenied
    return profile


@login_required
def members_view(request):
    """List all members (active + inactive) in the admin's tenant."""
    admin_profile = _require_admin(request)
    members = (
        UserProfile.objects.filter(tenant=admin_profile.tenant)
        .select_related("user")
        .order_by("user__email")
    )
    invite_form = InviteMemberForm()
    return render(
        request,
        "users/members.html",
        {
            "members": members,
            "invite_form": invite_form,
            "admin_profile": admin_profile,
        },
    )


@login_required
@require_POST
def invite_member_view(request):
    """Admin invites a new member by email."""
    admin_profile = _require_admin(request)
    form = InviteMemberForm(request.POST)
    if form.is_valid():
        try:
            invite_member(
                admin_profile=admin_profile,
                email=form.cleaned_data["email"],
            )
            messages.success(
                request,
                _("%(email)s has been added to your workspace.")
                % {"email": form.cleaned_data["email"]},
            )
        except ValueError as exc:
            messages.error(request, str(exc))
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
    return redirect("users:members")


@login_required
@require_POST
def revoke_member_view(request, profile_id: uuid.UUID):
    """Admin revokes a member's access."""
    admin_profile = _require_admin(request)
    target = get_object_or_404(UserProfile, pk=profile_id, tenant=admin_profile.tenant)
    try:
        revoke_member(admin_profile=admin_profile, target_profile=target)
        messages.success(
            request,
            _("%(email)s has been removed from the workspace.")
            % {"email": target.user.email},
        )
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("users:members")


@login_required
@require_POST
def reengage_member_view(request, profile_id: uuid.UUID):
    """Admin re-engages a revoked member."""
    admin_profile = _require_admin(request)
    target = get_object_or_404(UserProfile, pk=profile_id, tenant=admin_profile.tenant)
    try:
        reengage_member(admin_profile=admin_profile, target_profile=target)
        messages.success(
            request,
            _("%(email)s has been re-added to the workspace.")
            % {"email": target.user.email},
        )
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("users:members")


# ---------------------------------------------------------------------------
# Theme — save preference to profile (authenticated users only)
# ---------------------------------------------------------------------------

_VALID_THEMES = {"corporate", "night", "system"}


@require_POST
def set_theme_view(request):
    """
    POST /theme/set/  { "theme": "corporate"|"night"|"system" }

    Authenticated:   save to UserProfile.theme, return JSON ok.
    Unauthenticated: 204 No Content (client already handled localStorage).
    """
    theme = request.POST.get("theme", "").strip()
    if theme not in _VALID_THEMES:
        return JsonResponse({"error": "invalid theme"}, status=400)

    if request.user.is_authenticated:
        profile = request.user.profile
        profile.theme = theme
        profile.save(update_fields=["theme", "updated_at"])
        return JsonResponse({"ok": True, "theme": theme})

    # Unauthenticated — nothing to persist server-side; the client uses localStorage.
    return JsonResponse({"ok": True, "theme": theme})
