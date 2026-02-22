from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedAuditModel


class Tenant(TimeStampedAuditModel):
    """
    Workspace / organisation.

    Tenant IS the root object — it has no tenant_id on itself.
    Extends TimeStampedAuditModel (Category B) for full audit trail.
    """

    organization = models.CharField(
        max_length=200,
        verbose_name=_("organisation name"),
        help_text=_("Company or workspace name."),
    )

    class Meta:
        verbose_name = _("tenant")
        verbose_name_plural = _("tenants")
        ordering = ["organization"]

    def __str__(self) -> str:
        return self.organization
