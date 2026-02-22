"""
Tests for apps.users — User model, UserProfile auto-creation, and helpers.
"""

import uuid

from django.test import TestCase

from apps.users.models import User, UserProfile, derive_display_name


class UserManagerTest(TestCase):
    def test_create_user_with_email(self) -> None:
        user = User.objects.create_user(email="alice@example.com", password="pass1234!")
        self.assertEqual(user.email, "alice@example.com")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_requires_email(self) -> None:
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="pass1234!")

    def test_create_superuser(self) -> None:
        user = User.objects.create_superuser(
            email="admin@example.com", password="admin1234!"
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_email_is_unique(self) -> None:
        from django.db import IntegrityError

        User.objects.create_user(email="dup@example.com", password="pass1234!")
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email="dup@example.com", password="other1234!")

    def test_user_uuid_pk(self) -> None:
        user = User.objects.create_user(email="uuid@example.com", password="pass1234!")
        self.assertIsInstance(user.pk, uuid.UUID)

    def test_user_soft_delete_fields_exist(self) -> None:
        user = User.objects.create_user(email="soft@example.com", password="pass1234!")
        self.assertIsNone(user.deleted_at)
        self.assertIsNone(user.deleted_by)

    def test_user_has_no_username_field(self) -> None:
        """username must not be a model field (it is set to None on the class)."""
        user = User.objects.create_user(
            email="nouser@example.com", password="pass1234!"
        )
        field_names = [f.name for f in user._meta.get_fields()]
        self.assertNotIn("username", field_names)

    def test_user_str(self) -> None:
        user = User.objects.create_user(email="str@example.com", password="pass1234!")
        self.assertEqual(str(user), "str@example.com")


class UserProfileSignalTest(TestCase):
    def test_profile_auto_created_on_user_creation(self) -> None:
        user = User.objects.create_user(
            email="newuser@example.com", password="pass1234!"
        )
        self.assertTrue(hasattr(user, "profile"))
        self.assertIsInstance(user.profile, UserProfile)

    def test_profile_completed_at_is_none_on_creation(self) -> None:
        user = User.objects.create_user(
            email="incomplete@example.com", password="pass1234!"
        )
        self.assertIsNone(user.profile.profile_completed_at)

    def test_signal_is_idempotent(self) -> None:
        """Calling save() again on an existing user must not create a second profile."""
        user = User.objects.create_user(email="idem@example.com", password="pass1234!")
        profile_pk = user.profile.pk
        user.save()  # triggers post_save again
        user.refresh_from_db()
        self.assertEqual(user.profile.pk, profile_pk)
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)

    def test_profile_tenant_is_none_on_creation(self) -> None:
        user = User.objects.create_user(
            email="notable@example.com", password="pass1234!"
        )
        self.assertIsNone(user.profile.tenant)

    def test_profile_role_default_is_member(self) -> None:
        user = User.objects.create_user(
            email="member@example.com", password="pass1234!"
        )
        self.assertEqual(user.profile.role, "member")


class DeriveDisplayNameTest(TestCase):
    def test_dotted_email(self) -> None:
        self.assertEqual(derive_display_name("peter.janssens@acme.com"), "Peter")

    def test_plain_email(self) -> None:
        self.assertEqual(derive_display_name("alice@example.com"), "Alice")

    def test_multiple_dots(self) -> None:
        self.assertEqual(derive_display_name("jean.pierre.dupont@mail.com"), "Jean")

    def test_capitalises_result(self) -> None:
        self.assertEqual(derive_display_name("bob@example.com"), "Bob")

    def test_display_name_derived_from_email_on_profile_creation(self) -> None:
        user = User.objects.create_user(
            email="peter.janssens@acme.com", password="pass1234!"
        )
        self.assertEqual(user.profile.display_name, "Peter")
