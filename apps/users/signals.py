"""
User post_save signal.

Auto-creates a UserProfile whenever a new User is saved for the first time.
The display_name is derived from the email local-part.
"""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile, derive_display_name


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created: bool, **kwargs) -> None:
    """Create a UserProfile for every new User. Idempotent via get_or_create."""
    if created:
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={"display_name": derive_display_name(instance.email)},
        )
