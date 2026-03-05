import json
import httpx
from core.models.publications import Publication
from core.models.workflow import WorkflowTransition


CROSSREF_URL = 'https://api.crossref.org/works/{doi}'


def import_from_doi(doi: str) -> tuple[Publication, bool]:
    """
    Given a DOI string, fetch metadata from Crossref and create a Publication.
    Returns a tuple of (publication, created) where created is True if a new
    record was made, False if one already existed with that DOI.
    """
    doi = doi.strip()

    # Deduplication check -- never import the same DOI twice
    existing = Publication.objects.filter(doi=doi).first()
    if existing:
        return existing, False

    # Fetch from Crossref
    response = httpx.get(
        CROSSREF_URL.format(doi=doi),
        headers={'User-Agent': 'tcom-bibliography/0.1 (mailto:your@email.com)'},
        timeout=10.0,
    )
    response.raise_for_status()
    data = response.json()
    work = data['message']

    # Parse fields
    title = _extract_title(work)
    year = _extract_year(work)
    journal = _extract_journal(work)
    abstract = work.get('abstract', '')
    volume = work.get('volume', '')
    issue = work.get('issue', '')
    pages = work.get('page', '')
    publication_type = _extract_type(work)

    publication = Publication.objects.create(
        doi=doi,
        title=title,
        abstract=abstract,
        year=year,
        journal=journal,
        volume=volume,
        issue=issue,
        pages=pages,
        publication_type=publication_type,
        metadata_source='crossref',
        raw_metadata=json.dumps(work),
    )

    # Create initial workflow transition
    WorkflowTransition.objects.create(
        publication=publication,
        from_state='',
        to_state='unassigned',
        actor=None,
        is_system_action=True,
        comment='Automatically created on DOI import.',
    )

    return publication, True


def _extract_title(work: dict) -> str:
    titles = work.get('title', [])
    return titles[0] if titles else 'Unknown Title'


def _extract_year(work: dict) -> int | None:
    date_parts = (
        work.get('published-print', {}).get('date-parts') or
        work.get('published-online', {}).get('date-parts') or
        work.get('created', {}).get('date-parts')
    )
    if date_parts and date_parts[0]:
        return date_parts[0][0]
    return None


def _extract_journal(work: dict) -> str:
    container = work.get('container-title', [])
    return container[0] if container else ''


def _extract_type(work: dict) -> str:
    type_map = {
        'journal-article': 'journal_article',
        'proceedings-article': 'conference',
        'book-chapter': 'book_chapter',
        'book': 'book',
        'report': 'report',
        'dissertation': 'thesis',
    }
    return type_map.get(work.get('type', ''), 'other')