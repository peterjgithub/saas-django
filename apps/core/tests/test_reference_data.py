"""
Tests for apps.core reference data models and management command.

The LoadReferenceDataCommandTest and ReferenceDataRelationshipTest classes are
tagged "slow" because they invoke the full load_reference_data command (7 000+
languages via pycountry).  They are skipped in the pre-commit hook
(--exclude-tag=slow) but always run in CI and on-demand test runs.
"""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase, tag

from apps.core.models import Country, Currency, Language, Timezone


@tag("slow")
class LoadReferenceDataCommandTest(TestCase):
    """The load_reference_data management command populates all four tables."""

    def test_command_creates_countries(self) -> None:
        call_command("load_reference_data", stdout=StringIO())
        self.assertGreater(Country.objects.count(), 200)

    def test_command_creates_languages(self) -> None:
        call_command("load_reference_data", stdout=StringIO())
        self.assertGreater(Language.objects.count(), 100)

    def test_command_creates_timezones(self) -> None:
        call_command("load_reference_data", stdout=StringIO())
        self.assertGreater(Timezone.objects.count(), 400)

    def test_command_creates_currencies(self) -> None:
        call_command("load_reference_data", stdout=StringIO())
        self.assertGreater(Currency.objects.count(), 100)

    def test_command_is_idempotent(self) -> None:
        """Running twice must not raise or create duplicates."""
        stdout = StringIO()
        call_command("load_reference_data", stdout=stdout)
        first_count = Country.objects.count()
        call_command("load_reference_data", stdout=StringIO())
        self.assertEqual(Country.objects.count(), first_count)


@tag("slow")
class ReferenceDataRelationshipTest(TestCase):
    """FK filtering works (e.g. languages spoken in Belgium)."""

    @classmethod
    def setUpTestData(cls) -> None:
        call_command("load_reference_data", stdout=StringIO())

    def test_belgium_has_languages(self) -> None:
        belgium = Country.objects.get(code="BE")
        langs = Language.objects.filter(countries=belgium)
        # Belgium has at least Dutch (nl), French (fr), German (de)
        lang_codes = set(langs.values_list("code", flat=True))
        self.assertTrue(
            lang_codes.intersection({"nl", "fr", "de"}),
            f"Expected Belgian languages in {lang_codes}",
        )

    def test_belgium_has_timezones(self) -> None:
        belgium = Country.objects.get(code="BE")
        tzs = Timezone.objects.filter(countries=belgium)
        tz_names = list(tzs.values_list("name", flat=True))
        self.assertIn("Europe/Brussels", tz_names)

    def test_belgium_has_currency(self) -> None:
        belgium = Country.objects.get(code="BE")
        currencies = Currency.objects.filter(countries=belgium)
        codes = list(currencies.values_list("code", flat=True))
        self.assertIn("EUR", codes)

    def test_country_str(self) -> None:
        belgium = Country.objects.get(code="BE")
        self.assertEqual(str(belgium), belgium.name)

    def test_currency_str(self) -> None:
        eur = Currency.objects.get(code="EUR")
        self.assertIn("EUR", str(eur))

    def test_timezone_str(self) -> None:
        bxl = Timezone.objects.get(name="Europe/Brussels")
        self.assertIn("Europe/Brussels", str(bxl))
