from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from core.models.extraction_review import ExtractionReview
from core.services.extraction import approve_extraction, reject_extraction, needs_revision
from contributor.decorators import contributor_required


@contributor_required
def review_queue(request):
    reviews = ExtractionReview.objects.filter(
        decision='pending',
    ).select_related('extraction__publication', 'submitted_by')

    return render(request, 'contributor/review_queue.html', {
        'reviews': reviews,
    })


@contributor_required
def review_detail(request, review_id):
    review = get_object_or_404(ExtractionReview, pk=review_id)
    extraction = review.extraction
    publication = extraction.publication

    is_reviewer = (
        request.user.is_staff or
        request.user.groups.filter(name__in=['Reviewer', 'Editor']).exists()
    )

    if request.method == 'POST' and is_reviewer:
        action = request.POST.get('action')
        notes = request.POST.get('reviewer_notes', '').strip()
        score = request.POST.get('quality_score', '').strip()
        quality_score = int(score) if score.isdigit() else None

        try:
            if action == 'approve':
                approve_extraction(
                    review=review,
                    reviewer=request.user,
                    notes=notes,
                    quality_score=quality_score,
                )
                messages.success(request, 'Extraction approved.')
                return redirect('contributor:review_queue')

            elif action == 'needs_revision':
                needs_revision(
                    review=review,
                    reviewer=request.user,
                    notes=notes,
                    quality_score=quality_score,
                )
                messages.warning(request, 'Extraction returned for revision.')
                return redirect('contributor:review_queue')

            elif action == 'reject':
                reject_extraction(
                    review=review,
                    reviewer=request.user,
                    notes=notes,
                    quality_score=quality_score,
                )
                messages.error(request, 'Extraction rejected.')
                return redirect('contributor:review_queue')

        except ValueError as e:
            messages.error(request, str(e))

    study_profile = getattr(extraction, 'study_profile', None)
    tool_usages = extraction.assessment_tool_usages.prefetch_related(
        'outcome_domains', 'tool', 'population_type'
    )

    return render(request, 'contributor/review_detail.html', {
        'review': review,
        'extraction': extraction,
        'publication': publication,
        'study_profile': study_profile,
        'tool_usages': tool_usages,
        'is_reviewer': is_reviewer,
    })
