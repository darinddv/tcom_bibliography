from django.db import models
from simple_history.models import HistoricalRecords


FRAMEWORK_CHOICES = [
    ('rob2', 'Cochrane RoB 2 (RCTs)'),
    ('robins_i', 'ROBINS-I (Observational)'),
    ('other', 'Other'),
]

OVERALL_RATING_CHOICES = [
    ('low', 'Low'),
    ('some_concerns', 'Some Concerns'),
    ('high', 'High'),
    ('critical', 'Critical'),
    ('unclear', 'Unclear'),
]

DOMAIN_RATING_CHOICES = [
    ('low', 'Low'),
    ('some_concerns', 'Some Concerns'),
    ('high', 'High'),
    ('na', 'Not Applicable'),
    ('unclear', 'Unclear'),
]


class RiskOfBiasAssessment(models.Model):
    """
    Risk of bias assessment for an extraction.
    Framework choice determines which domain names are relevant.
    """

    extraction = models.OneToOneField(
        'ExtractionRecord',
        on_delete=models.CASCADE,
        related_name='risk_of_bias',
    )
    framework = models.CharField(
        max_length=20,
        choices=FRAMEWORK_CHOICES,
        blank=True,
    )
    overall_rating = models.CharField(
        max_length=20,
        choices=OVERALL_RATING_CHOICES,
        blank=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Risk of Bias Assessment'

    def __str__(self):
        return f'RoB for {self.extraction} [{self.get_framework_display()}]'

    history = HistoricalRecords()


class RiskOfBiasDomain(models.Model):
    """
    Individual domain rating within a risk of bias assessment.
    Domain names vary by framework so stored as free text.
    """

    assessment = models.ForeignKey(
        'RiskOfBiasAssessment',
        on_delete=models.CASCADE,
        related_name='domains',
    )
    domain_name = models.CharField(
        max_length=200,
        help_text='e.g. "Randomization process" or "Missing outcome data"'
    )
    rating = models.CharField(
        max_length=20,
        choices=DOMAIN_RATING_CHOICES,
        blank=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['assessment', 'domain_name']

    def __str__(self):
        return f'{self.domain_name} — {self.get_rating_display()}'