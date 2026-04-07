from django.shortcuts import render, get_object_or_404
from django.db.models import Q

from core.models.publications import Publication
from core.models.controlled_vocabulary import ControlledTerm


def _filter_options():
    return {
        'tools': ControlledTerm.objects.filter(
            category='assessment_tool', is_approved=True
        ).order_by('label'),
        'settings': ControlledTerm.objects.filter(
            category='setting', is_approved=True
        ).order_by('label'),
        'study_designs': ControlledTerm.objects.filter(
            category='study_design', is_approved=True
        ).order_by('label'),
        'population_types': ControlledTerm.objects.filter(
            category='population_type', is_approved=True
        ).order_by('label'),
    }


def bibliography(request):
    publications = Publication.objects.exclude(inclusion_status='excluded')

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        publications = publications.filter(
            Q(title__icontains=q) |
            Q(abstract__icontains=q) |
            Q(journal__icontains=q) |
            Q(doi__icontains=q)
        )

    # Tool filter — only papers with an approved extraction using that tool
    tool_id = request.GET.get('tool', '')
    if tool_id:
        publications = publications.filter(
            extractions__assessment_tool_usages__tool_id=tool_id,
            extractions__status='approved',
        ).distinct()

    # Setting filter
    setting_id = request.GET.get('setting', '')
    if setting_id:
        publications = publications.filter(
            extractions__study_profile__setting_id=setting_id,
            extractions__status='approved',
        ).distinct()

    # Study design filter
    design_id = request.GET.get('design', '')
    if design_id:
        publications = publications.filter(
            extractions__study_profile__study_design_id=design_id,
            extractions__status='approved',
        ).distinct()

    # Population type filter
    population_id = request.GET.get('population', '')
    if population_id:
        publications = publications.filter(
            extractions__assessment_tool_usages__population_type_id=population_id,
            extractions__status='approved',
        ).distinct()

    # Year range
    year_from = request.GET.get('year_from', '')
    if year_from.isdigit():
        publications = publications.filter(year__gte=int(year_from))

    year_to = request.GET.get('year_to', '')
    if year_to.isdigit():
        publications = publications.filter(year__lte=int(year_to))

    # Publication type
    pub_type = request.GET.get('type', '')
    if pub_type:
        publications = publications.filter(publication_type=pub_type)

    # Inclusion status
    status = request.GET.get('status', '')
    if status:
        publications = publications.filter(inclusion_status=status)

    # Sort
    sort = request.GET.get('sort', '-year')
    if sort not in ['-year', 'year', 'title', '-created_at']:
        sort = '-year'
    publications = publications.order_by(sort)

    total = publications.count()

    active_filters = {
        k: v for k, v in request.GET.items()
        if v and k not in ('sort',)
    }

    return render(request, 'contributor/bibliography.html', {
        'publications': publications,
        'total': total,
        'q': q,
        'sort': sort,
        'active_filters': active_filters,
        'pub_type_choices': Publication._meta.get_field('publication_type').choices,
        **_filter_options(),
    })


def bibliography_detail(request, pk):
    publication = get_object_or_404(
        Publication.objects.exclude(inclusion_status='excluded'),
        pk=pk,
    )
    approved_extractions = publication.extractions.filter(
        status='approved',
    ).prefetch_related(
        'study_profile__demographics',
        'assessment_tool_usages__outcome_domains__domain',
        'assessment_tool_usages__tool',
        'assessment_tool_usages__population_type',
        'statistical_methods__method_name',
        'risk_of_bias__domains',
    )

    return render(request, 'contributor/bibliography_detail.html', {
        'publication': publication,
        'extractions': approved_extractions,
    })
