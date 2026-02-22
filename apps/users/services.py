"""
Service functions for the users app.

All business logic lives here — views stay thin.
Each function takes explicit arguments; no request objects passed in.
"""

from django.contrib.auth import authenticate
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import Country, Language, Timezone
from apps.tenants.models import Tenant
from apps.users.models import User, UserProfile, derive_display_name

# ---------------------------------------------------------------------------
# I18N helpers
# ---------------------------------------------------------------------------

# Map ISO 639-1 alpha-2 language codes (as stored in core.Language.code) to the
# Django LANGUAGES codes used in this project.  Any unmapped code falls back to "en".
_LANGUAGE_CODE_MAP: dict[str, str] = {
    "nl": "nl-be",
    "fr": "fr-be",
    "en": "en",
}


def locale_code_for_language(language) -> str:
    """
    Return the Django LANGUAGES code for a core.Language instance (or None).

    Examples:
        Language(code="nl") → "nl-be"
        Language(code="fr") → "fr-be"
        Language(code="de") → "en"   (unsupported — fall back to English)
        None                → "en"
    """
    if language is None:
        return "en"
    return _LANGUAGE_CODE_MAP.get(language.code, "en")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def register_user(
    email: str,
    password: str,
    tz_detect: str = "",
    lang_detect: str = "",
) -> User:
    """
    Create a new User and return it.

    The UserProfile is created automatically by the post_save signal.
    After creation we attempt to pre-fill timezone and language from
    the browser-detected values if they match records in the DB.
    """
    user = User.objects.create_user(email=email.lower(), password=password)

    # Pre-fill display_name (signal may already do this — be idempotent)
    profile: UserProfile = user.profile
    if not profile.display_name:
        profile.display_name = derive_display_name(email)

    # Pre-fill timezone from browser hint
    if tz_detect:
        tz_obj = Timezone.objects.filter(name=tz_detect).first()
        if tz_obj:
            profile.timezone = tz_obj

    # Pre-fill language from browser hint (e.g. "en-US" → try "en" or "en-US")
    if lang_detect:
        lang_code = lang_detect.lower().replace("-", "_")
        # Try exact match first, then prefix
        lang_obj = Language.objects.filter(code__iexact=lang_code).first()
        if not lang_obj and "_" in lang_code:
            lang_obj = Language.objects.filter(
                code__iexact=lang_code.split("_")[0]
            ).first()
        if lang_obj:
            profile.language = lang_obj

    profile.save(update_fields=["display_name", "timezone", "language"])
    return user


def authenticate_user(email: str, password: str) -> User | None:
    """Authenticate by email + password. Returns User or None."""
    return authenticate(email=email.lower(), password=password)


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------


def complete_profile(
    profile: UserProfile,
    display_name: str,
    timezone_obj: Timezone | None,
    country_obj: Country | None = None,
) -> None:
    """
    Mark Step 1 of onboarding complete.

    Sets profile_completed_at to now if not already set.
    """
    profile.display_name = display_name or profile.display_name
    if timezone_obj is not None:
        profile.timezone = timezone_obj
    if country_obj is not None:
        profile.country = country_obj
    if not profile.profile_completed_at:
        profile.profile_completed_at = timezone.now()
    profile.save(
        update_fields=[
            "display_name",
            "timezone",
            "country",
            "profile_completed_at",
        ]
    )


def create_tenant_for_profile(profile: UserProfile, organization: str) -> Tenant:
    """
    Create a Tenant and assign it to the profile as admin.

    Step 2 of onboarding.
    """
    tenant = Tenant.objects.create(
        organization=organization,
        created_by=profile.user.pk,
    )
    profile.tenant = tenant
    profile.role = "admin"
    profile.tenant_joined_at = timezone.now()
    profile.save(update_fields=["tenant", "role", "tenant_joined_at"])
    return tenant


# ---------------------------------------------------------------------------
# Member management
# ---------------------------------------------------------------------------


def invite_member(admin_profile: UserProfile, email: str) -> UserProfile:
    """
    Invite a user to the admin's tenant.

    - If no User exists for this email, create one with an unusable password
      (they must use password-reset to set their password).
    - The invited user's profile must have tenant=None (no second workspace).
    - Sets profile.tenant, role=member, tenant_joined_at=now(), is_active=True.
    - Raises ValueError on constraint violations.
    """
    if not admin_profile.tenant:
        raise ValueError(_("Admin has no tenant to invite to."))

    email = email.lower()

    # Get-or-create the user
    user, created = User.objects.get_or_create(
        email=email,
        defaults={},
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])

    member_profile: UserProfile = user.profile

    # Guard: cannot join a second workspace
    if member_profile.tenant_id is not None:
        raise ValueError(
            _(
                "%(email)s already belongs to a workspace. "
                "They must register a new account to join yours."
            )
            % {"email": email}
        )

    member_profile.tenant = admin_profile.tenant
    member_profile.role = "member"
    member_profile.tenant_joined_at = timezone.now()
    member_profile.tenant_revoked_at = None
    member_profile.is_active = True
    member_profile.deleted_by = None
    member_profile.deleted_at = None
    member_profile.save(
        update_fields=[
            "tenant",
            "role",
            "tenant_joined_at",
            "tenant_revoked_at",
            "is_active",
            "deleted_by",
            "deleted_at",
        ]
    )
    return member_profile


def revoke_member(admin_profile: UserProfile, target_profile: UserProfile) -> None:
    """
    Revoke a member's access to the tenant.

    - Sets is_active=False, tenant_revoked_at=now(), deleted_by=admin uuid.
    - Does NOT clear the tenant FK.
    - Admin cannot revoke themselves.
    """
    if admin_profile.pk == target_profile.pk:
        raise ValueError(_("You cannot revoke your own access."))
    if target_profile.tenant_id != admin_profile.tenant_id:
        raise ValueError(_("That member does not belong to your tenant."))

    target_profile.is_active = False
    target_profile.tenant_revoked_at = timezone.now()
    target_profile.deleted_by = admin_profile.user.pk
    target_profile.save(update_fields=["is_active", "tenant_revoked_at", "deleted_by"])


def reengage_member(admin_profile: UserProfile, target_profile: UserProfile) -> None:
    """
    Re-engage a previously revoked member.
    """
    if target_profile.tenant_id != admin_profile.tenant_id:
        raise ValueError(_("That member does not belong to your tenant."))

    target_profile.is_active = True
    target_profile.tenant_revoked_at = None
    target_profile.deleted_by = None
    target_profile.deleted_at = None
    target_profile.save(
        update_fields=["is_active", "tenant_revoked_at", "deleted_by", "deleted_at"]
    )


def promote_to_admin(admin_profile: UserProfile, target_profile: UserProfile) -> None:
    """
    Promote a member to the admin role.

    - Only a current admin may promote.
    - The target must belong to the same tenant.
    - An admin can promote themselves (no-op — already admin).
    """
    if target_profile.tenant_id != admin_profile.tenant_id:
        raise ValueError(_("That member does not belong to your tenant."))
    if target_profile.role == "admin":
        return  # already admin — idempotent
    target_profile.role = "admin"
    target_profile.updated_by = admin_profile.user.pk
    target_profile.save(update_fields=["role", "updated_by"])


def set_member_role(
    admin_profile: UserProfile,
    target_profile: UserProfile,
    role: str,
) -> None:
    """
    Set the role of a member to 'admin' or 'member'.

    - Only a current admin may change roles.
    - The target must belong to the same tenant.
    - An admin cannot demote themselves.
    - Idempotent — no-op if the role is already set to the requested value.
    """
    if role not in ("admin", "member"):
        raise ValueError(_("Invalid role."))
    if target_profile.tenant_id != admin_profile.tenant_id:
        raise ValueError(_("That member does not belong to your tenant."))
    if admin_profile.pk == target_profile.pk and role == "member":
        raise ValueError(_("You cannot remove your own admin role."))
    if target_profile.role == role:
        return  # already the requested role — idempotent
    target_profile.role = role
    target_profile.updated_by = admin_profile.user.pk
    target_profile.save(update_fields=["role", "updated_by"])


def deactivate_member(admin_profile: UserProfile, target_profile: UserProfile) -> None:
    """
    Deactivate a member account (soft-revoke: profile.is_active = False).

    This is identical to revoke_member in behaviour; it is exposed under a
    separate name so the Settings > Users UI can use the "Deactivate" label
    while the existing /settings/members/ endpoint keeps the "Revoke" label.
    Admin cannot deactivate themselves.
    """
    if admin_profile.pk == target_profile.pk:
        raise ValueError(_("You cannot deactivate your own account."))
    if target_profile.tenant_id != admin_profile.tenant_id:
        raise ValueError(_("That member does not belong to your tenant."))

    target_profile.is_active = False
    target_profile.tenant_revoked_at = timezone.now()
    target_profile.deleted_by = admin_profile.user.pk
    target_profile.save(update_fields=["is_active", "tenant_revoked_at", "deleted_by"])


__all__ = [
    "locale_code_for_language",
    "register_user",
    "authenticate_user",
    "complete_profile",
    "create_tenant_for_profile",
    "invite_member",
    "revoke_member",
    "reengage_member",
    "promote_to_admin",
    "set_member_role",
    "deactivate_member",
]
