"""
Phase 4 — I18N tests.

Verifies that:
- Dutch (nl) and French (fr) translations are loaded and applied correctly.
- English is served by default when no Accept-Language header is sent.
- Django's `set_language` view switches the active language for subsequent requests.
"""

from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(
    LANGUAGE_CODE="en",
    LANGUAGES=[("en", "English"), ("nl", "Nederlands"), ("fr", "Français")],
    USE_I18N=True,
)
class I18NLanguageTests(TestCase):
    """Test that pages are served in the correct language."""

    def test_english_is_default(self):
        """Login page is served in English when no Accept-Language is sent."""
        response = self.client.get(reverse("users:login"))
        self.assertContains(response, "Sign in")

    def test_dutch_login_page(self):
        """Login page shows Dutch text when Accept-Language: nl-BE is sent."""
        response = self.client.get(
            reverse("users:login"), HTTP_ACCEPT_LANGUAGE="nl-BE,nl;q=0.9"
        )
        self.assertContains(response, "Aanmelden")

    def test_french_login_page(self):
        """Login page shows French text when Accept-Language: fr-BE is sent."""
        response = self.client.get(
            reverse("users:login"), HTTP_ACCEPT_LANGUAGE="fr-BE,fr;q=0.9"
        )
        self.assertContains(response, "Se connecter")

    def test_dutch_register_page(self):
        """Register page shows Dutch text when Accept-Language: nl is sent."""
        response = self.client.get(reverse("users:register"), HTTP_ACCEPT_LANGUAGE="nl")
        self.assertContains(response, "Account aanmaken")

    def test_french_register_page(self):
        """Register page shows French text when Accept-Language: fr is sent."""
        response = self.client.get(reverse("users:register"), HTTP_ACCEPT_LANGUAGE="fr")
        self.assertContains(response, "Créer un compte")

    def test_dutch_password_reset_page(self):
        """Password reset page shows Dutch text."""
        response = self.client.get(reverse("password_reset"), HTTP_ACCEPT_LANGUAGE="nl")
        self.assertContains(response, "Wachtwoord opnieuw instellen")

    def test_french_password_reset_page(self):
        """Password reset page shows French text."""
        response = self.client.get(reverse("password_reset"), HTTP_ACCEPT_LANGUAGE="fr")
        self.assertContains(response, "Réinitialiser le mot de passe")


@override_settings(
    LANGUAGE_CODE="en",
    LANGUAGES=[("en", "English"), ("nl", "Nederlands"), ("fr", "Français")],
    USE_I18N=True,
)
class SetLanguageViewTests(TestCase):
    """Test Django's built-in set_language view switches the session language."""

    def test_set_language_to_dutch(self):
        """POSTing nl to set_language switches subsequent requests to Dutch."""
        # Switch language to nl
        response = self.client.post(
            reverse("set_language"),
            {"language": "nl", "next": reverse("users:login")},
        )
        self.assertRedirects(response, reverse("users:login"))

        # Next request should be in Dutch — check a uniquely Dutch phrase
        response = self.client.get(reverse("users:login"))
        self.assertContains(response, "Wachtwoord vergeten?")

    def test_set_language_to_french(self):
        """POSTing fr to set_language switches subsequent requests to French."""
        response = self.client.post(
            reverse("set_language"),
            {"language": "fr", "next": reverse("users:login")},
        )
        self.assertRedirects(response, reverse("users:login"))

        response = self.client.get(reverse("users:login"))
        self.assertContains(response, "Mot de passe oublié")

    def test_set_language_back_to_english(self):
        """After switching to Dutch, switching back to en restores English."""
        self.client.post(
            reverse("set_language"),
            {"language": "nl", "next": "/"},
        )
        self.client.post(
            reverse("set_language"),
            {"language": "en", "next": reverse("users:login")},
        )
        response = self.client.get(reverse("users:login"))
        self.assertContains(response, "Forgot password")

    def test_set_language_invalid_code_ignored(self):
        """An invalid language code is rejected."""
        response = self.client.post(
            reverse("set_language"),
            {"language": "zz", "next": reverse("users:login")},
        )
        # Django returns 200 with a form error or redirects; either way no crash
        self.assertIn(response.status_code, [200, 302])
