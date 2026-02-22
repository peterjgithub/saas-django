"""
Phase 3 member management tests.
"""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.tenants.models import Tenant
from apps.users.models import User


def _make_admin(email="admin@example.com"):
    """Create a fully onboarded admin user."""
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


class MembersViewTest(TestCase):
    def setUp(self):
        self.admin_user, self.tenant = _make_admin()
        self.url = reverse("users:members")

    def test_admin_can_access_members_page(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/members.html")

    def test_non_admin_gets_403(self):
        member_user = _make_member(self.tenant, email="member2@example.com")
        self.client.force_login(member_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(
            response,
            "/login/?next=/settings/members/",
            fetch_redirect_response=False,
        )

    def test_members_list_shows_all_tenant_members(self):
        _make_member(self.tenant, email="active@example.com")
        _make_member(self.tenant, email="inactive@example.com", is_active=False)
        self.client.force_login(self.admin_user)
        response = self.client.get(self.url)
        self.assertContains(response, "active@example.com")
        self.assertContains(response, "inactive@example.com")


class InviteMemberViewTest(TestCase):
    def setUp(self):
        self.admin_user, self.tenant = _make_admin()
        self.url = reverse("users:invite_member")

    def test_admin_can_invite_new_email(self):
        self.client.force_login(self.admin_user)
        self.client.post(self.url, {"email": "newbie@example.com"})
        user = User.objects.filter(email="newbie@example.com").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.profile.tenant, self.tenant)
        self.assertEqual(user.profile.role, "member")

    def test_admin_can_invite_existing_user_without_tenant(self):
        """Existing user with no tenant gets assigned to this tenant."""
        existing = User.objects.create_user(
            email="existing@example.com", password="pass1234!"
        )
        self.client.force_login(self.admin_user)
        self.client.post(self.url, {"email": "existing@example.com"})
        existing.profile.refresh_from_db()
        self.assertEqual(existing.profile.tenant, self.tenant)
        self.assertEqual(existing.profile.role, "member")

    def test_cannot_invite_user_who_already_has_tenant(self):
        """User already in a different org cannot be invited."""
        other_tenant = Tenant.objects.create(organization="Other Corp")
        other_user = User.objects.create_user(
            email="taken@example.com", password="pass1234!"
        )
        p = other_user.profile
        p.tenant = other_tenant
        p.role = "member"
        p.tenant_joined_at = timezone.now()
        p.save()
        self.client.force_login(self.admin_user)
        response = self.client.post(
            self.url, {"email": "taken@example.com"}, follow=True
        )
        # Should show error message, user not moved
        msgs = list(response.context["messages"])
        self.assertTrue(any("already" in str(m).lower() for m in msgs))
        other_user.profile.refresh_from_db()
        self.assertEqual(other_user.profile.tenant, other_tenant)

    def test_non_admin_gets_403(self):
        member_user = _make_member(self.tenant, email="m@example.com")
        self.client.force_login(member_user)
        response = self.client.post(self.url, {"email": "x@example.com"})
        self.assertEqual(response.status_code, 403)


class RevokeMemberViewTest(TestCase):
    def setUp(self):
        self.admin_user, self.tenant = _make_admin()
        self.member_user = _make_member(self.tenant, email="target@example.com")

    def test_admin_can_revoke_member(self):
        url = reverse("users:revoke_member", args=[self.member_user.profile.pk])
        self.client.force_login(self.admin_user)
        self.client.post(url)
        self.member_user.profile.refresh_from_db()
        self.assertFalse(self.member_user.profile.is_active)
        self.assertIsNotNone(self.member_user.profile.tenant_revoked_at)

    def test_admin_cannot_revoke_themselves(self):
        url = reverse("users:revoke_member", args=[self.admin_user.profile.pk])
        self.client.force_login(self.admin_user)
        response = self.client.post(url, follow=True)
        msgs = list(response.context["messages"])
        self.assertTrue(any("cannot revoke" in str(m).lower() for m in msgs))
        # Admin should still be active
        self.admin_user.profile.refresh_from_db()
        self.assertTrue(self.admin_user.profile.is_active)

    def test_revoked_member_redirected_to_account_revoked(self):
        """Middleware should catch is_active=False and redirect to revoked page."""
        self.member_user.profile.is_active = False
        self.member_user.profile.tenant_revoked_at = timezone.now()
        self.member_user.profile.save()
        self.client.force_login(self.member_user)
        response = self.client.get("/dashboard/")
        self.assertRedirects(
            response, "/account/revoked/", fetch_redirect_response=False
        )

    def test_non_admin_gets_403_on_revoke(self):
        other_member = _make_member(self.tenant, email="other@example.com")
        url = reverse("users:revoke_member", args=[self.member_user.profile.pk])
        self.client.force_login(other_member)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)


class ReengageMemberViewTest(TestCase):
    def setUp(self):
        self.admin_user, self.tenant = _make_admin()
        self.member_user = _make_member(
            self.tenant, email="revoked@example.com", is_active=False
        )
        self.member_user.profile.tenant_revoked_at = timezone.now()
        self.member_user.profile.save()

    def test_admin_can_reengage_revoked_member(self):
        url = reverse("users:reengage_member", args=[self.member_user.profile.pk])
        self.client.force_login(self.admin_user)
        self.client.post(url)
        self.member_user.profile.refresh_from_db()
        self.assertTrue(self.member_user.profile.is_active)
        self.assertIsNone(self.member_user.profile.tenant_revoked_at)

    def test_reengage_clears_revocation_fields(self):
        url = reverse("users:reengage_member", args=[self.member_user.profile.pk])
        self.client.force_login(self.admin_user)
        self.client.post(url)
        self.member_user.profile.refresh_from_db()
        self.assertIsNone(self.member_user.profile.tenant_revoked_at)
        self.assertIsNone(self.member_user.profile.deleted_by)

    def test_non_admin_gets_403_on_reengage(self):
        other_member = _make_member(self.tenant, email="other2@example.com")
        url = reverse("users:reengage_member", args=[self.member_user.profile.pk])
        self.client.force_login(other_member)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
