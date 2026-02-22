"""
Core models.

Abstract base classes (Categories A and B) and reference / lookup tables
(Category C: Country, Language, Timezone, Currency).
"""

import uuid

from django.db import models

# ---------------------------------------------------------------------------
# Category B — TimeStampedAuditModel
# Use for system-level records with no workspace scope (UserProfile, Tenant, …)
# ---------------------------------------------------------------------------


class TimeStampedAuditModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField(null=True, blank=True)  # acting user UUID — no FK
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.UUIDField(null=True, blank=True)  # acting user UUID — no FK
    is_active = models.BooleanField(default=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.UUIDField(null=True, blank=True)  # acting user UUID — no FK

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Category A — TenantScopedModel
# Use for all tenant-scoped business data (invoices, documents, tasks, …)
# ---------------------------------------------------------------------------


class TenantScopedModel(TimeStampedAuditModel):
    tenant_id = models.UUIDField(db_index=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Category C — Reference / lookup tables (plain models.Model, no soft-delete)
# Loaded once from pycountry / zoneinfo via the load_reference_data command.
# ---------------------------------------------------------------------------


class Country(models.Model):
    """ISO 3166-1 country."""

    code = models.CharField(max_length=2, unique=True)  # alpha-2
    code3 = models.CharField(max_length=3, unique=True)  # alpha-3
    name = models.CharField(max_length=200)
    numeric = models.CharField(max_length=3, blank=True)

    class Meta:
        verbose_name_plural = "countries"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Language(models.Model):
    """ISO 639-1/-3 language."""

    code = models.CharField(max_length=8, unique=True)  # BCP-47 / alpha-2 or alpha-3
    name = models.CharField(max_length=200)
    countries = models.ManyToManyField(
        Country,
        blank=True,
        related_name="languages",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Timezone(models.Model):
    """IANA timezone."""

    name = models.CharField(max_length=100, unique=True)  # e.g. "Europe/Brussels"
    label = models.CharField(max_length=200)  # e.g. "Europe/Brussels (UTC+01:00)"
    offset_seconds = models.IntegerField(default=0)  # raw UTC offset for sorting
    countries = models.ManyToManyField(
        Country,
        blank=True,
        related_name="timezones",
    )

    class Meta:
        ordering = ["offset_seconds", "name"]

    def __str__(self) -> str:
        return self.label


class Currency(models.Model):
    """ISO 4217 currency."""

    code = models.CharField(max_length=3, unique=True)  # e.g. "EUR"
    name = models.CharField(max_length=200)
    numeric = models.CharField(max_length=3, blank=True)
    countries = models.ManyToManyField(
        Country,
        blank=True,
        related_name="currencies",
    )

    class Meta:
        verbose_name_plural = "currencies"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"
