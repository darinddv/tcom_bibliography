from django.db import models
from simple_history.models import HistoricalRecords


class PredictorCovariate(models.Model):
    """
    Predictor or covariate used in the study.
    Multiple per extraction. Category drawn from ControlledTerm
    so new categories can be added without migrations.
    """

    extraction = models.ForeignKey(
        'ExtractionRecord',
        on_delete=models.CASCADE,
        related_name='predictors',
    )
    category = models.ForeignKey(
        'ControlledTerm',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='predictors_by_category',
        limit_choices_to={'category': 'predictor_category'},
    )
    description = models.TextField(
        blank=True,
        help_text='Specific predictor or covariate as described in the paper.'
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['extraction', 'category']

    def __str__(self):
        cat = self.category.label if self.category else 'Uncategorized'
        return f'{cat}: {self.description[:60]}'

    history = HistoricalRecords()