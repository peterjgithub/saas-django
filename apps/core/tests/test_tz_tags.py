"""
Tests for apps/core/templatetags/tz_tags.py
"""

from datetime import datetime
from datetime import timezone as dt_timezone

from django.test import TestCase

from apps.core.templatetags.tz_tags import localtime


class LocaltimeFilterTests(TestCase):
    def _utc(self, **kwargs):
        """Return a UTC-aware datetime."""
        return datetime(2024, 6, 15, 12, 0, 0, tzinfo=dt_timezone.utc)

    def test_converts_with_iana_string(self):
        """Filter accepts a plain IANA timezone string."""
        utc_dt = self._utc()
        result = localtime(utc_dt, "Europe/Brussels")
        # UTC+2 in summer → 14:00
        self.assertEqual(result.hour, 14)

    def test_converts_with_timezone_model_instance(self):
        """Filter accepts a core.Timezone model instance (has .name attribute)."""

        class FakeTZ:
            name = "America/New_York"

        utc_dt = self._utc()
        result = localtime(utc_dt, FakeTZ())
        # UTC-4 in summer → 08:00
        self.assertEqual(result.hour, 8)

    def test_returns_unchanged_when_tz_is_none(self):
        utc_dt = self._utc()
        result = localtime(utc_dt, None)
        self.assertEqual(result, utc_dt)

    def test_returns_unchanged_when_value_is_none(self):
        result = localtime(None, "Europe/Brussels")
        self.assertIsNone(result)

    def test_returns_unchanged_for_unknown_timezone(self):
        utc_dt = self._utc()
        result = localtime(utc_dt, "Invalid/Zone")
        self.assertEqual(result, utc_dt)
