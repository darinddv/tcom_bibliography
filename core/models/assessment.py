from django.db import models
from simple_history.models import HistoricalRecords


class AssessmentToolUsage(models.Model):
    """
    Records the use of a specific assessment tool within an extraction.
    One record per tool per extraction. All population and outcome data
    for that tool hangs off this record.
    """

    USED_AS_CHOICES = [
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
    ]

    extraction = models.ForeignKey(
        'ExtractionRecord',
        on_delete=models.CASCADE,
        related_name='assessment_tool_usages',
    )
    tool = models.ForeignKey(
        'ControlledTerm',
        on_delete=models.PROTECT,
        related_name='assessment_tool_usages',
        limit_choices_to={'category': 'assessment_tool'},
    )
    used_as = models.CharField(
        max_length=20,
        choices=USED_AS_CHOICES,
        default='primary',
    )
    sample_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Number of participants assessed with this tool, if reported separately.'
    )
    age_range_min = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Minimum age of participants assessed with this tool.'
    )
    age_range_max = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Maximum age of participants assessed with this tool.'
    )
    population_type = models.ForeignKey(
        'ControlledTerm',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assessment_tool_usages_by_population',
        limit_choices_to={'category': 'population_type'},
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['extraction', 'tool']
        unique_together = [('extraction', 'tool')]

    def __str__(self):
        return f'{self.tool} ({self.get_used_as_display()}) — {self.extraction}'
    history = HistoricalRecords()


class OutcomeDomain(models.Model):
    """
    An outcome observed for a specific assessment tool usage.
    One or more per AssessmentToolUsage.
    """

    DIRECTION_CHOICES = [
        ('improvement', 'Improvement'),
        ('decline', 'Decline'),
        ('mixed', 'Mixed'),
        ('null', 'Null / No significant change'),
    ]

    assessment_tool_usage = models.ForeignKey(
        'AssessmentToolUsage',
        on_delete=models.CASCADE,
        related_name='outcome_domains',
    )
    domain = models.ForeignKey(
        'ControlledTerm',
        on_delete=models.PROTECT,
        related_name='outcome_domains',
        limit_choices_to={'category': 'outcome_domain'},
    )
    direction = models.CharField(
        max_length=20,
        choices=DIRECTION_CHOICES,
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['assessment_tool_usage', 'domain']
        unique_together = [('assessment_tool_usage', 'domain')]

    def __str__(self):
        direction = self.get_direction_display() if self.direction else 'no direction recorded'
        return f'{self.domain} — {direction}'
    history = HistoricalRecords()