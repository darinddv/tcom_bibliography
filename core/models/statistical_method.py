from django.db import models
from simple_history.models import HistoricalRecords


METHOD_CATEGORY_CHOICES = [
    ('regression', 'Regression (continuous outcome)'),
    ('classification', 'Classification (discrete outcome)'),
    ('reliability', 'Reliability'),
    ('validity', 'Validity'),
    ('descriptive', 'Descriptive'),
    ('other', 'Other'),
]


class StatisticalMethod(models.Model):
    """
    Statistical approach used in the study.
    Multiple methods per extraction are allowed.
    """

    extraction = models.ForeignKey(
        'ExtractionRecord',
        on_delete=models.CASCADE,
        related_name='statistical_methods',
    )
    method_category = models.CharField(
        max_length=30,
        choices=METHOD_CATEGORY_CHOICES,
        blank=True,
    )
    method_name = models.ForeignKey(
        'ControlledTerm',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='statistical_methods',
        limit_choices_to={'category': 'statistical_method'},
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['extraction', 'method_category']

    def __str__(self):
        name = self.method_name.label if self.method_name else 'Unspecified'
        return f'{name} ({self.get_method_category_display()})'

    history = HistoricalRecords()