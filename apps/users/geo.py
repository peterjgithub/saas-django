"""
IP-based geolocation helper.

Uses ip-api.com (free tier, no API key required) to resolve the best-guess
timezone, country, and language for a visitor's IP address.

Returns a plain dict — never raises; falls back to empty strings on any error
so callers can always safely do ``result.get("timezone", "")``.

The function is deliberately synchronous (no async/Celery) — it is only called
once during onboarding and the timeout is kept very short (1 s).
"""

import json
import logging
from urllib.error import URLError
from urllib.request import urlopen

logger = logging.getLogger(__name__)

# Mapping from ISO 3166-1 alpha-2 country code to the most common BCP-47
# language tag used there.  This is a best-effort fallback; the actual
# language tables are stored in core.Language and linked via M2M.
_COUNTRY_LANG: dict[str, str] = {
    "BE": "nl-BE",
    "NL": "nl",
    "FR": "fr",
    "DE": "de",
    "GB": "en-GB",
    "US": "en-US",
    "CA": "en-CA",
    "AU": "en-AU",
    "NZ": "en-NZ",
    "ZA": "en-ZA",
    "IN": "en-IN",
    "SG": "en-SG",
    "ES": "es",
    "MX": "es-MX",
    "AR": "es-AR",
    "CO": "es-CO",
    "PT": "pt",
    "BR": "pt-BR",
    "IT": "it",
    "PL": "pl",
    "RU": "ru",
    "CN": "zh-CN",
    "TW": "zh-TW",
    "JP": "ja",
    "KR": "ko",
    "SE": "sv",
    "NO": "nb",
    "DK": "da",
    "FI": "fi",
    "CZ": "cs",
    "SK": "sk",
    "HU": "hu",
    "RO": "ro",
    "TR": "tr",
    "IL": "he",
    "SA": "ar",
    "AE": "ar",
    "EG": "ar",
    "TH": "th",
    "VN": "vi",
    "ID": "id",
    "MY": "ms",
    "PH": "fil",
    "UA": "uk",
    "HR": "hr",
    "RS": "sr",
    "BG": "bg",
    "GR": "el",
}

_API_URL = "http://ip-api.com/json/{ip}?fields=status,countryCode,timezone,lang"
_TIMEOUT = 1  # seconds — never block a page render


def lookup_from_ip(ip: str) -> dict:
    """
    Query ip-api.com for the given IP address.

    Returns a dict with zero or more of these keys (all strings):
        timezone   — IANA tz name, e.g. "Europe/Brussels"
        country    — ISO 3166-1 alpha-2, e.g. "BE"
        language   — BCP-47 tag, e.g. "nl-BE"

    Returns an empty dict on any error (timeout, private IP, API failure, etc.).
    Private / loopback IPs ("127.*", "::1", "10.*", "192.168.*") are silently
    skipped to avoid wasting time during local development.
    """
    if not ip or _is_private(ip):
        return {}

    try:
        url = _API_URL.format(ip=ip)
        with urlopen(url, timeout=_TIMEOUT) as resp:  # noqa: S310
            data = json.loads(resp.read())
    except (URLError, OSError, ValueError) as exc:
        logger.debug("ip-api lookup failed for %s: %s", ip, exc)
        return {}

    if data.get("status") != "success":
        return {}

    result: dict[str, str] = {}

    if tz := data.get("timezone", ""):
        result["timezone"] = tz

    if cc := data.get("countryCode", ""):
        result["country"] = cc
        if lang := _COUNTRY_LANG.get(cc):
            result["language"] = lang

    return result


def _is_private(ip: str) -> bool:
    """Return True for loopback / RFC-1918 / link-local addresses."""
    return (
        ip.startswith("127.")
        or ip == "::1"
        or ip.startswith("10.")
        or ip.startswith("192.168.")
        or ip.startswith("172.16.")
        or ip.startswith("172.17.")
        or ip.startswith("172.18.")
        or ip.startswith("172.19.")
        or ip.startswith("172.2")
        or ip.startswith("172.30.")
        or ip.startswith("172.31.")
        or ip == "localhost"
    )


def get_client_ip(request) -> str:
    """Extract the real client IP from the request (respects X-Forwarded-For)."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
