"""
Development settings.

Inherits everything from base and enables debug-friendly defaults.
Never use in production.
"""

from .base import *  # noqa: F401, F403
from .base import env

DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Allow all origins in development for convenience
INTERNAL_IPS = ["127.0.0.1"]
