from django.db import models
from simple_history.models import HistoricalRecords


US_STATES = [
    ('', 'N/A'),
    ('AL', 'Alabama'), ('AK', 'Alaska'), ('AZ', 'Arizona'), ('AR', 'Arkansas'),
    ('CA', 'California'), ('CO', 'Colorado'), ('CT', 'Connecticut'), ('DE', 'Delaware'),
    ('FL', 'Florida'), ('GA', 'Georgia'), ('HI', 'Hawaii'), ('ID', 'Idaho'),
    ('IL', 'Illinois'), ('IN', 'Indiana'), ('IA', 'Iowa'), ('KS', 'Kansas'),
    ('KY', 'Kentucky'), ('LA', 'Louisiana'), ('ME', 'Maine'), ('MD', 'Maryland'),
    ('MA', 'Massachusetts'), ('MI', 'Michigan'), ('MN', 'Minnesota'), ('MS', 'Mississippi'),
    ('MO', 'Missouri'), ('MT', 'Montana'), ('NE', 'Nebraska'), ('NV', 'Nevada'),
    ('NH', 'New Hampshire'), ('NJ', 'New Jersey'), ('NM', 'New Mexico'), ('NY', 'New York'),
    ('NC', 'North Carolina'), ('ND', 'North Dakota'), ('OH', 'Ohio'), ('OK', 'Oklahoma'),
    ('OR', 'Oregon'), ('PA', 'Pennsylvania'), ('RI', 'Rhode Island'), ('SC', 'South Carolina'),
    ('SD', 'South Dakota'), ('TN', 'Tennessee'), ('TX', 'Texas'), ('UT', 'Utah'),
    ('VT', 'Vermont'), ('VA', 'Virginia'), ('WA', 'Washington'), ('WV', 'West Virginia'),
    ('WI', 'Wisconsin'), ('WY', 'Wyoming'), ('DC', 'District of Columbia'),
    ('PR', 'Puerto Rico'), ('VI', 'Virgin Islands'), ('GU', 'Guam'),
]

FUNDING_SOURCE_CHOICES = [
    ('', 'Not reported'),
    ('government', 'Government'),
    ('industry', 'Industry'),
    ('nonprofit', 'Nonprofit / Foundation'),
    ('university', 'University / Academic'),
    ('mixed', 'Mixed'),
    ('none', 'No funding reported'),
    ('unclear', 'Unclear'),
]

CONFLICTS_CHOICES = [
    ('', 'Not reported'),
    ('yes', 'Yes'),
    ('no', 'No'),
    ('unclear', 'Unclear'),
]


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

    # --- Study Design ---
    study_design = models.ForeignKey(
        'ControlledTerm',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='study_profiles_by_design',
        limit_choices_to={'category': 'study_design'},
    )
    study_duration_years = models.FloatField(
        null=True,
        blank=True,
        help_text='Years of cross-sectional data or duration of follow-up.'
    )
    follow_up_duration = models.CharField(
        max_length=200,
        blank=True,
        help_text='Description of follow-up duration if longitudinal.'
    )

    # --- Sample ---
    overall_sample_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Total number of participants across the full study.'
    )
    inclusion_criteria = models.TextField(
        blank=True,
        help_text='Participant inclusion criteria as reported.'
    )
    exclusion_criteria = models.TextField(
        blank=True,
        help_text='Participant exclusion criteria as reported.'
    )

    # --- Location ---
    country = models.CharField(
        max_length=100,
        blank=True,
        help_text='Primary country where the study was conducted.'
    )
    us_state = models.CharField(
        max_length=2,
        choices=US_STATES,
        blank=True,
        help_text='US state if applicable.'
    )

    # --- Setting ---
    setting = models.ForeignKey(
        'ControlledTerm',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='study_profiles_by_setting',
        limit_choices_to={'category': 'setting'},
    )

    # --- Quality ---
    funding_source = models.CharField(
        max_length=20,
        choices=FUNDING_SOURCE_CHOICES,
        blank=True,
    )
    conflicts_of_interest = models.CharField(
        max_length=20,
        choices=CONFLICTS_CHOICES,
        blank=True,
    )

    # --- Notes ---
    notes = models.TextField(
        blank=True,
        help_text='Any additional study-level observations.'
    )

    class Meta:
        ordering = ['extraction']

    def __str__(self):
        return f'Study profile for {self.extraction}'

    history = HistoricalRecords()