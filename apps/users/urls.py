"""URL patterns for the users app — Phase 3."""

from django.urls import path

from apps.users import views

app_name = "users"

urlpatterns = [
    # Auth
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    # Onboarding
    path("profile/complete/", views.profile_complete_view, name="profile_complete"),
    path(
        "onboarding/create-tenant/",
        views.onboarding_tenant_view,
        name="onboarding_create_tenant",
    ),
    # Profile
    path("profile/", views.profile_view, name="profile"),
    # Theme preference (AJAX POST — authenticated saves to DB, unauth is no-op)
    path("theme/set/", views.set_theme_view, name="set_theme"),
    # Account revoked
    path("account/revoked/", views.account_revoked_view, name="account_revoked"),
    # Member management (admin only)
    path("settings/members/", views.members_view, name="members"),
    path("settings/members/invite/", views.invite_member_view, name="invite_member"),
    path(
        "settings/members/revoke/<uuid:profile_id>/",
        views.revoke_member_view,
        name="revoke_member",
    ),
    path(
        "settings/members/reengage/<uuid:profile_id>/",
        views.reengage_member_view,
        name="reengage_member",
    ),
]
