"""
Production settings.

Inherits from base and enforces security hardening.
All secrets MUST be provided via environment variables.
"""

from .base import *  # noqa: F401, F403
from .base import env

DEBUG = False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")

# ---------------------------------------------------------------------------
# Security hardening
# ---------------------------------------------------------------------------

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

X_FRAME_OPTIONS = "DENY"
