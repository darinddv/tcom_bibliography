from django.db import models
from simple_history.models import HistoricalRecords


SIGNIFICANCE_CHOICES = [
    ('', 'Not reported'),
    ('significant', 'Statistically significant'),
    ('not_significant', 'Not statistically significant'),
    ('unclear', 'Unclear'),
]

EFFECT_SIZE_TYPE_CHOICES = [
    ('', 'Not reported'),
    ('beta', 'Beta coefficient'),
    ('or', 'Odds ratio (OR)'),
    ('rr', 'Risk ratio (RR)'),
    ('mean_diff', 'Mean difference'),
    ('cohen_d', "Cohen's d"),
    ('r', 'Correlation (r)'),
    ('other', 'Other'),
]

SCORING_METHOD_CHOICES = [
    ('', 'Not reported'),
    ('total_score', 'Total score'),
    ('subscale', 'Subscale score'),
    ('cutoff', 'Cutoff / threshold'),
    ('change_score', 'Change score'),
    ('other', 'Other'),
]

ADMINISTRATION_TIMING_CHOICES = [
    ('', 'Not reported'),
    ('intake', 'Intake / Baseline'),
    ('discharge', 'Discharge'),
    ('follow_up', 'Follow-up'),
    ('cross_sectional', 'Cross-sectional'),
    ('multiple', 'Multiple timepoints'),
    ('other', 'Other'),
]


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

    # --- Sample ---
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
    sample_descriptor = models.TextField(
        blank=True,
        help_text='Description of the sample assessed with this tool.'
    )

    # --- Administration ---
    administration_timing = models.CharField(
        max_length=20,
        choices=ADMINISTRATION_TIMING_CHOICES,
        blank=True,
        help_text='When the tool was administered relative to the study timeline.'
    )
    scoring_method = models.CharField(
        max_length=20,
        choices=SCORING_METHOD_CHOICES,
        blank=True,
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

    # --- Results ---
    outcome_metric = models.TextField(
        blank=True,
        help_text='Specific metric used to measure this outcome.'
    )
    predictor = models.TextField(
        blank=True,
        help_text='Predictor associated with this outcome if applicable.'
    )
    is_case_control = models.BooleanField(
        default=False,
        help_text='Whether this outcome is from a case-control comparison.'
    )
    effect_size_type = models.CharField(
        max_length=20,
        choices=EFFECT_SIZE_TYPE_CHOICES,
        blank=True,
    )
    effect_size_value = models.FloatField(
        null=True,
        blank=True,
        help_text='Numeric effect size value.'
    )
    confidence_interval = models.CharField(
        max_length=50,
        blank=True,
        help_text='e.g. "0.23-0.45" or "95% CI: 1.2-3.4"'
    )
    p_value = models.CharField(
        max_length=50,
        blank=True,
        help_text='e.g. "0.032" or "<0.001". Stored as text to preserve original reporting.'
    )
    significance = models.CharField(
        max_length=20,
        choices=SIGNIFICANCE_CHOICES,
        blank=True,
    )
    result_description = models.TextField(
        blank=True,
        help_text='Short description of the result as reported in the paper.'
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['assessment_tool_usage', 'domain']
        unique_together = [('assessment_tool_usage', 'domain')]

    def __str__(self):
        direction = self.get_direction_display() if self.direction else 'no direction recorded'
        return f'{self.domain} — {direction}'

    history = HistoricalRecords()