from django.shortcuts import render, redirect
from django.db.models import Count

from core.models.publications import Publication
from core.models.controlled_vocabulary import ControlledTerm


def landing(request):
    if request.user.is_authenticated:
        return redirect('contributor:analytics')

    stats = {
        'publication_count': Publication.objects.exclude(
            inclusion_status='excluded'
        ).count(),
        'tool_count': ControlledTerm.objects.filter(
            category='assessment_tool',
            is_approved=True,
        ).count(),
        'included_count': Publication.objects.filter(
            inclusion_status='included'
        ).count(),
    }

    return render(request, 'contributor/landing.html', {'stats': stats})
