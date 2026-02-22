"""
Phase 2 tests for the pages app.

Covers:
- Health check endpoint (200, JSON body, db ok)
- Homepage (200, uses base.html, skip-link present)
- Context processor injects SITE_NAME and current_theme
- Dashboard redirects unauthenticated users to login
- Dashboard is accessible when authenticated
"""

import json

from django.test import TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):
    def test_health_returns_200(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)

    def test_health_content_type_is_json(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response["Content-Type"], "application/json")

    def test_health_body_status_ok(self):
        response = self.client.get(reverse("health"))
        data = json.loads(response.content)
        self.assertEqual(data["status"], "ok")

    def test_health_body_db_ok(self):
        response = self.client.get(reverse("health"))
        data = json.loads(response.content)
        self.assertEqual(data["db"], "ok")


class HomepageTests(TestCase):
    def test_homepage_returns_200(self):
        response = self.client.get(reverse("pages:home"))
        self.assertEqual(response.status_code, 200)

    def test_homepage_uses_base_template(self):
        response = self.client.get(reverse("pages:home"))
        self.assertTemplateUsed(response, "base.html")
        self.assertTemplateUsed(response, "pages/home.html")

    def test_homepage_has_skip_link(self):
        """Skip-to-content must be the first focusable element (WCAG AA)."""
        response = self.client.get(reverse("pages:home"))
        # The skip link href must target #main-content
        self.assertContains(response, 'href="#main-content"')

    def test_homepage_main_id_present(self):
        """<main id="main-content"> must exist for the skip link target."""
        response = self.client.get(reverse("pages:home"))
        self.assertContains(response, 'id="main-content"')

    def test_homepage_html_lang_attribute_present(self):
        """<html lang="..."> must be dynamic, not hardcoded."""
        response = self.client.get(reverse("pages:home"))
        self.assertContains(response, "<html lang=")


class ContextProcessorTests(TestCase):
    def test_site_name_injected(self):
        response = self.client.get(reverse("pages:home"))
        self.assertIn("SITE_NAME", response.context)

    def test_current_theme_injected(self):
        response = self.client.get(reverse("pages:home"))
        self.assertIn("current_theme", response.context)

    def test_current_theme_default_is_system(self):
        """Unauthenticated request with no cookie → theme is 'system'."""
        response = self.client.get(reverse("pages:home"))
        self.assertEqual(response.context["current_theme"], "system")

    def test_current_theme_from_cookie(self):
        """A 'theme' cookie value is picked up for unauthenticated requests."""
        self.client.cookies["theme"] = "night"
        response = self.client.get(reverse("pages:home"))
        self.assertEqual(response.context["current_theme"], "night")


class DashboardTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from django.utils import timezone as tz

        from apps.tenants.models import Tenant

        User = get_user_model()
        self.user = User.objects.create_user(  # noqa: S106
            email="dash@example.com",
            password="testpass123",
        )
        # Complete onboarding so ProfileCompleteMiddleware passes through
        tenant = Tenant.objects.create(organization="Dash Corp")
        p = self.user.profile
        p.profile_completed_at = tz.now()
        p.tenant = tenant
        p.role = "admin"
        p.tenant_joined_at = tz.now()
        p.save()

    def test_dashboard_redirects_anonymous(self):
        response = self.client.get(reverse("pages:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_dashboard_accessible_when_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("pages:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/dashboard.html")
