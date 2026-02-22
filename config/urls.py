"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path

from apps.pages.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("", include("apps.pages.urls")),
    path("", include("apps.users.urls")),
]
