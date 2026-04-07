from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from core.models.publications import Publication
from core.models.workflow import PublicationAssignment
from core.models.extraction import ExtractionRecord
from core.models.deletion_request import DeletionRequest
from core.services.deletion import (
    request_deletion,
    cancel_deletion_request,
)
from contributor.decorators import contributor_required, editor_required


@contributor_required
def publication_list(request):
    """Internal contributor publications list — includes workflow controls."""
    publications = Publication.objects.exclude(
        inclusion_status='excluded'
    ).order_by('-created_at')
    return render(request, 'contributor/publication_list.html', {
        'publications': publications,
    })


@login_required
def publication_detail(request, pk):
    publication = get_object_or_404(Publication, pk=pk)

    any_assignment = PublicationAssignment.objects.filter(
        publication=publication,
        assigned_to=request.user,
    ).exists()

    active_assignment = PublicationAssignment.objects.filter(
        publication=publication,
        assigned_to=request.user,
        completed_at=None,
    ).exists()

    user_extraction = ExtractionRecord.objects.filter(
        publication=publication,
        reviewer=request.user,
    ).first()

    can_unassign = active_assignment and not user_extraction

    extractions = ExtractionRecord.objects.filter(
        publication=publication,
    ).select_related('reviewer')

    human_extraction = ExtractionRecord.objects.filter(
        publication=publication,
        reviewer_type='human',
    ).first()

    latest_transition = publication.transitions.order_by('-timestamp').first()
    current_state = latest_transition.to_state if latest_transition else 'unassigned'

    return render(request, 'contributor/publication_detail.html', {
        'publication': publication,
        'active_assignment': active_assignment,
        'any_assignment': any_assignment,
        'user_extraction': user_extraction,
        'human_extraction': human_extraction,
        'can_unassign': can_unassign,
        'extractions': extractions,
        'current_state': current_state,
    })


@contributor_required
def assign_to_me(request, pk):
    if request.method == 'POST':
        publication = get_object_or_404(Publication, pk=pk)
        from core.services.assignment import self_assign
        self_assign(publication=publication, user=request.user)
    return redirect('contributor:publication_detail', pk=pk)


@contributor_required
def unassign_me(request, pk):
    if request.method == 'POST':
        publication = get_object_or_404(Publication, pk=pk)
        has_extraction = ExtractionRecord.objects.filter(
            publication=publication,
            reviewer=request.user,
        ).exists()
        if has_extraction:
            messages.error(
                request,
                'You cannot unassign yourself after creating an extraction.'
            )
            return redirect('contributor:publication_detail', pk=pk)

        PublicationAssignment.objects.filter(
            publication=publication,
            assigned_to=request.user,
            completed_at=None,
        ).update(completed_at=timezone.now())

        messages.success(request, 'You have been unassigned from this paper.')

    return redirect('contributor:publication_detail', pk=pk)


@contributor_required
def import_doi(request):
    if request.method == 'POST':
        from core.services.doi_import import import_from_doi

        doi = request.POST.get('doi', '').strip()
        if not doi:
            messages.error(request, 'Please enter a DOI.')
            return redirect('contributor:publication_list')

        try:
            pub, created = import_from_doi(doi, submitted_by=request.user)
            if created:
                messages.success(request, f'Successfully imported: {pub.title[:80]}')
                return redirect('contributor:publication_detail', pk=pub.pk)
            else:
                messages.warning(request, 'This paper is already in the system.')
                return redirect('contributor:publication_detail', pk=pub.pk)
        except Exception as e:
            messages.error(request, f'Import failed: {e}')

    return redirect('contributor:publication_list')


@login_required
def extraction_detail(request, pk, extraction_id):
    publication = get_object_or_404(Publication, pk=pk)
    extraction = get_object_or_404(
        ExtractionRecord, pk=extraction_id, publication=publication
    )
    study_profile = getattr(extraction, 'study_profile', None)
    demographics = getattr(study_profile, 'demographics', None) if study_profile else None
    rob = getattr(extraction, 'risk_of_bias', None)
    rob_domains = rob.domains.all() if rob else []
    tool_usages = extraction.assessment_tool_usages.prefetch_related(
        'outcome_domains__domain', 'tool', 'population_type'
    )
    statistical_methods = extraction.statistical_methods.select_related('method_name')
    predictors = extraction.predictors.select_related('category')
    latest_review = extraction.reviews.order_by('-submitted_at').first()

    return render(request, 'contributor/extraction_detail.html', {
        'publication': publication,
        'extraction': extraction,
        'study_profile': study_profile,
        'demographics': demographics,
        'rob': rob,
        'rob_domains': rob_domains,
        'tool_usages': tool_usages,
        'statistical_methods': statistical_methods,
        'predictors': predictors,
        'latest_review': latest_review,
    })


@contributor_required
def upload_pdf(request, pk):
    publication = get_object_or_404(Publication, pk=pk)

    if request.method == 'POST':
        pdf_file = request.FILES.get('pdf_file')
        if not pdf_file:
            messages.error(request, 'No file selected.')
            return redirect('contributor:publication_detail', pk=pk)

        if not pdf_file.name.endswith('.pdf'):
            messages.error(request, 'Only PDF files are accepted.')
            return redirect('contributor:publication_detail', pk=pk)

        if publication.pdf_file:
            publication.pdf_file.delete(save=False)

        publication.pdf_file = pdf_file
        publication.pdf_uploaded_by = request.user
        publication.pdf_uploaded_at = timezone.now()
        publication.save()
        messages.success(request, 'PDF uploaded successfully.')

    return redirect('contributor:publication_detail', pk=pk)


@editor_required
def delete_pdf(request, pk):
    publication = get_object_or_404(Publication, pk=pk)

    if request.method == 'POST':
        if publication.pdf_file:
            publication.pdf_file.delete(save=False)
            publication.pdf_file = None
            publication.pdf_uploaded_by = None
            publication.pdf_uploaded_at = None
            publication.save()
            messages.success(request, 'PDF deleted.')

    return redirect('contributor:publication_detail', pk=pk)


@editor_required
def run_llm_extraction_view(request, pk):
    publication = get_object_or_404(Publication, pk=pk)

    if request.method == 'POST':
        from core.services.llm_extraction import run_llm_extraction
        try:
            run_llm_extraction(publication)
            messages.success(
                request,
                'LLM extraction complete. It has been added to the review queue.'
            )
        except Exception as e:
            messages.error(request, f'LLM extraction failed: {e}')

    return redirect('contributor:publication_detail', pk=pk)


@contributor_required
def request_deletion_view(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        try:
            request_deletion(
                publication=publication,
                requested_by=request.user,
                reason=reason,
            )
            messages.warning(
                request,
                'Deletion request submitted. The paper is now locked.'
            )
        except ValueError as e:
            messages.error(request, str(e))
    return redirect('contributor:publication_detail', pk=pk)


@contributor_required
def cancel_deletion_view(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    deletion_request = get_object_or_404(
        DeletionRequest,
        publication=publication,
        requested_by=request.user,
        status='pending',
    )
    if request.method == 'POST':
        try:
            cancel_deletion_request(
                deletion_request=deletion_request,
                cancelled_by=request.user,
            )
            messages.success(
                request,
                'Deletion request cancelled. The paper is now unlocked.'
            )
        except ValueError as e:
            messages.error(request, str(e))
    return redirect('contributor:publication_detail', pk=pk)
