from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from core.models.publications import Publication
from core.models.workflow import PublicationAssignment
from core.models.extraction import ExtractionRecord
from core.models.study_profile import StudyProfile
from core.models.assessment import AssessmentToolUsage, OutcomeDomain
from core.models.extraction_review import ExtractionReview

from contributor.forms import StudyProfileForm, AssessmentToolUsageForm, OutcomeDomainForm

from core.services.workflow import transition, get_current_state
from core.services.extraction import approve_extraction, reject_extraction, needs_revision

from core.models.deletion_request import DeletionRequest
from core.services.deletion import request_deletion, cancel_deletion_request, resolve_deletion_request

@login_required
def dashboard(request):
    assignments = PublicationAssignment.objects.filter(
        assigned_to=request.user,
        completed_at=None,
    ).select_related('publication')

    active_extractions = ExtractionRecord.objects.filter(
        reviewer=request.user,
        status__in=['draft', 'submitted'],
    ).select_related('publication')

    return render(request, 'contributor/dashboard.html', {
        'assignments': assignments,
        'active_extractions': active_extractions,
    })


@login_required
def publication_list(request):
    publications = Publication.objects.all().order_by('-created_at')
    return render(request, 'contributor/publication_list.html', {
        'publications': publications,
    })


@login_required
def publication_detail(request, pk):
    publication = get_object_or_404(Publication, pk=pk)

    # Check for any assignment (active or completed) for this user
    any_assignment = PublicationAssignment.objects.filter(
        publication=publication,
        assigned_to=request.user,
    ).exists()

    # Active assignment (not yet completed)
    active_assignment = PublicationAssignment.objects.filter(
        publication=publication,
        assigned_to=request.user,
        completed_at=None,
    ).exists()

    # Check if this user has an existing extraction
    user_extraction = ExtractionRecord.objects.filter(
        publication=publication,
        reviewer=request.user,
    ).first()

    # Can unassign only if assigned but no extraction exists yet
    can_unassign = active_assignment and not user_extraction

    extractions = ExtractionRecord.objects.filter(
        publication=publication,
    ).select_related('reviewer')

    latest_transition = publication.transitions.order_by('-timestamp').first()
    current_state = latest_transition.to_state if latest_transition else 'unassigned'

    return render(request, 'contributor/publication_detail.html', {
        'publication': publication,
        'active_assignment': active_assignment,
        'any_assignment': any_assignment,
        'user_extraction': user_extraction,
        'can_unassign': can_unassign,
        'extractions': extractions,
        'current_state': current_state,
    })


@login_required
def assign_to_me(request, pk):
    if request.method == 'POST':
        publication = get_object_or_404(Publication, pk=pk)
        from core.services.assignment import self_assign
        self_assign(publication=publication, user=request.user)
    return redirect('contributor:publication_detail', pk=pk)


@login_required
def unassign_me(request, pk):
    if request.method == 'POST':
        publication = get_object_or_404(Publication, pk=pk)

        # Only allow unassign if no extraction exists
        has_extraction = ExtractionRecord.objects.filter(
            publication=publication,
            reviewer=request.user,
        ).exists()
        if has_extraction:
            from django.contrib import messages
            messages.error(
                request,
                'You cannot unassign yourself after creating an extraction.'
            )
            return redirect('contributor:publication_detail', pk=pk)

        from django.utils import timezone
        PublicationAssignment.objects.filter(
            publication=publication,
            assigned_to=request.user,
            completed_at=None,
        ).update(completed_at=timezone.now())

        from django.contrib import messages
        messages.success(request, 'You have been unassigned from this paper.')

    return redirect('contributor:publication_detail', pk=pk)


@login_required
def review_queue(request):
    reviews = ExtractionReview.objects.filter(
        decision='pending',
    ).select_related('extraction__publication', 'submitted_by')

    is_reviewer = (
        request.user.is_staff or
        request.user.groups.filter(name='Reviewer').exists()
    )

    return render(request, 'contributor/review_queue.html', {
        'reviews': reviews,
        'is_reviewer': is_reviewer,
    })


@login_required
def profile(request):
    return render(request, 'contributor/profile.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def extraction_form(request, pk):
    publication = get_object_or_404(Publication, pk=pk)

    # Allow access if user has any assignment (active or completed)
    # once an extraction exists, the assignment is permanent
    has_assignment = PublicationAssignment.objects.filter(
        publication=publication,
        assigned_to=request.user,
    ).exists()
    if not has_assignment:
        from django.contrib import messages
        messages.error(request, 'You are not assigned to this paper.')
        return redirect('contributor:publication_detail', pk=pk)

    # Get or create draft extraction for this user
    extraction, created = ExtractionRecord.objects.get_or_create(
        publication=publication,
        reviewer=request.user,
        defaults={'reviewer_type': 'human', 'status': 'draft'},
    )

    # Transition to in_progress if currently assigned
    current_state = get_current_state(publication)
    if current_state == 'assigned':
        transition(
            publication=publication,
            to_state='in_progress',
            actor=request.user,
            comment='Extraction form opened.',
        )

    # Get or create study profile
    study_profile, _ = StudyProfile.objects.get_or_create(extraction=extraction)

    # Get existing tool usages
    tool_usages = AssessmentToolUsage.objects.filter(
        extraction=extraction
    ).prefetch_related('outcome_domains')

    if request.method == 'POST':
        action = request.POST.get('action')
        from django.contrib import messages

        if action == 'save':
            study_form = StudyProfileForm(request.POST, instance=study_profile)
            if study_form.is_valid():
                study_form.save()
                messages.success(request, 'Extraction saved.')
            else:
                messages.error(request, f'Could not save: {study_form.errors}')

        elif action == 'submit':
            from core.services.extraction import submit_extraction
            try:
                submit_extraction(extraction=extraction, actor=request.user)
                messages.success(request, 'Extraction submitted for review.')
                return redirect('contributor:dashboard')
            except ValueError as e:
                messages.error(request, str(e))

        return redirect('contributor:extraction_form', pk=pk)

    else:
        study_form = StudyProfileForm(instance=study_profile)

    latest_review = extraction.reviews.order_by('-submitted_at').first()

    return render(request, 'contributor/extraction_form.html', {
        'publication': publication,
        'extraction': extraction,
        'study_form': study_form,
        'tool_usages': tool_usages,
        'tool_form': AssessmentToolUsageForm(),
        'outcome_form': OutcomeDomainForm(),
        'latest_review': latest_review,
    })


@login_required
def add_tool_usage(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    extraction = get_object_or_404(
        ExtractionRecord,
        publication=publication,
        reviewer=request.user,
    )
    if request.method == 'POST':
        form = AssessmentToolUsageForm(request.POST)
        if form.is_valid():
            tool_usage = form.save(commit=False)
            tool_usage.extraction = extraction
            tool_usage.save()
        else:
            from django.contrib import messages
            messages.error(request, 'Please select a valid tool.')
    return redirect('contributor:extraction_form', pk=pk)


@login_required
def add_outcome_domain(request, pk, tool_usage_id):
    publication = get_object_or_404(Publication, pk=pk)
    tool_usage = get_object_or_404(
        AssessmentToolUsage,
        pk=tool_usage_id,
        extraction__publication=publication,
        extraction__reviewer=request.user,
    )
    if request.method == 'POST':
        form = OutcomeDomainForm(request.POST)
        if form.is_valid():
            outcome = form.save(commit=False)
            outcome.assessment_tool_usage = tool_usage
            outcome.save()
    return redirect('contributor:extraction_form', pk=pk)


@login_required
def delete_tool_usage(request, pk, tool_usage_id):
    tool_usage = get_object_or_404(
        AssessmentToolUsage,
        pk=tool_usage_id,
        extraction__publication__pk=pk,
        extraction__reviewer=request.user,
    )
    if request.method == 'POST':
        tool_usage.delete()
    return redirect('contributor:extraction_form', pk=pk)


@login_required
def delete_outcome_domain(request, pk, outcome_id):
    outcome = get_object_or_404(
        OutcomeDomain,
        pk=outcome_id,
        assessment_tool_usage__extraction__publication__pk=pk,
        assessment_tool_usage__extraction__reviewer=request.user,
    )
    if request.method == 'POST':
        outcome.delete()
    return redirect('contributor:extraction_form', pk=pk)


@login_required
def review_detail(request, review_id):
    review = get_object_or_404(ExtractionReview, pk=review_id)
    extraction = review.extraction
    publication = extraction.publication

    is_reviewer = (
        request.user.is_staff or
        request.user.groups.filter(name='Reviewer').exists()
    )

    if request.method == 'POST' and is_reviewer:
        action = request.POST.get('action')
        notes = request.POST.get('reviewer_notes', '').strip()
        score = request.POST.get('quality_score', '').strip()
        quality_score = int(score) if score.isdigit() else None

        from django.contrib import messages
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
            from django.contrib import messages
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

@login_required
def extraction_detail(request, pk, extraction_id):
    publication = get_object_or_404(Publication, pk=pk)
    extraction = get_object_or_404(
        ExtractionRecord,
        pk=extraction_id,
        publication=publication,
    )
    study_profile = getattr(extraction, 'study_profile', None)
    tool_usages = extraction.assessment_tool_usages.prefetch_related(
        'outcome_domains', 'tool', 'population_type'
    )
    latest_review = extraction.reviews.order_by('-submitted_at').first()

    return render(request, 'contributor/extraction_detail.html', {
        'publication': publication,
        'extraction': extraction,
        'study_profile': study_profile,
        'tool_usages': tool_usages,
        'latest_review': latest_review,
    })


@login_required
def import_doi(request):
    """Frontend DOI import for contributors and above."""
    if request.method == 'POST':
        from django.contrib import messages
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
                messages.warning(request, f'This paper is already in the system.')
                return redirect('contributor:publication_detail', pk=pub.pk)
        except Exception as e:
            messages.error(request, f'Import failed: {e}')

    return redirect('contributor:publication_list')


@login_required
def request_deletion_view(request, pk):
    publication = get_object_or_404(Publication, pk=pk)

    if request.method == 'POST':
        from django.contrib import messages
        reason = request.POST.get('reason', '').strip()
        try:
            request_deletion(
                publication=publication,
                requested_by=request.user,
                reason=reason,
            )
            messages.warning(request, 'Deletion request submitted. The paper is now locked.')
        except ValueError as e:
            messages.error(request, str(e))

    return redirect('contributor:publication_detail', pk=pk)


@login_required
def cancel_deletion_view(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    deletion_request = get_object_or_404(
        DeletionRequest,
        publication=publication,
        requested_by=request.user,
        status='pending',
    )

    if request.method == 'POST':
        from django.contrib import messages
        try:
            cancel_deletion_request(
                deletion_request=deletion_request,
                cancelled_by=request.user,
            )
            messages.success(request, 'Deletion request cancelled. The paper is now unlocked.')
        except ValueError as e:
            messages.error(request, str(e))

    return redirect('contributor:publication_detail', pk=pk)


@login_required
def deletion_queue(request):
    """Editor-facing queue of pending deletion requests."""
    is_editor = (
        request.user.is_staff or
        request.user.groups.filter(name='Editor').exists()
    )

    pending_requests = DeletionRequest.objects.filter(
        status='pending',
    ).select_related('publication', 'requested_by')

    return render(request, 'contributor/deletion_queue.html', {
        'pending_requests': pending_requests,
        'is_editor': is_editor,
    })


@login_required
def resolve_deletion_view(request, deletion_request_id):
    deletion_request = get_object_or_404(DeletionRequest, pk=deletion_request_id)

    is_editor = (
        request.user.is_staff or
        request.user.groups.filter(name='Editor').exists()
    )
    if not is_editor:
        from django.contrib import messages
        messages.error(request, 'You do not have permission to resolve deletion requests.')
        return redirect('contributor:deletion_queue')

    if request.method == 'POST':
        from django.contrib import messages
        action = request.POST.get('action')
        note = request.POST.get('resolution_note', '').strip()
        try:
            resolve_deletion_request(
                deletion_request=deletion_request,
                resolved_by=request.user,
                approve=action == 'approve',
                note=note,
            )
            if action == 'approve':
                messages.success(request, 'Publication marked as excluded.')
            else:
                messages.success(request, 'Deletion request rejected. Paper is unlocked.')
        except ValueError as e:
            messages.error(request, str(e))

    return redirect('contributor:deletion_queue')