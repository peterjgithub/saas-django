"""
Forms for the users app.

- LoginForm         — email + password
- RegisterForm      — email + password + hidden tz_detect/lang_detect
- ProfileCompleteForm — display_name + timezone (onboarding step 1)
- TenantCreateForm  — organization (onboarding step 2)
- ProfileSettingsForm — full profile preferences
- InviteMemberForm  — admin invites by email
- OrgSettingsForm   — organisation name + logo (settings > general)
- InviteAcceptForm  — invited user sets their password via the accept link
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.models import Country, Timezone
from apps.users.models import THEME_CHOICES, UserProfile


class LoginForm(forms.Form):
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "placeholder": _("you@example.com"),
                "class": "input w-full text-base",
            }
        ),
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "placeholder": "••••••••",
                "class": "input w-full text-base",
            }
        ),
    )


class RegisterForm(forms.Form):
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "placeholder": _("you@example.com"),
                "class": "input w-full text-base",
            }
        ),
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": "••••••••",
                "class": "input w-full text-base",
            }
        ),
    )
    # Hidden — populated by JS before form submit
    tz_detect = forms.CharField(required=False, widget=forms.HiddenInput())
    lang_detect = forms.CharField(required=False, widget=forms.HiddenInput())
    country_detect = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean_email(self):
        from apps.users.models import User

        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("An account with this email already exists."))
        return email


class ProfileCompleteForm(forms.ModelForm):
    """Step 1 of onboarding — display name + timezone + country."""

    class Meta:
        model = UserProfile
        fields = ["display_name", "timezone", "country"]
        widgets = {
            "display_name": forms.TextInput(
                attrs={
                    "autocomplete": "name",
                    "class": "input w-full text-base",
                    "placeholder": _("Your name"),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["timezone"].queryset = Timezone.objects.all().order_by("name")
        self.fields["timezone"].empty_label = _("Select your timezone")
        self.fields["timezone"].widget.attrs.update(
            {"class": "select w-full text-base"}
        )
        self.fields["timezone"].required = False

        self.fields["country"].queryset = Country.objects.all().order_by("name")
        self.fields["country"].empty_label = _("Select your country")
        self.fields["country"].widget.attrs.update({"class": "select w-full text-base"})
        self.fields["country"].required = False


class TenantCreateForm(forms.Form):
    """Step 2 of onboarding — create the workspace."""

    organization = forms.CharField(
        label=_("Organisation name"),
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "organization",
                "class": "input w-full text-base",
                "placeholder": _("Acme Inc."),
            }
        ),
    )


class ProfileSettingsForm(forms.ModelForm):
    """Full profile preferences — everything except email, password, and language."""

    class Meta:
        model = UserProfile
        fields = [
            "display_name",
            "timezone",
            "country",
            "theme",
            "marketing_emails",
        ]
        widgets = {
            "display_name": forms.TextInput(
                attrs={"autocomplete": "name", "class": "input w-full text-base"}
            ),
            "marketing_emails": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["timezone"].queryset = Timezone.objects.all().order_by("name")
        self.fields["timezone"].empty_label = _("Select timezone")
        self.fields["timezone"].widget.attrs.update(
            {"class": "select w-full text-base"}
        )
        self.fields["timezone"].required = False

        self.fields["country"].queryset = Country.objects.all().order_by("name")
        self.fields["country"].empty_label = _("Select country")
        self.fields["country"].widget.attrs.update({"class": "select w-full text-base"})
        self.fields["country"].required = False

        self.fields["theme"].widget = forms.Select(
            choices=THEME_CHOICES,
            attrs={"class": "select w-full text-base"},
        )


class InviteMemberForm(forms.Form):
    email = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "placeholder": _("colleague@example.com"),
                "class": "input w-full text-base",
            }
        ),
    )


class OrgSettingsForm(forms.ModelForm):
    """Settings > General — edit organisation name and logo."""

    class Meta:
        from apps.tenants.models import Tenant

        model = Tenant
        fields = ["organization", "logo"]
        widgets = {
            "organization": forms.TextInput(attrs={"class": "input w-full text-base"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organization"].label = _("Organisation name")
        self.fields["logo"].required = False
        self.fields["logo"].label = _("Logo")
        self.fields["logo"].widget.attrs.update(
            {"class": "file-input w-full text-base"}
        )


__all__ = [
    "LoginForm",
    "RegisterForm",
    "ProfileCompleteForm",
    "TenantCreateForm",
    "ProfileSettingsForm",
    "InviteMemberForm",
    "OrgSettingsForm",
    "InviteAcceptForm",
]


class InviteAcceptForm(forms.Form):
    """
    Presented to an invited user when they follow their invite link.

    Only collects a password (the email is already known and shown read-only).
    Both fields use password-manager-friendly autocomplete attributes.
    """

    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "class": "input w-full text-base",
            }
        ),
        min_length=8,
    )
    confirm_password = forms.CharField(
        label=_("Confirm password"),
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "class": "input w-full text-base",
            }
        ),
    )

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("password")
        pw2 = cleaned.get("confirm_password")
        if pw and pw2 and pw != pw2:
            raise forms.ValidationError(_("Passwords do not match."))
        return cleaned
