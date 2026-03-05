from django.db import models


class Publication(models.Model):

    # --- External Identifiers ---
    doi = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True
    )
    pmid = models.CharField(
        max_length=50,
        blank=True,
        help_text='PubMed ID'
    )
    arxiv_id = models.CharField(
        max_length=50,
        blank=True
    )

    # --- Core Bibliographic Fields ---
    title = models.TextField()
    abstract = models.TextField(blank=True)
    year = models.IntegerField(null=True, blank=True)
    volume = models.CharField(max_length=50, blank=True)
    issue = models.CharField(max_length=50, blank=True)
    pages = models.CharField(max_length=50, blank=True)
    language = models.CharField(max_length=50, default='English')
    publication_type = models.CharField(
        max_length=50,
        choices=[
            ('journal_article', 'Journal Article'),
            ('conference', 'Conference Paper'),
            ('report', 'Report'),
            ('thesis', 'Thesis'),
            ('book_chapter', 'Book Chapter'),
            ('book', 'Book'),
            ('other', 'Other'),
        ],
        default='journal_article',
    )

    # --- Source ---
    journal = models.CharField(
        max_length=255,
        blank=True,
        help_text='Journal name. Stored as text for now, can be normalised later.'
    )
    raw_metadata = models.TextField(
        blank=True,
        help_text='Raw API response from Crossref or PubMed stored as JSON string.'
    )
    metadata_source = models.CharField(
        max_length=50,
        choices=[
            ('crossref', 'Crossref'),
            ('pubmed', 'PubMed'),
            ('manual', 'Manual Entry'),
            ('other', 'Other'),
        ],
        default='manual',
    )

    # --- Curation ---
    inclusion_status = models.CharField(
        max_length=50,
        choices=[
            ('candidate', 'Candidate'),
            ('included', 'Included'),
            ('excluded', 'Excluded'),
        ],
        default='candidate',
    )
    exclusion_reason = models.TextField(
        blank=True,
        help_text='Required when inclusion_status is excluded.'
    )
    curation_notes = models.TextField(blank=True)

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year', 'title']

    def __str__(self):
        return f'{self.title[:80]} ({self.year})'