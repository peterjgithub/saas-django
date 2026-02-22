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

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import activate, get_language
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.core.models import Country, Timezone
from apps.users.forms import (
    InviteMemberForm,
    LoginForm,
    ProfileCompleteForm,
    ProfileSettingsForm,
    RegisterForm,
    TenantCreateForm,
)
from apps.users.geo import country_code_from_timezone, get_client_ip, lookup_from_ip
from apps.users.models import UserProfile
from apps.users.services import (
    authenticate_user,
    complete_profile,
    create_tenant_for_profile,
    invite_member,
    locale_code_for_language,
    reengage_member,
    register_user,
    revoke_member,
)

# ---------------------------------------------------------------------------
# I18N helpers
# ---------------------------------------------------------------------------


def _apply_language(locale: str, response):
    """
    Activate *locale* for the current thread and set the Django language cookie
    on *response* so LocaleMiddleware picks it up on the next request.

    Django 4+ removed LANGUAGE_SESSION_KEY; the cookie is now the sole
    persistence mechanism used by get_language_from_request().
    """
    activate(locale)
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        locale,
        max_age=settings.LANGUAGE_COOKIE_AGE,
        path=settings.LANGUAGE_COOKIE_PATH,
        domain=settings.LANGUAGE_COOKIE_DOMAIN,
        secure=settings.LANGUAGE_COOKIE_SECURE,
        httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
        samesite=settings.LANGUAGE_COOKIE_SAMESITE,
    )
    return response


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
            tz_detect = form.cleaned_data.get("tz_detect", "")
            lang_detect = form.cleaned_data.get("lang_detect", "")
            country_detect = form.cleaned_data.get("country_detect", "")
            user = register_user(
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                tz_detect=tz_detect,
                lang_detect=lang_detect,
            )
            login(request, user)
            # Preserve browser hints in session for use on the onboarding step-1 page
            if tz_detect:
                request.session["tz_detect"] = tz_detect
            if lang_detect:
                request.session["lang_detect"] = lang_detect
            if country_detect:
                request.session["country_detect"] = country_detect
            # Set Django locale immediately from browser hint so the very next
            # page (profile/complete) renders in the user's detected language.
            lang_obj = user.profile.language  # pre-filled by register_user()
            locale = locale_code_for_language(lang_obj)
            return _apply_language(locale, redirect("users:profile_complete"))
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


def _org_suggestion_from_email(email: str) -> str:
    """
    Derive an organisation name suggestion from the domain part of an email.

    "peter@acme.com"        → "Acme"
    "info@my-company.co.uk" → "My Company"
    """
    try:
        domain = email.split("@")[1]  # e.g. "acme.com"
        stem = domain.rsplit(".", 1)[0]  # strip last extension: "acme"
        # strip a second extension for multi-part TLDs (co.uk, com.au, etc.)
        if "." in stem:
            stem = stem.rsplit(".", 1)[-1]
        return stem.replace("-", " ").replace("_", " ").title()
    except IndexError, AttributeError:
        return ""


@login_required
def profile_complete_view(request):
    """
    Step 1 of onboarding.

    On GET — builds smart initial values by merging:
      1. Already-saved profile values (highest priority)
      2. Browser hints from registration (tz_detect / lang_detect stored in session)
      3. IP-based geolocation (lowest priority, best-effort)

    Shows a hint banner the first time so the user knows where the values
    came from.  Once the form has been saved the banner disappears.

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
                country_obj=form.cleaned_data.get("country"),
            )
            # Mark that suggestions have been confirmed — hide banner on next visit
            request.session["profile_suggestions_confirmed"] = True
            return redirect("users:onboarding_create_tenant")
    else:
        # Build initial data by layering sources lowest → highest priority
        initial = {}

        # Layer 1: IP-based geo (lowest priority)
        ip = get_client_ip(request)
        geo = lookup_from_ip(ip)

        if geo.get("timezone") and not profile.timezone_id:
            tz_obj = Timezone.objects.filter(name=geo["timezone"]).first()
            if tz_obj:
                initial["timezone"] = tz_obj.pk

        if geo.get("country") and not profile.country_id:
            country_obj = Country.objects.filter(code=geo["country"]).first()
            if country_obj:
                initial["country"] = country_obj.pk

        # Layer 2: browser hints stored in session at registration (override geo)
        sess_tz = request.session.get("tz_detect", "")
        sess_country = request.session.get("country_detect", "")

        if sess_tz and not profile.timezone_id:
            tz_obj = Timezone.objects.filter(name=sess_tz).first()
            if tz_obj:
                initial["timezone"] = tz_obj.pk

        # country_detect comes from the region subtag of navigator.language
        # e.g. "nl-BE" → "BE".  This is a browser signal, works on localhost.
        if sess_country and not profile.country_id:
            country_obj = Country.objects.filter(code__iexact=sess_country).first()
            if country_obj:
                initial["country"] = country_obj.pk

        # Fallback: infer country from the browser timezone when locale gave no
        # region subtag (e.g. navigator.language = "en" or "nl" without "-BE").
        if not initial.get("country") and not profile.country_id:
            tz_name = sess_tz or geo.get("timezone", "")
            if tz_name:
                cc = country_code_from_timezone(tz_name)
                if cc:
                    country_obj = Country.objects.filter(code=cc).first()
                    if country_obj:
                        initial["country"] = country_obj.pk

        form = ProfileCompleteForm(instance=profile, initial=initial)

    # Show the hint banner only when the user has never saved the profile AND
    # hasn't already confirmed suggestions in this session.
    has_suggestions = not profile.profile_completed_at and not request.session.get(
        "profile_suggestions_confirmed"
    )

    return render(
        request,
        "users/onboarding_step1.html",
        {
            "form": form,
            "next": next_url,
            "has_suggestions": has_suggestions,
        },
    )


# ---------------------------------------------------------------------------
# Onboarding — Step 2: Create workspace
# ---------------------------------------------------------------------------


@login_required
def onboarding_tenant_view(request):
    """
    Step 2 of onboarding — cannot be skipped.

    On GET — pre-fills organisation name derived from the user's email domain.
    Shows a hint banner the first time only.

    Save → create Tenant, assign profile as admin, redirect to dashboard.
    """
    profile = request.user.profile

    if profile.tenant_id is not None:
        return redirect("pages:dashboard")

    # Derive a suggestion from the email domain if this is the first visit
    org_suggestion = _org_suggestion_from_email(request.user.email)
    # Banner only shown until the user has actually submitted (saved) once
    org_from_email = not request.session.get("org_suggestion_confirmed") and bool(
        org_suggestion
    )

    if request.method == "POST":
        form = TenantCreateForm(request.POST)
        if form.is_valid():
            create_tenant_for_profile(
                profile=profile,
                organization=form.cleaned_data["organization"],
            )
            request.session["org_suggestion_confirmed"] = True
            return redirect("pages:dashboard")
    else:
        form = TenantCreateForm(initial={"organization": org_suggestion})

    return render(
        request,
        "users/onboarding_step2.html",
        {
            "form": form,
            "org_from_email": org_from_email,
        },
    )


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
            # Preserve the current active locale (set by LocaleMiddleware from the
            # django_language cookie) — language is now changed via the navbar/profile
            # language buttons (set_language), not through this form.
            locale = get_language() or "en"
            messages.success(request, _("Your profile has been updated."))
            return _apply_language(locale, redirect("users:profile"))
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
