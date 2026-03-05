from django.contrib.auth.models import User
from django.db import models


class ControlledTerm(models.Model):
    """
    Shared vocabulary table for all fields that require controlled input.
    A single model handles all categories -- adding a new category requires
    no schema change, just a new category choice and seed data.
    """

    CATEGORY_CHOICES = [
        ('study_design', 'Study Design'),
        ('setting', 'Setting'),
        ('population_type', 'Population Type'),
        ('assessment_tool', 'Assessment Tool'),
        ('tool_usage_type', 'Tool Usage Type'),
        ('outcome_domain', 'Outcome Domain'),
    ]

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        db_index=True,
    )
    label = models.CharField(
        max_length=255,
        help_text='Full display name, e.g. "Child and Adolescent Needs and Strengths"'
    )
    abbreviation = models.CharField(
        max_length=50,
        blank=True,
        help_text='Short form, e.g. "CANS"'
    )
    is_approved = models.BooleanField(
        default=False,
        help_text='Only approved terms appear in user-facing dropdowns.'
    )
    suggested_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='suggested_terms',
        help_text='Null if seeded by admin.'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'label']
        unique_together = [('category', 'label')]

    def __str__(self):
        if self.abbreviation:
            return f'{self.abbreviation} — {self.label} ({self.category})'
        return f'{self.label} ({self.category})'