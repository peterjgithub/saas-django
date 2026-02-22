"""
URL stubs for the users app.

Full auth views (login, register, profile, logout) are implemented in Phase 3.
These stubs exist so that base.html {% url %} tags resolve correctly during
Phase 2 development and testing.
"""

from django.urls import path
from django.views.generic import RedirectView

app_name = "users"

urlpatterns = [
    # Phase 3 will replace these with real views.
    path("login/", RedirectView.as_view(url="/", permanent=False), name="login"),
    path("logout/", RedirectView.as_view(url="/", permanent=False), name="logout"),
    path("profile/", RedirectView.as_view(url="/", permanent=False), name="profile"),
]
