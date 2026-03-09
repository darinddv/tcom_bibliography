from django.contrib.auth.models import User
from django.db import models


class DeletionRequest(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    publication = models.ForeignKey(
        'Publication',
        on_delete=models.CASCADE,
        related_name='deletion_requests',
    )
    requested_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='deletion_requests',
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(
        help_text='Required. Explain why this publication should be deleted.'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
    )
    resolved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='resolved_deletion_requests',
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(
        blank=True,
        help_text='Optional note from the editor explaining the decision.'
    )

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f'Deletion request for {self.publication} by {self.requested_by} [{self.get_status_display()}]'