from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class ExtractionReview(models.Model):

    DECISION_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('needs_revision', 'Needs Revision'),
    ]

    extraction = models.ForeignKey(
        'ExtractionRecord',
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews_submitted',
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewer = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviews_assigned',
        help_text='Null until a reviewer claims or is assigned to this review.'
    )
    decision = models.CharField(
        max_length=20,
        choices=DECISION_CHOICES,
        default='pending',
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Set when the reviewer records their decision.'
    )
    quality_score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text='Quality score from 1 (poor) to 10 (excellent).'
    )
    reviewer_notes = models.TextField(
        blank=True,
        help_text='Required when decision is rejected or needs revision.'
    )

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        reviewer_name = self.reviewer.username if self.reviewer else 'unassigned'
        return (
            f'Review of {self.extraction} '
            f'by {reviewer_name} '
            f'[{self.get_decision_display()}]'
        )