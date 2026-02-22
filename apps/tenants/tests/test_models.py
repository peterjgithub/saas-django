"""
Tests for apps.tenants.
"""

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.tenants.models import Tenant


class TenantModelTest(TestCase):
    def test_create_tenant(self) -> None:
        tenant = Tenant.objects.create(organization="Acme Corp")
        self.assertEqual(str(tenant), "Acme Corp")
        self.assertTrue(tenant.is_active)
        self.assertIsNotNone(tenant.id)

    def test_tenant_requires_organization(self) -> None:
        tenant = Tenant(organization="")
        with self.assertRaises(ValidationError):
            tenant.full_clean()

    def test_tenant_uuid_pk(self) -> None:
        import uuid

        tenant = Tenant.objects.create(organization="Beta Inc")
        self.assertIsInstance(tenant.id, uuid.UUID)

    def test_tenant_soft_delete_fields_exist(self) -> None:
        """TimeStampedAuditModel fields must be present."""
        tenant = Tenant.objects.create(organization="Gamma LLC")
        self.assertIsNone(tenant.deleted_at)
        self.assertIsNone(tenant.deleted_by)
        self.assertIsNotNone(tenant.created_at)
        self.assertIsNotNone(tenant.updated_at)

    def test_tenant_is_active_default_true(self) -> None:
        tenant = Tenant.objects.create(organization="Delta Ltd")
        self.assertTrue(tenant.is_active)
