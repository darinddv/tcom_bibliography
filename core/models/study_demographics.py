from django.db import models
from simple_history.models import HistoricalRecords


class StudyDemographics(models.Model):
    """
    Study-level participant demographics. One per StudyProfile.
    Kept separate from StudyProfile to avoid that model becoming unwieldy.
    """

    study_profile = models.OneToOneField(
        'StudyProfile',
        on_delete=models.CASCADE,
        related_name='demographics',
    )
    percent_female = models.FloatField(
        null=True,
        blank=True,
        help_text='Percentage of female participants (0-100).'
    )
    percent_male = models.FloatField(
        null=True,
        blank=True,
        help_text='Percentage of male participants (0-100).'
    )
    age_range_min = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Minimum age of participants in years.'
    )
    age_range_max = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Maximum age of participants in years.'
    )
    age_notes = models.CharField(
        max_length=200,
        blank=True,
        help_text='e.g. "mean age 12.3" or age reporting details.'
    )
    race_distribution = models.TextField(
        blank=True,
        help_text='Race/ethnicity distribution as reported. Free text due to '
                  'inconsistent reporting across studies.'
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Study Demographics'
        verbose_name_plural = 'Study Demographics'

    def __str__(self):
        return f'Demographics for {self.study_profile}'

    history = HistoricalRecords()