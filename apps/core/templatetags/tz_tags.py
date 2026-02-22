"""
Timezone template filters.

Usage:
    {% load tz_tags %}
    {{ some_utc_datetime|localtime:request.user.profile.timezone }}
    {{ some_utc_datetime|localtime:timezone_obj }}
"""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django import template
from django.utils import timezone as django_timezone

register = template.Library()


@register.filter
def localtime(value, tz):
    """
    Convert *value* (a timezone-aware datetime) to the timezone identified
    by *tz*.

    *tz* may be:
    - A ``core.Timezone`` model instance (has a ``name`` attribute)
    - A plain IANA timezone string, e.g. ``"Europe/Brussels"``
    - ``None`` / falsy — returns *value* unchanged (UTC)
    """
    if not value:
        return value

    # Resolve tz argument to a ZoneInfo instance
    tz_name = None
    if hasattr(tz, "name"):
        # core.Timezone model instance
        tz_name = tz.name
    elif isinstance(tz, str):
        tz_name = tz

    if not tz_name:
        return value

    try:
        zone = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError, KeyError:
        return value

    # Ensure value is aware before converting
    if django_timezone.is_naive(value):
        value = django_timezone.make_aware(value, ZoneInfo("UTC"))

    return value.astimezone(zone)


@register.filter
def flag_emoji(country_code: str) -> str:
    """
    Convert an ISO 3166-1 alpha-2 country code to a flag emoji.

    Each letter is mapped to the corresponding Regional Indicator Symbol
    (U+1F1E6–U+1F1FF).  Unknown or empty codes return an empty string.

    Usage:
        {{ country.code|flag_emoji }}
    """
    if not country_code or len(country_code) != 2:
        return ""
    try:
        return "".join(chr(0x1F1E6 + ord(c.upper()) - ord("A")) for c in country_code)
    except TypeError, ValueError:
        return ""
