from django.db import models
from simple_history.models import HistoricalRecords


class StudyProfile(models.Model):
    """
    Paper-level study characteristics. One per ExtractionRecord.
    Captures facts about the study as a whole, not specific to any
    particular assessment tool or subgroup.
    """

    extraction = models.OneToOneField(
        'ExtractionRecord',
        on_delete=models.CASCADE,
        related_name='study_profile',
    )
    study_design = models.ForeignKey(
        'ControlledTerm',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='study_profiles_by_design',
        limit_choices_to={'category': 'study_design'},
    )
    overall_sample_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Total number of participants across the full study.'
    )
    setting = models.ForeignKey(
        'ControlledTerm',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='study_profiles_by_setting',
        limit_choices_to={'category': 'setting'},
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        help_text='Primary country where the study was conducted.'
    )
    notes = models.TextField(
        blank=True,
        help_text='Any additional study-level observations.'
    )

    class Meta:
        ordering = ['extraction']

    def __str__(self):
        return f'Study profile for {self.extraction}'
    history = HistoricalRecords()