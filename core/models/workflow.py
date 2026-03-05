from django.contrib.auth.models import User
from django.db import models


WORKFLOW_STATES = [
    ('unassigned', 'Unassigned'),
    ('assigned', 'Assigned'),
    ('in_progress', 'In Progress'),
    ('pending_review', 'Pending Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('archived', 'Archived'),
    ('flagged', 'Flagged'),
]


class WorkflowTransition(models.Model):
    """
    Immutable audit log of every state change for a publication.
    Never update these rows — only ever insert new ones.
    Current state is always the to_state of the most recent transition.
    """
    publication = models.ForeignKey(
        'Publication',
        on_delete=models.CASCADE,
        related_name='transitions',
    )
    from_state = models.CharField(
        max_length=50,
        choices=WORKFLOW_STATES,
        blank=True,
        help_text='Empty string on the initial transition.'
    )
    to_state = models.CharField(
        max_length=50,
        choices=WORKFLOW_STATES,
    )
    actor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='transitions_made',
        help_text='Null if system-initiated, e.g. on import.'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(
        blank=True,
        help_text='Required when rejecting. Optional otherwise.'
    )
    is_system_action = models.BooleanField(
        default=False,
        help_text='True if triggered automatically, e.g. on DOI import.'
    )

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        actor_label = self.actor.username if self.actor else 'system'
        return (
            f'{self.publication_id}: {self.from_state} -> {self.to_state} '
            f'by {actor_label} at {self.timestamp:%Y-%m-%d %H:%M}'
        )


class PublicationAssignment(models.Model):
    """
    Tracks who is currently responsible for extracting a publication.
    One active assignment per paper at a time.
    completed_at is set when the contributor submits for review.
    """
    publication = models.ForeignKey(
        'Publication',
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assignments_made',
        help_text='Same as assigned_to if self-assigned.'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Set when the contributor submits for review.'
    )

    class Meta:
        ordering = ['-assigned_at']

    def __str__(self):
        return f'{self.publication} -> {self.assigned_to.username}'