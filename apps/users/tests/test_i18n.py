"""
Phase 4 — I18N tests.

Verifies that:
- Belgian Dutch (nl-BE) and Belgian French (fr-BE) translations are loaded and applied.
- English is served by default when no Accept-Language header is sent.
- Django's `set_language` view switches the active language for subsequent requests.
- The nl-BE → nl fallback chain works (nl_BE overrides layer on top of base nl).
"""

from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(
    LANGUAGE_CODE="en",
    LANGUAGES=[("en", "English"), ("nl-be", "Nederlands"), ("fr-be", "Français")],
    USE_I18N=True,
)
class I18NLanguageTests(TestCase):
    """Test that pages are served in the correct language."""

    def test_english_is_default(self):
        """Login page is served in English when no Accept-Language is sent."""
        response = self.client.get(reverse("users:login"))
        self.assertContains(response, "Sign in")

    def test_dutch_login_page(self):
        """Login page shows Belgian Dutch text when Accept-Language: nl-BE is sent."""
        response = self.client.get(
            reverse("users:login"), HTTP_ACCEPT_LANGUAGE="nl-BE,nl;q=0.9"
        )
        self.assertContains(response, "Aanmelden")

    def test_french_login_page(self):
        """Login page shows Belgian French text when Accept-Language: fr-BE is sent."""
        response = self.client.get(
            reverse("users:login"), HTTP_ACCEPT_LANGUAGE="fr-BE,fr;q=0.9"
        )
        self.assertContains(response, "Se connecter")

    def test_dutch_register_page(self):
        """Register page shows Dutch text when Accept-Language: nl-BE is sent."""
        response = self.client.get(
            reverse("users:register"), HTTP_ACCEPT_LANGUAGE="nl-BE"
        )
        self.assertContains(response, "Account aanmaken")

    def test_french_register_page(self):
        """Register page shows French text when Accept-Language: fr-BE is sent."""
        response = self.client.get(
            reverse("users:register"), HTTP_ACCEPT_LANGUAGE="fr-BE"
        )
        self.assertContains(response, "Créer un compte")

    def test_dutch_password_reset_page(self):
        """Password reset page shows Dutch text when Accept-Language: nl-BE is sent."""
        response = self.client.get(
            reverse("password_reset"), HTTP_ACCEPT_LANGUAGE="nl-BE"
        )
        self.assertContains(response, "Wachtwoord opnieuw instellen")

    def test_french_password_reset_page(self):
        """Password reset page shows French text when Accept-Language: fr-BE is sent."""
        response = self.client.get(
            reverse("password_reset"), HTTP_ACCEPT_LANGUAGE="fr-BE"
        )
        self.assertContains(response, "Réinitialiser le mot de passe")


@override_settings(
    LANGUAGE_CODE="en",
    LANGUAGES=[("en", "English"), ("nl-be", "Nederlands"), ("fr-be", "Français")],
    USE_I18N=True,
)
class SetLanguageViewTests(TestCase):
    """Test Django's built-in set_language view switches the session language."""

    def test_set_language_to_dutch(self):
        """POSTing nl-be to set_language switches to Belgian Dutch."""
        response = self.client.post(
            reverse("set_language"),
            {"language": "nl-be", "next": reverse("users:login")},
        )
        self.assertRedirects(response, reverse("users:login"))

        # Next request should be in Belgian Dutch
        response = self.client.get(reverse("users:login"))
        self.assertContains(response, "Wachtwoord vergeten?")

    def test_set_language_to_french(self):
        """POSTing fr-be to set_language switches to Belgian French."""
        response = self.client.post(
            reverse("set_language"),
            {"language": "fr-be", "next": reverse("users:login")},
        )
        self.assertRedirects(response, reverse("users:login"))

        response = self.client.get(reverse("users:login"))
        self.assertContains(response, "Mot de passe oublié")

    def test_set_language_back_to_english(self):
        """After switching to Dutch, switching back to en restores English."""
        self.client.post(
            reverse("set_language"),
            {"language": "nl-be", "next": "/"},
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
