from django.contrib import admin

from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("organization", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("organization",)
    readonly_fields = ("id", "created_at", "updated_at")
