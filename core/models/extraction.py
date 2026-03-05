from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords


class ExtractionRecord(models.Model):
    """
    The anchor for all extraction data on a publication.
    One record per reviewer per publication -- human or LLM.
    Everything extracted from a paper hangs off this record.
    """

    REVIEWER_TYPE_CHOICES = [
        ('human', 'Human'),
        ('llm', 'LLM'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    publication = models.ForeignKey(
        'Publication',
        on_delete=models.CASCADE,
        related_name='extractions',
    )
    reviewer = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='extractions',
        help_text='Null if this is an LLM extraction.'
    )
    reviewer_type = models.CharField(
        max_length=10,
        choices=REVIEWER_TYPE_CHOICES,
        default='human',
    )
    llm_model = models.CharField(
        max_length=100,
        blank=True,
        help_text='Model identifier if reviewer_type is LLM, e.g. claude-sonnet-4-6.'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        # One extraction per human reviewer per publication.
        # LLM extractions are not constrained -- multiple runs per model are allowed
        # to support prompt development and performance comparison.
        unique_together = [('publication', 'reviewer')]

    def __str__(self):
        if self.reviewer_type == 'llm':
            return f'{self.publication} — LLM ({self.llm_model})'
        reviewer_name = self.reviewer.username if self.reviewer else 'unknown'
        return f'{self.publication} — {reviewer_name}'
    history = HistoricalRecords()
