from django.shortcuts import render
from django.db.models import Count

from core.models.publications import Publication
from core.models.controlled_vocabulary import ControlledTerm
from core.models.assessment import AssessmentToolUsage
from core.models.study_profile import StudyProfile
from core.models.extraction import ExtractionRecord


def dashboard(request):
    # Publication counts
    total_publications = Publication.objects.exclude(
        inclusion_status='excluded'
    ).count()
    included = Publication.objects.filter(inclusion_status='included').count()
    candidate = Publication.objects.filter(inclusion_status='candidate').count()

    # Publications by year (most recent 20)
    by_year = list(
        Publication.objects
        .exclude(inclusion_status='excluded')
        .exclude(year__isnull=True)
        .values('year')
        .annotate(count=Count('id'))
        .order_by('-year')[:20]
    )

    # Publications by type
    by_type = list(
        Publication.objects
        .exclude(inclusion_status='excluded')
        .values('publication_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Only use approved extractions for research data
    approved = ExtractionRecord.objects.filter(status='approved')
    total_extractions = approved.count()

    # Tool usage frequency
    tool_counts = list(
        AssessmentToolUsage.objects
        .filter(extraction__in=approved)
        .values('tool__label', 'tool__abbreviation')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    # Max tool count for progress bar scaling
    max_tool_count = tool_counts[0]['count'] if tool_counts else 1

    # Study design distribution
    design_counts = list(
        StudyProfile.objects
        .filter(extraction__in=approved)
        .exclude(study_design__isnull=True)
        .values('study_design__label')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Country distribution (top 10)
    country_counts = list(
        StudyProfile.objects
        .filter(extraction__in=approved)
        .exclude(country='')
        .values('country')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    # Max year count for progress bar scaling
    max_year_count = max((item['count'] for item in by_year), default=1)

    return render(request, 'contributor/analytics.html', {
        'total_publications': total_publications,
        'included': included,
        'candidate': candidate,
        'total_extractions': total_extractions,
        'by_year': by_year,
        'max_year_count': max_year_count,
        'by_type': by_type,
        'tool_counts': tool_counts,
        'max_tool_count': max_tool_count,
        'design_counts': design_counts,
        'country_counts': country_counts,
    })
