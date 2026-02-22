"""
Phase 3 auth tests — login, register, logout, onboarding gate.
"""

from django.test import TestCase
from django.urls import reverse

from apps.tenants.models import Tenant
from apps.users.models import User


def _make_user(  # noqa: S107
    email="user@example.com",
    password="pass1234!",
    complete=False,
    tenant=None,
):
    """Helper: create a user and optionally complete their profile + attach tenant."""
    user = User.objects.create_user(email=email, password=password)
    profile = user.profile
    if complete:
        from django.utils import timezone as tz

        profile.profile_completed_at = tz.now()
    if tenant:
        profile.tenant = tenant
        profile.role = "admin"
        from django.utils import timezone as tz

        profile.tenant_joined_at = tz.now()
    profile.save()
    return user


def _make_complete_user(email="complete@example.com", password="pass1234!"):  # noqa: S107
    """Create a fully onboarded user (profile complete + tenant)."""
    tenant = Tenant.objects.create(organization="ACME")
    return _make_user(email=email, password=password, complete=True, tenant=tenant)


class LoginViewTest(TestCase):
    def setUp(self):
        self.url = reverse("users:login")
        self.user = User.objects.create_user(
            email="login@example.com", password="pass1234!"
        )

    def test_get_renders_login_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/login.html")

    def test_correct_credentials_redirect_to_dashboard(self):
        # Complete the user so middleware passes
        tenant = Tenant.objects.create(organization="T")
        from django.utils import timezone as tz

        p = self.user.profile
        p.profile_completed_at = tz.now()
        p.tenant = tenant
        p.role = "admin"
        p.tenant_joined_at = tz.now()
        p.save()
        response = self.client.post(
            self.url, {"email": "login@example.com", "password": "pass1234!"}
        )
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)

    def test_wrong_password_stays_on_login_form(self):
        response = self.client.post(
            self.url, {"email": "login@example.com", "password": "wrongpassword"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/login.html")
        self.assertContains(response, "Incorrect email or password")

    def test_wrong_password_no_redirect(self):
        """Login failure must NOT redirect — stays on form."""
        response = self.client.post(
            self.url, {"email": "login@example.com", "password": "bad"}
        )
        # 200 means no redirect happened
        self.assertEqual(response.status_code, 200)

    def test_cancel_link_points_to_homepage(self):
        response = self.client.get(self.url)
        self.assertContains(response, reverse("pages:home"))

    def test_next_param_redirects_after_login(self):
        tenant = Tenant.objects.create(organization="T2")
        from django.utils import timezone as tz

        p = self.user.profile
        p.profile_completed_at = tz.now()
        p.tenant = tenant
        p.role = "admin"
        p.tenant_joined_at = tz.now()
        p.save()
        response = self.client.post(
            self.url + "?next=/dashboard/",
            {
                "email": "login@example.com",
                "password": "pass1234!",
                "next": "/dashboard/",
            },  # noqa: E501
        )
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)


class RegisterViewTest(TestCase):
    def setUp(self):
        self.url = reverse("users:register")

    def test_get_renders_register_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/register.html")

    def test_registration_redirects_to_profile_complete(self):
        response = self.client.post(
            self.url, {"email": "new@example.com", "password": "StrongPass1!"}
        )
        self.assertRedirects(
            response,
            reverse("users:profile_complete"),
            fetch_redirect_response=False,
        )

    def test_registration_creates_user(self):
        self.client.post(
            self.url, {"email": "new2@example.com", "password": "StrongPass1!"}
        )
        self.assertTrue(User.objects.filter(email="new2@example.com").exists())

    def test_duplicate_email_shows_error(self):
        User.objects.create_user(email="dup@example.com", password="pass1234!")
        response = self.client.post(
            self.url, {"email": "dup@example.com", "password": "StrongPass1!"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")

    def test_tz_detect_hidden_field_present(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'name="tz_detect"')

    def test_lang_detect_hidden_field_present(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'name="lang_detect"')

    def test_authenticated_user_redirected(self):
        user = _make_complete_user(email="auth@example.com")
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)


class LogoutViewTest(TestCase):
    def setUp(self):
        self.url = reverse("users:logout")
        self.user = _make_complete_user()

    def test_post_logout_redirects_to_home(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertRedirects(
            response, reverse("pages:home"), fetch_redirect_response=False
        )

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)


class ProfileCompleteViewTest(TestCase):
    def setUp(self):
        self.url = reverse("users:profile_complete")
        self.user = User.objects.create_user(
            email="pc@example.com", password="pass1234!"
        )

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(
            response, "/login/?next=/profile/complete/", fetch_redirect_response=False
        )

    def test_renders_step1_template(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/onboarding_step1.html")

    def test_page_title_is_complete_your_profile(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "Complete your profile")

    def test_skip_sets_session_flag_and_redirects_to_step2(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"skip": "1"})
        self.assertRedirects(
            response,
            reverse("users:onboarding_create_tenant"),
            fetch_redirect_response=False,
        )
        self.assertTrue(self.client.session.get("skip_profile_gate"))

    def test_save_sets_profile_completed_at_and_redirects_to_step2(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"display_name": "Alice"})
        self.assertRedirects(
            response,
            reverse("users:onboarding_create_tenant"),
            fetch_redirect_response=False,
        )
        self.user.profile.refresh_from_db()
        self.assertIsNotNone(self.user.profile.profile_completed_at)

    def test_do_this_later_subsequent_requests_pass_gate(self):
        """After skip, next request should bypass Step 1 gate."""
        self.client.force_login(self.user)
        # Simulate skip
        session = self.client.session
        session["skip_profile_gate"] = True
        session.save()
        # Accessing profile_complete again should still work (not be in a redirect loop)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)


class OnboardingTenantViewTest(TestCase):
    def setUp(self):
        self.url = reverse("users:onboarding_create_tenant")
        self.user = User.objects.create_user(
            email="ot@example.com", password="pass1234!"
        )
        from django.utils import timezone as tz

        p = self.user.profile
        p.profile_completed_at = tz.now()
        p.save()

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(
            response,
            "/login/?next=/onboarding/create-tenant/",
            fetch_redirect_response=False,
        )

    def test_renders_step2_template(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/onboarding_step2.html")

    def test_page_title_is_create_your_workspace(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "Create your workspace")

    def test_save_creates_tenant_and_redirects_to_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"organization": "My Corp"})
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)
        self.user.profile.refresh_from_db()
        self.assertIsNotNone(self.user.profile.tenant_id)
        self.assertEqual(self.user.profile.role, "admin")

    def test_user_with_tenant_redirected_to_dashboard(self):
        tenant = Tenant.objects.create(organization="Existing")
        from django.utils import timezone as tz

        p = self.user.profile
        p.tenant = tenant
        p.role = "admin"
        p.tenant_joined_at = tz.now()
        p.save()
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)


class ProfileGateMiddlewareTest(TestCase):
    """Test ProfileCompleteMiddleware gate logic."""

    def test_incomplete_profile_no_skip_redirects_to_step1(self):
        user = User.objects.create_user(email="gate1@example.com", password="pass1234!")
        self.client.force_login(user)
        response = self.client.get("/dashboard/")
        self.assertRedirects(
            response,
            "/profile/complete/?next=/dashboard/",
            fetch_redirect_response=False,
        )

    def test_profile_complete_no_tenant_redirects_to_step2(self):
        from django.utils import timezone as tz

        user = User.objects.create_user(email="gate2@example.com", password="pass1234!")
        p = user.profile
        p.profile_completed_at = tz.now()
        p.save()
        self.client.force_login(user)
        response = self.client.get("/dashboard/")
        self.assertRedirects(
            response,
            "/onboarding/create-tenant/?next=/dashboard/",
            fetch_redirect_response=False,
        )

    def test_revoked_user_redirected_to_account_revoked(self):
        from django.utils import timezone as tz

        tenant = Tenant.objects.create(organization="R")
        user = User.objects.create_user(email="gate3@example.com", password="pass1234!")
        p = user.profile
        p.profile_completed_at = tz.now()
        p.tenant = tenant
        p.role = "member"
        p.tenant_joined_at = tz.now()
        p.is_active = False
        p.save()
        self.client.force_login(user)
        response = self.client.get("/dashboard/")
        self.assertRedirects(
            response, "/account/revoked/", fetch_redirect_response=False
        )

    def test_complete_user_passes_gate(self):
        user = _make_complete_user(email="gate4@example.com")
        self.client.force_login(user)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

    def test_logout_never_intercepted(self):
        user = User.objects.create_user(email="gate5@example.com", password="pass1234!")
        self.client.force_login(user)
        response = self.client.post(reverse("users:logout"))
        # Should redirect to home, not intercepted
        self.assertRedirects(
            response, reverse("pages:home"), fetch_redirect_response=False
        )

    def test_health_never_intercepted(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)


class ProfileViewTest(TestCase):
    def setUp(self):
        self.url = reverse("users:profile")
        self.user = _make_complete_user(email="pv@example.com")

    def test_renders_profile_template(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/profile.html")

    def test_save_updates_display_name_and_stays_on_page(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.url, {"display_name": "NewName", "theme": "system"}
        )
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.display_name, "NewName")

    def test_save_shows_success_message(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.url, {"display_name": "Updated", "theme": "system"}, follow=True
        )
        messages = list(response.context["messages"])
        self.assertTrue(any("updated" in str(m).lower() for m in messages))

    def test_marketing_opt_in_toggle(self):
        self.client.force_login(self.user)
        self.client.post(
            self.url,
            {"display_name": "X", "marketing_emails": "on", "theme": "system"},
        )
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.marketing_emails)

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(
            response, "/login/?next=/profile/", fetch_redirect_response=False
        )


class AccountRevokedViewTest(TestCase):
    def test_renders_revoked_template(self):
        response = self.client.get(reverse("users:account_revoked"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/account_revoked.html")


class SetThemeViewTest(TestCase):
    """
    Tests for POST /theme/set/ — theme persistence endpoint.

    - Authenticated users: theme saved to UserProfile.theme.
    - Unauthenticated users: 200 JSON ok returned (client stores in localStorage).
    - Invalid theme value → 400.
    - GET not allowed → 405.
    """

    url = "/theme/set/"

    def setUp(self):
        self.user = _make_complete_user(email="theme@example.com")

    # --- authenticated ---

    def test_authenticated_saves_corporate(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"theme": "corporate"})
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.theme, "corporate")

    def test_authenticated_saves_night(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"theme": "night"})
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.theme, "night")

    def test_authenticated_saves_system(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"theme": "system"})
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.theme, "system")

    def test_authenticated_returns_json_ok(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"theme": "night"})
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["theme"], "night")

    # --- unauthenticated ---

    def test_unauthenticated_returns_ok(self):
        """Unauthenticated POST returns 200 ok (client handles localStorage)."""
        response = self.client.post(self.url, {"theme": "night"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_unauthenticated_does_not_persist(self):
        """No DB write happens for unauthenticated requests."""
        self.client.post(self.url, {"theme": "night"})
        # Verify the user's profile was not changed (different session, no auth)
        self.user.profile.refresh_from_db()
        # Default theme is "system" — it should not have changed to "night"
        self.assertNotEqual(self.user.profile.theme, "night")

    # --- validation ---

    def test_invalid_theme_returns_400(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"theme": "rainbow"})
        self.assertEqual(response.status_code, 400)

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    # --- context processor ---

    def test_authenticated_context_uses_profile_theme(self):
        """current_theme in template context comes from profile, not cookie."""
        self.user.profile.theme = "night"
        self.user.profile.save(update_fields=["theme", "updated_at"])
        self.client.force_login(self.user)
        # Set a conflicting cookie to confirm profile wins
        self.client.cookies["theme"] = "corporate"
        response = self.client.get(reverse("pages:dashboard"))
        self.assertEqual(response.context["current_theme"], "night")

    def test_unauthenticated_context_uses_cookie(self):
        """Unauthenticated: current_theme falls back to cookie."""
        self.client.cookies["theme"] = "night"
        response = self.client.get(reverse("pages:home"))
        self.assertEqual(response.context["current_theme"], "night")

    def test_unauthenticated_no_cookie_defaults_to_system(self):
        response = self.client.get(reverse("pages:home"))
        self.assertEqual(response.context["current_theme"], "system")


# ---------------------------------------------------------------------------
# Language cookie sync tests
# ---------------------------------------------------------------------------


class LanguageCookieSyncTest(TestCase):
    """
    Language switching now goes through Django's built-in set_language view
    (same mechanism as the navbar/profile language buttons).

    The profile form no longer has a language field — saving other profile
    preferences must not clobber the active locale cookie.
    """

    LANG_COOKIE = "django_language"

    def setUp(self):
        from apps.tenants.models import Tenant

        tenant = Tenant.objects.create(organization="Test Corp")
        self.user = _make_user(
            email="langtest@example.com", complete=True, tenant=tenant
        )
        self.client.force_login(self.user)

    def test_set_language_nl_sets_cookie_nl_be(self):
        """POSTing nl-be to set_language sets django_language=nl-be."""
        response = self.client.post(
            reverse("set_language"),
            {"language": "nl-be", "next": reverse("users:profile")},
        )
        self.assertIn(response.status_code, [302, 200])
        self.assertEqual(response.cookies.get(self.LANG_COOKIE).value, "nl-be")

    def test_set_language_fr_sets_cookie_fr_be(self):
        """POSTing fr-be to set_language sets django_language=fr-be."""
        response = self.client.post(
            reverse("set_language"),
            {"language": "fr-be", "next": reverse("users:profile")},
        )
        self.assertIn(response.status_code, [302, 200])
        self.assertEqual(response.cookies.get(self.LANG_COOKIE).value, "fr-be")

    def test_profile_save_preserves_active_locale(self):
        """
        Saving the profile form (no language field) must not reset the locale.
        After switching to nl-be the profile save should keep the nl-be cookie.
        The cookie is held in the client session; the profile-save redirect does
        not need to re-set it (the language is controlled exclusively by set_language).
        """
        # First switch to Dutch via set_language.
        self.client.post(
            reverse("set_language"),
            {"language": "nl-be", "next": reverse("users:profile")},
        )
        # Verify the cookie is in the client session after set_language.
        self.assertEqual(self.client.cookies.get(self.LANG_COOKIE).value, "nl-be")
        # Now save the profile form — no language field.
        response = self.client.post(
            reverse("users:profile"),
            {"display_name": "Test", "theme": "system", "marketing_emails": ""},
        )
        self.assertEqual(response.status_code, 302)
        # Cookie must still be nl-be in the client session (not reset by profile save).
        self.assertEqual(self.client.cookies.get(self.LANG_COOKIE).value, "nl-be")

    def test_profile_save_nl_changes_ui_language(self):
        """After switching to Dutch the next page load is in Dutch."""
        # Switch language via set_language then follow the redirect.
        self.client.post(
            reverse("set_language"),
            {"language": "nl-be", "next": reverse("users:profile")},
        )
        # Load the profile page — it should now render in Dutch.
        response = self.client.get(reverse("users:profile"))
        # "Wijzigingen opslaan" = "Save changes" in Dutch.
        self.assertContains(response, "Wijzigingen opslaan")
