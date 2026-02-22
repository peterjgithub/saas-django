"""
Custom User model and UserProfile.

User  — extends AbstractUser; email is the USERNAME_FIELD; no created_by/updated_by
        (sole exception in the codebase due to self-registration circular risk).
UserProfile — extends TimeStampedAuditModel; auto-created via post_save signal;
              holds all profile, locale, and tenant-membership fields.
"""

import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedAuditModel

# ---------------------------------------------------------------------------
# Custom manager
# ---------------------------------------------------------------------------


class UserManager(BaseUserManager):
    """Manager for email-based auth (no username field)."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError(_("An email address is required."))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self._create_user(email, password, **extra_fields)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class User(AbstractUser):
    """
    Custom user model.

    - Email is the login credential (USERNAME_FIELD = "email").
    - The inherited `username` field is removed.
    - UUID primary key — no enumerable integer IDs.
    - NO created_by / updated_by — self-registration circular risk.
    - NEVER hard-delete a User. Set is_active = False only.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None  # remove the username field entirely

    email = models.EmailField(
        unique=True,
        verbose_name=_("email address"),
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.UUIDField(null=True, blank=True)  # acting user UUID — no FK

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self) -> str:
        return self.email


# ---------------------------------------------------------------------------
# UserProfile
# ---------------------------------------------------------------------------

THEME_CHOICES = [
    ("corporate", _("Light (Corporate)")),
    ("night", _("Dark (Night)")),
    ("system", _("Follow system")),
]

ROLE_CHOICES = [
    ("admin", _("Admin")),
    ("member", _("Member")),
]


class UserProfile(TimeStampedAuditModel):
    """
    Extended profile for a User.

    Auto-created by post_save signal on User (see signals.py).
    NEVER hard-delete a UserProfile — soft-delete only (is_active = False).
    """

    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("user"),
    )

    # --- Display ---
    display_name = models.CharField(  # noqa: DJ001 — intentional: null means "not yet set"
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("display name"),
    )

    # --- Localisation (FK to core reference tables) ---
    language = models.ForeignKey(
        "core.Language",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="user_profiles",
        verbose_name=_("language"),
    )
    timezone = models.ForeignKey(
        "core.Timezone",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="user_profiles",
        verbose_name=_("timezone"),
    )
    country = models.ForeignKey(
        "core.Country",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="user_profiles",
        verbose_name=_("country"),
    )
    currency = models.ForeignKey(
        "core.Currency",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="user_profiles",
        verbose_name=_("currency"),
    )

    # --- UI preferences ---
    theme = models.CharField(
        max_length=20,
        choices=THEME_CHOICES,
        default="system",
        verbose_name=_("theme"),
    )

    # --- Consent ---
    marketing_emails = models.BooleanField(
        default=False,
        verbose_name=_("marketing emails"),
        help_text=_("Receive newsletters and promotional emails."),
    )

    # --- Onboarding gate ---
    profile_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("profile completed at"),
        help_text=_("Set when the user saves the profile form for the first time."),
    )

    # --- Tenant membership ---
    tenant = models.ForeignKey(
        "tenants.Tenant",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
        verbose_name=_("tenant"),
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        blank=True,
        default="member",
        verbose_name=_("role"),
    )
    tenant_joined_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("tenant joined at"),
    )
    tenant_revoked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("tenant revoked at"),
        help_text=_("Set on revocation; cleared on re-engagement."),
    )

    class Meta:
        verbose_name = _("user profile")
        verbose_name_plural = _("user profiles")

    def __str__(self) -> str:
        return f"Profile({self.user.email})"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def derive_display_name(email: str) -> str:
    """
    Derive a friendly display name from an email address.

    Rules:
    - Take the local-part (left of @).
    - If it contains a dot, take the substring left of the first dot.
    - Capitalise the result.

    Examples:
        peter.janssens@acme.com  → "Peter"
        alice@example.com        → "Alice"
    """
    local = email.split("@")[0]
    if "." in local:
        local = local.split(".")[0]
    return local.capitalize()


__all__ = [
    "User",
    "UserManager",
    "UserProfile",
    "derive_display_name",
]
