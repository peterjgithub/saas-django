"""
Phase 5 organisation settings tests.

Covers:
- /settings/ redirect
- /settings/users/ — access control, invite, promote, deactivate, reengage
- /settings/general/ — access control, save org name
- /settings/billing/ — access control, placeholder renders
"""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.tenants.models import Tenant
from apps.users.models import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_admin(email="admin@example.com"):
    """Create a fully onboarded admin user with a tenant."""
    tenant = Tenant.objects.create(organization="ACME Corp")
    user = User.objects.create_user(email=email, password="pass1234!")
    p = user.profile
    p.profile_completed_at = timezone.now()
    p.tenant = tenant
    p.role = "admin"
    p.tenant_joined_at = timezone.now()
    p.save()
    return user, tenant


def _make_member(tenant, email="member@example.com", is_active=True):
    """Create a member user attached to the given tenant."""
    user = User.objects.create_user(email=email, password="pass1234!")
    p = user.profile
    p.profile_completed_at = timezone.now()
    p.tenant = tenant
    p.role = "member"
    p.tenant_joined_at = timezone.now()
    p.is_active = is_active
    p.save()
    return user


# ---------------------------------------------------------------------------
# /settings/ — redirect
# ---------------------------------------------------------------------------


class SettingsRedirectViewTest(TestCase):
    def test_redirects_to_settings_users(self):
        admin, _ = _make_admin()
        self.client.force_login(admin)
        response = self.client.get(reverse("users:settings"))
        self.assertRedirects(response, reverse("users:settings_users"))

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("users:settings"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])


# ---------------------------------------------------------------------------
# /settings/users/ — access control
# ---------------------------------------------------------------------------


class SettingsUsersAccessTest(TestCase):
    def setUp(self):
        self.admin, self.tenant = _make_admin()
        self.url = reverse("users:settings_users")

    def test_admin_can_access(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/settings_users.html")

    def test_member_gets_403(self):
        member = _make_member(self.tenant)
        self.client.force_login(member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_anonymous_redirected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)


# ---------------------------------------------------------------------------
# /settings/users/ — invite action
# ---------------------------------------------------------------------------


class SettingsUsersInviteTest(TestCase):
    def setUp(self):
        self.admin, self.tenant = _make_admin()
        self.url = reverse("users:settings_users")

    def test_invite_new_user_creates_and_attaches(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url,
            {"action": "invite", "email": "newuser@example.com"},
        )
        self.assertRedirects(response, self.url)
        new_user = User.objects.get(email="newuser@example.com")
        self.assertEqual(new_user.profile.tenant, self.tenant)
        self.assertEqual(new_user.profile.role, "member")
        self.assertTrue(new_user.profile.is_active)

    def test_invite_existing_user_without_tenant(self):
        orphan = User.objects.create_user(email="orphan@example.com", password="x")
        p = orphan.profile
        p.profile_completed_at = timezone.now()
        p.save()
        self.client.force_login(self.admin)
        self.client.post(self.url, {"action": "invite", "email": "orphan@example.com"})
        orphan.profile.refresh_from_db()
        self.assertEqual(orphan.profile.tenant, self.tenant)

    def test_invite_user_already_in_tenant_shows_error(self):
        existing = _make_member(self.tenant, email="existing@example.com")
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url,
            {"action": "invite", "email": existing.email},
            follow=True,
        )
        messages = list(response.context["messages"])
        self.assertTrue(
            any(
                "already" in str(m).lower() or "tenant" in str(m).lower()
                for m in messages
            )
        )


# ---------------------------------------------------------------------------
# /settings/users/ — promote action
# ---------------------------------------------------------------------------


class SettingsUsersPromoteTest(TestCase):
    def setUp(self):
        self.admin, self.tenant = _make_admin()
        self.member = _make_member(self.tenant)
        self.url = reverse("users:settings_users")

    def test_promote_member_to_admin(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url,
            {"action": "promote", "profile_id": str(self.member.profile.pk)},
        )
        self.assertRedirects(response, self.url)
        self.member.profile.refresh_from_db()
        self.assertEqual(self.member.profile.role, "admin")

    def test_promote_already_admin_is_idempotent(self):
        """Promoting an admin again should not error."""
        second_admin = _make_member(self.tenant, email="admin2@example.com")
        second_admin.profile.role = "admin"
        second_admin.profile.save()
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url,
            {"action": "promote", "profile_id": str(second_admin.profile.pk)},
        )
        self.assertRedirects(response, self.url)

    def test_promote_member_from_different_tenant_fails(self):
        other_tenant = Tenant.objects.create(organization="Other Org")
        other_user = _make_member(other_tenant, email="other@example.com")
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url,
            {"action": "promote", "profile_id": str(other_user.profile.pk)},
            follow=True,
        )
        # Should show error — member not found in this tenant
        messages = list(response.context["messages"])
        self.assertTrue(any("not found" in str(m).lower() for m in messages))


# ---------------------------------------------------------------------------
# /settings/users/ — deactivate action
# ---------------------------------------------------------------------------


class SettingsUsersDeactivateTest(TestCase):
    def setUp(self):
        self.admin, self.tenant = _make_admin()
        self.member = _make_member(self.tenant)
        self.url = reverse("users:settings_users")

    def test_deactivate_member(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url,
            {"action": "deactivate", "profile_id": str(self.member.profile.pk)},
        )
        self.assertRedirects(response, self.url)
        self.member.profile.refresh_from_db()
        self.assertFalse(self.member.profile.is_active)
        self.assertIsNotNone(self.member.profile.tenant_revoked_at)

    def test_admin_cannot_deactivate_themselves(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url,
            {"action": "deactivate", "profile_id": str(self.admin.profile.pk)},
            follow=True,
        )
        messages = list(response.context["messages"])
        self.assertTrue(
            any(
                "deactivate" in str(m).lower() or "own" in str(m).lower()
                for m in messages
            )
        )
        self.admin.profile.refresh_from_db()
        self.assertTrue(self.admin.profile.is_active)


# ---------------------------------------------------------------------------
# /settings/users/ — reengage action
# ---------------------------------------------------------------------------


class SettingsUsersReengageTest(TestCase):
    def setUp(self):
        self.admin, self.tenant = _make_admin()
        self.revoked = _make_member(
            self.tenant, email="revoked@example.com", is_active=False
        )
        self.revoked.profile.tenant_revoked_at = timezone.now()
        self.revoked.profile.save()
        self.url = reverse("users:settings_users")

    def test_reengage_revoked_member(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url,
            {"action": "reengage", "profile_id": str(self.revoked.profile.pk)},
        )
        self.assertRedirects(response, self.url)
        self.revoked.profile.refresh_from_db()
        self.assertTrue(self.revoked.profile.is_active)
        self.assertIsNone(self.revoked.profile.tenant_revoked_at)


# ---------------------------------------------------------------------------
# /settings/general/ — access control + save
# ---------------------------------------------------------------------------


class SettingsGeneralViewTest(TestCase):
    def setUp(self):
        self.admin, self.tenant = _make_admin()
        self.url = reverse("users:settings_general")

    def test_admin_can_access(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/settings_general.html")

    def test_member_gets_403(self):
        member = _make_member(self.tenant)
        self.client.force_login(member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_save_org_name(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {"organization": "New Corp Name"})
        self.assertRedirects(response, self.url)
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.organization, "New Corp Name")

    def test_save_empty_org_name_shows_error(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {"organization": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "organization", "This field is required."
        )

    def test_save_with_logo_upload(self):
        """A minimal valid PNG upload should be accepted."""
        import struct
        import zlib

        def _make_png():
            def chunk(name, data):
                c = name + data
                return (
                    struct.pack(">I", len(data))
                    + c
                    + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
                )

            ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
            raw = b"\x00\xff\x00\x00"
            return (
                b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", ihdr_data)
                + chunk(b"IDAT", zlib.compress(raw))
                + chunk(b"IEND", b"")
            )

        logo = SimpleUploadedFile("logo.png", _make_png(), content_type="image/png")
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url,
            {"organization": "ACME Corp", "logo": logo},
        )
        self.assertRedirects(response, self.url)
        self.tenant.refresh_from_db()
        self.assertTrue(bool(self.tenant.logo))


# ---------------------------------------------------------------------------
# /settings/billing/ — access control + placeholder
# ---------------------------------------------------------------------------


class SettingsBillingViewTest(TestCase):
    def setUp(self):
        self.admin, self.tenant = _make_admin()
        self.url = reverse("users:settings_billing")

    def test_admin_can_access(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/settings_billing.html")
        self.assertContains(response, "coming soon")

    def test_member_gets_403(self):
        member = _make_member(self.tenant)
        self.client.force_login(member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
