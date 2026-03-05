from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models.users import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically creates a UserProfile when a new User is created.
    Uses get_or_create to avoid conflicts with Admin's inline saving.
    """
    if created:
        UserProfile.objects.get_or_create(user=instance)