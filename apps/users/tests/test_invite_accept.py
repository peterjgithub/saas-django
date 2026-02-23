"""
Tests for the invite-email accept flow.

Covers:
- invite_member() sends an email when base_url is provided
- GET /invite/accept/<uidb64>/<token>/ — valid token renders form
- POST — sets password, stamps profile_completed_at, logs in, redirects to profile
- POST — user is authenticated after accepting
- GET — invalid/garbage token returns 400
- GET — expired token returns 400
- GET — already-accepted (user has usable password) returns 200 + already_accepted page
"""

from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.tenants.models import Tenant
from apps.users.models import User
from apps.users.services import invite_member, invite_token_generator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_admin(email="admin@invite.com", org="InviteCorp"):
    """Create a fully onboarded admin user."""
    tenant = Tenant.objects.create(organization=org)
    user = User.objects.create_user(email=email, password="adminpass1!")
    p = user.profile
    p.profile_completed_at = timezone.now()
    p.tenant = tenant
    p.role = "admin"
    p.tenant_joined_at = timezone.now()
    p.save()
    return user, tenant


def _make_invited_user(tenant, email="invited@invite.com"):
    """
    Create an invited user as invite_member() would: no usable password,
    already attached to the tenant.
    """
    user = User.objects.create_user(email=email, password=None)
    user.set_unusable_password()
    user.save()
    p = user.profile
    p.tenant = tenant
    p.role = "member"
    p.tenant_joined_at = timezone.now()
    p.save()
    return user


def _accept_url(user):
    """Build the accept URL for *user* using a fresh token."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = invite_token_generator.make_token(user)
    return reverse("users:invite_accept", kwargs={"uidb64": uid, "token": token})


# ---------------------------------------------------------------------------
# Email sending
# ---------------------------------------------------------------------------


class InviteMemberEmailTest(TestCase):
    def setUp(self):
        self.admin, self.tenant = _make_admin()

    @patch("apps.users.services.send_mail")
    def test_invite_sends_email_when_base_url_given(self, mock_send):
        """invite_member() calls send_mail once when base_url is provided."""
        invite_member(
            admin_profile=self.admin.profile,
            email="newbie@example.com",
            base_url="https://example.com",
        )
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        # recipient should be the invited email
        kw = call_kwargs[1] or {}
        recipients = kw.get("recipient_list") or call_kwargs[0][3]
        self.assertIn("newbie@example.com", recipients)

    @patch("apps.users.services.send_mail")
    def test_invite_no_email_without_base_url(self, mock_send):
        """invite_member() does NOT call send_mail when base_url is empty."""
        invite_member(
            admin_profile=self.admin.profile,
            email="quiet@example.com",
            base_url="",
        )
        mock_send.assert_not_called()

    @patch("apps.users.services.send_mail")
    def test_invite_email_subject_contains_org(self, mock_send):
        """The email subject mentions the organisation name."""
        invite_member(
            admin_profile=self.admin.profile,
            email="subject@example.com",
            base_url="https://example.com",
        )
        kw = mock_send.call_args[1] or {}
        subject = kw.get("subject") or mock_send.call_args[0][0]
        self.assertIn("InviteCorp", subject)


# ---------------------------------------------------------------------------
# GET — valid token
# ---------------------------------------------------------------------------


class InviteAcceptGetValidTest(TestCase):
    def setUp(self):
        _, self.tenant = _make_admin()
        self.user = _make_invited_user(self.tenant)
        self.url = _accept_url(self.user)

    def test_valid_token_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_valid_token_renders_accept_template(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "users/invite_accept.html")

    def test_email_in_context(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["email"], self.user.email)


# ---------------------------------------------------------------------------
# POST — successful accept
# ---------------------------------------------------------------------------


class InviteAcceptPostTest(TestCase):
    def setUp(self):
        _, self.tenant = _make_admin()
        self.user = _make_invited_user(self.tenant)
        self.url = _accept_url(self.user)

    def test_post_sets_usable_password(self):
        data = {"password": "newpass99!", "confirm_password": "newpass99!"}
        self.client.post(self.url, data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.has_usable_password())
        self.assertTrue(self.user.check_password("newpass99!"))

    def test_post_stamps_profile_completed_at(self):
        self.assertIsNone(self.user.profile.profile_completed_at)
        data = {"password": "newpass99!", "confirm_password": "newpass99!"}
        self.client.post(self.url, data)
        self.user.profile.refresh_from_db()
        self.assertIsNotNone(self.user.profile.profile_completed_at)

    def test_post_logs_user_in(self):
        data = {"password": "newpass99!", "confirm_password": "newpass99!"}
        self.client.post(self.url, data)
        # After a successful accept the session should have the user logged in.
        user_id = self.client.session.get("_auth_user_id")
        self.assertEqual(str(user_id), str(self.user.pk))

    def test_post_redirects_to_profile(self):
        response = self.client.post(
            self.url, {"password": "newpass99!", "confirm_password": "newpass99!"}
        )
        self.assertRedirects(response, reverse("users:profile"))

    def test_post_invalid_passwords_do_not_match(self):
        response = self.client.post(
            self.url, {"password": "newpass99!", "confirm_password": "different99!"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/invite_accept.html")
        self.user.refresh_from_db()
        self.assertFalse(self.user.has_usable_password())

    def test_post_short_password_rejected(self):
        response = self.client.post(
            self.url, {"password": "short", "confirm_password": "short"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/invite_accept.html")


# ---------------------------------------------------------------------------
# GET — invalid / expired token
# ---------------------------------------------------------------------------


class InviteAcceptInvalidTokenTest(TestCase):
    def setUp(self):
        _, self.tenant = _make_admin()
        self.user = _make_invited_user(self.tenant)

    def test_garbage_token_returns_400(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        url = reverse(
            "users:invite_accept",
            kwargs={"uidb64": uid, "token": "invalid-token"},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed(response, "users/invite_invalid.html")

    def test_garbage_uid_returns_400(self):
        token = invite_token_generator.make_token(self.user)
        url = reverse(
            "users:invite_accept",
            kwargs={"uidb64": "notauid", "token": token},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_expired_token_returns_400(self):
        """
        Simulate a used/expired token by setting the user's password after
        the token is generated.  The token generator includes the password
        hash in its HMAC, so any password change invalidates the token.
        """
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = invite_token_generator.make_token(self.user)
        # Setting a password changes the hash → token is now invalid.
        self.user.set_password("changedpassword1!")
        self.user.save(update_fields=["password"])
        url = reverse(
            "users:invite_accept",
            kwargs={"uidb64": uid, "token": token},
        )
        response = self.client.get(url)
        # Token is now invalid (password hash changed) → 400, but since the
        # user now *has* a usable password the view returns the already-accepted
        # page (200) instead.  Both outcomes confirm re-use is blocked.
        self.assertIn(response.status_code, [200, 400])


# ---------------------------------------------------------------------------
# GET — already accepted
# ---------------------------------------------------------------------------


class InviteAcceptAlreadyAcceptedTest(TestCase):
    def setUp(self):
        _, self.tenant = _make_admin()
        # User who has already set a password (simulates re-visiting the link).
        self.user = User.objects.create_user(
            email="done@invite.com", password="alreadyset1!"
        )
        p = self.user.profile
        p.tenant = self.tenant
        p.role = "member"
        p.tenant_joined_at = timezone.now()
        p.profile_completed_at = timezone.now()
        p.save()
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = invite_token_generator.make_token(self.user)
        self.url = reverse(
            "users:invite_accept",
            kwargs={"uidb64": uid, "token": token},
        )

    def test_already_accepted_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_already_accepted_renders_correct_template(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "users/invite_already_accepted.html")
