from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    """
    Extends Django's built-in User with optional profile fields.
    Created automatically when a User is created via a post_save signal.
    Never replaces User — always extends it.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    organization = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=100, blank=True)
    orcid_id = models.CharField(
        max_length=50,
        blank=True,
        help_text='e.g. 0000-0002-1825-0097'
    )
    bio = models.TextField(blank=True)

    def __str__(self):
        return f'Profile: {self.user.get_full_name() or self.user.username}'