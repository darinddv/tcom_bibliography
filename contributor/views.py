from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from core.models.publications import Publication
from core.models.workflow import PublicationAssignment
from core.models.extraction import ExtractionRecord
from core.models.study_profile import StudyProfile
from core.models.study_demographics import StudyDemographics
from core.models.risk_of_bias import RiskOfBiasAssessment, RiskOfBiasDomain
from core.models.statistical_method import StatisticalMethod
from core.models.predictor import PredictorCovariate
from core.models.assessment import AssessmentToolUsage, OutcomeDomain
from core.models.extraction_review import ExtractionReview
from core.models.deletion_request import DeletionRequest

from contributor.forms import (
    StudyProfileForm, StudyDemographicsForm,
    RiskOfBiasForm, RiskOfBiasDomainForm,
    AssessmentToolUsageForm, OutcomeDomainForm,
    StatisticalMethodForm, PredictorCovariateForm,
)

from core.services.workflow import transition, get_current_state
from core.services.extraction import approve_extraction, reject_extraction, needs_revision
from core.services.deletion import request_deletion, cancel_deletion_request, resolve_deletion_request


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_extraction_or_redirect(request, publication):
    """
    Returns the ExtractionRecord for this request.
    For LLM extractions, reads extraction_id from POST/GET data.
    For human extractions, uses assignment check.
    """
    extraction_id = request.POST.get('extraction_id') or request.GET.get('extraction_id')

    if extraction_id:
        if not (request.user.is_staff or
                request.user.groups.filter(name='Editor').exists() or
                request.user.groups.filter(name='Reviewer').exists()):
            return None, redirect('contributor:publication_detail', pk=publication.pk)
        extraction = get_object_or_404(
            ExtractionRecord,
            pk=extraction_id,
            publication=publication,
        )
        return extraction, None

    has_assignment = PublicationAssignment.objects.filter(
        publication=publication,
        assigned_to=request.user,
    ).exists()
    if not has_assignment:
        return None, redirect('contributor:publication_detail', pk=publication.pk)

    extraction, _ = ExtractionRecord.objects.get_or_create(
        publication=publication,
        reviewer=request.user,
        defaults={'reviewer_type': 'human', 'status': 'draft'},
    )
    return extraction, None


def _check_not_locked(publication, request):
    if publication.is_locked():
        from django.contrib import messages
        messages.error(request, 'This paper is locked pending a deletion request.')
        return redirect('contributor:publication_detail', pk=publication.pk)
    return None


def _tools_context(extraction):
    return {
        'tool_usages': AssessmentToolUsage.objects.filter(
            extraction=extraction
        ).prefetch_related('outcome_domains__domain', 'tool', 'population_type'),
        'tool_form': AssessmentToolUsageForm(),
        'outcome_form': OutcomeDomainForm(),
        'extraction': extraction,
        'publication': extraction.publication,
        'extraction_id': extraction.pk if extraction.reviewer_type == 'llm' else '',
    }


def _statistical_context(extraction):
    return {
        'statistical_methods': StatisticalMethod.objects.filter(extraction=extraction),
        'statistical_form': StatisticalMethodForm(),
        'extraction': extraction,
        'publication': extraction.publication,
        'extraction_id': extraction.pk if extraction.reviewer_type == 'llm' else '',
    }


def _predictors_context(extraction):
    return {
        'predictors': PredictorCovariate.objects.filter(extraction=extraction),
        'predictor_form': PredictorCovariateForm(),
        'extraction': extraction,
        'publication': extraction.publication,
        'extraction_id': extraction.pk if extraction.reviewer_type == 'llm' else '',
    }


def _rob_context(extraction):
    rob, _ = RiskOfBiasAssessment.objects.get_or_create(extraction=extraction)
    return {
        'rob': rob,
        'rob_form': RiskOfBiasForm(instance=rob),
        'rob_domain_form': RiskOfBiasDomainForm(),
        'rob_domains': RiskOfBiasDomain.objects.filter(assessment=rob),
        'extraction': extraction,
        'publication': extraction.publication,
        'extraction_id': extraction.pk if extraction.reviewer_type == 'llm' else '',
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Publications
# ---------------------------------------------------------------------------

@login_required
def publication_list(request):
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
        has_extraction = ExtractionRecord.objects.filter(
            publication=publication,
            reviewer=request.user,
        ).exists()
        if has_extraction:
            from django.contrib import messages
            messages.error(request, 'You cannot unassign yourself after creating an extraction.')
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
def import_doi(request):
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
                messages.warning(request, 'This paper is already in the system.')
                return redirect('contributor:publication_detail', pk=pub.pk)
        except Exception as e:
            messages.error(request, f'Import failed: {e}')

    return redirect('contributor:publication_list')


@login_required
def extraction_detail(request, pk, extraction_id):
    publication = get_object_or_404(Publication, pk=pk)
    extraction = get_object_or_404(ExtractionRecord, pk=extraction_id, publication=publication)
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

@login_required
def upload_pdf(request, pk):
    publication = get_object_or_404(Publication, pk=pk)

    if not (request.user.is_staff or
            request.user.groups.filter(name='Editor').exists() or
            request.user.groups.filter(name='Contributor').exists()):
        from django.contrib import messages
        messages.error(request, 'You do not have permission to upload PDFs.')
        return redirect('contributor:publication_detail', pk=pk)

    if request.method == 'POST':
        from django.contrib import messages
        from django.utils import timezone

        pdf_file = request.FILES.get('pdf_file')
        if not pdf_file:
            messages.error(request, 'No file selected.')
            return redirect('contributor:publication_detail', pk=pk)

        if not pdf_file.name.endswith('.pdf'):
            messages.error(request, 'Only PDF files are accepted.')
            return redirect('contributor:publication_detail', pk=pk)

        # Delete old PDF if one exists
        if publication.pdf_file:
            publication.pdf_file.delete(save=False)

        publication.pdf_file = pdf_file
        publication.pdf_uploaded_by = request.user
        publication.pdf_uploaded_at = timezone.now()
        publication.save()

        messages.success(request, 'PDF uploaded successfully.')

    return redirect('contributor:publication_detail', pk=pk)


@login_required
def delete_pdf(request, pk):
    publication = get_object_or_404(Publication, pk=pk)

    if not (request.user.is_staff or
            request.user.groups.filter(name='Editor').exists()):
        from django.contrib import messages
        messages.error(request, 'You do not have permission to delete PDFs.')
        return redirect('contributor:publication_detail', pk=pk)

    if request.method == 'POST':
        from django.contrib import messages
        if publication.pdf_file:
            publication.pdf_file.delete(save=False)
            publication.pdf_file = None
            publication.pdf_uploaded_by = None
            publication.pdf_uploaded_at = None
            publication.save()
            messages.success(request, 'PDF deleted.')

    return redirect('contributor:publication_detail', pk=pk)
# ---------------------------------------------------------------------------
# Extraction form — full page
# ---------------------------------------------------------------------------

@login_required
def extraction_form(request, pk, extraction_id=None):
    publication = get_object_or_404(Publication, pk=pk)

    lock_response = _check_not_locked(publication, request)
    if lock_response:
        return lock_response

    # LLM extraction editing — requires editor/reviewer/staff
    if extraction_id:
        if not (request.user.is_staff or
                request.user.groups.filter(name='Editor').exists() or
                request.user.groups.filter(name='Reviewer').exists()):
            from django.contrib import messages
            messages.error(request, 'You do not have permission to edit LLM extractions.')
            return redirect('contributor:publication_detail', pk=pk)
        extraction = get_object_or_404(
            ExtractionRecord,
            pk=extraction_id,
            publication=publication,
            reviewer_type='llm',
        )

    # Human extraction — requires assignment
    else:
        has_assignment = PublicationAssignment.objects.filter(
            publication=publication,
            assigned_to=request.user,
        ).exists()
        if not has_assignment:
            from django.contrib import messages
            messages.error(request, 'You are not assigned to this paper.')
            return redirect('contributor:publication_detail', pk=pk)

        extraction, _ = ExtractionRecord.objects.get_or_create(
            publication=publication,
            reviewer=request.user,
            defaults={'reviewer_type': 'human', 'status': 'draft'},
        )

        current_state = get_current_state(publication)
        if current_state == 'assigned':
            transition(
                publication=publication,
                to_state='in_progress',
                actor=request.user,
                comment='Extraction form opened.',
            )

    study_profile, _ = StudyProfile.objects.get_or_create(extraction=extraction)
    demographics, _ = StudyDemographics.objects.get_or_create(study_profile=study_profile)
    rob, _ = RiskOfBiasAssessment.objects.get_or_create(extraction=extraction)
    latest_review = extraction.reviews.order_by('-submitted_at').first()
    llm_extraction_id = extraction.pk if extraction.reviewer_type == 'llm' else ''

    return render(request, 'contributor/extraction_form.html', {
        'publication': publication,
        'extraction': extraction,
        'latest_review': latest_review,
        'extraction_id': llm_extraction_id,
        'study_form': StudyProfileForm(instance=study_profile),
        'demographics_form': StudyDemographicsForm(instance=demographics),
        'rob_form': RiskOfBiasForm(instance=rob),
        'rob_domain_form': RiskOfBiasDomainForm(),
        'rob_domains': RiskOfBiasDomain.objects.filter(assessment=rob),
        'rob': rob,
        **_tools_context(extraction),
        **_statistical_context(extraction),
        **_predictors_context(extraction),
    })


# ---------------------------------------------------------------------------
# Extraction form — HTMX partial saves
# ---------------------------------------------------------------------------

@login_required
@require_POST
def save_study_profile(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)

    study_profile, _ = StudyProfile.objects.get_or_create(extraction=extraction)
    form = StudyProfileForm(request.POST, instance=study_profile)
    if form.is_valid():
        form.save()
        return HttpResponse(status=204)
    return HttpResponse(status=422)


@login_required
@require_POST
def save_demographics(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)

    study_profile, _ = StudyProfile.objects.get_or_create(extraction=extraction)
    demographics, _ = StudyDemographics.objects.get_or_create(study_profile=study_profile)
    form = StudyDemographicsForm(request.POST, instance=demographics)
    if form.is_valid():
        form.save()
        return HttpResponse(status=204)
    return HttpResponse(status=422)


@login_required
@require_POST
def save_risk_of_bias(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)

    rob, _ = RiskOfBiasAssessment.objects.get_or_create(extraction=extraction)
    form = RiskOfBiasForm(request.POST, instance=rob)
    if form.is_valid():
        form.save()
        return HttpResponse(status=204)
    return HttpResponse(status=422)


@login_required
@require_POST
def add_rob_domain(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)

    rob, _ = RiskOfBiasAssessment.objects.get_or_create(extraction=extraction)
    form = RiskOfBiasDomainForm(request.POST)
    if form.is_valid():
        domain = form.save(commit=False)
        domain.assessment = rob
        domain.save()

    return render(request, 'contributor/partials/rob_section.html', _rob_context(extraction))


@login_required
@require_POST
def delete_rob_domain(request, pk, domain_id):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)

    domain = get_object_or_404(RiskOfBiasDomain, pk=domain_id,
                                assessment__extraction=extraction)
    domain.delete()
    return render(request, 'contributor/partials/rob_section.html', _rob_context(extraction))


# ---------------------------------------------------------------------------
# Extraction form — HTMX tool actions
# ---------------------------------------------------------------------------

@login_required
def tools_section(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)
    return render(request, 'contributor/partials/tools_section.html', _tools_context(extraction))


@login_required
@require_POST
def add_tool_usage(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)

    form = AssessmentToolUsageForm(request.POST)
    if form.is_valid():
        tool_usage = form.save(commit=False)
        tool_usage.extraction = extraction
        tool_usage.save()

    return render(request, 'contributor/partials/tools_section.html', _tools_context(extraction))


@login_required
@require_POST
def delete_tool_usage(request, pk, tool_usage_id):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)

    tool_usage = get_object_or_404(AssessmentToolUsage, pk=tool_usage_id,
                                    extraction=extraction)
    tool_usage.delete()
    return render(request, 'contributor/partials/tools_section.html', _tools_context(extraction))


@login_required
@require_POST
def add_outcome_domain(request, pk, tool_usage_id):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)

    tool_usage = get_object_or_404(AssessmentToolUsage, pk=tool_usage_id,
                                    extraction=extraction)
    form = OutcomeDomainForm(request.POST)
    if form.is_valid():
        outcome = form.save(commit=False)
        outcome.assessment_tool_usage = tool_usage
        outcome.save()

    return render(request, 'contributor/partials/tools_section.html', _tools_context(extraction))


@login_required
@require_POST
def delete_outcome_domain(request, pk, outcome_id):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)

    outcome = get_object_or_404(
        OutcomeDomain, pk=outcome_id,
        assessment_tool_usage__extraction=extraction,
    )
    outcome.delete()
    return render(request, 'contributor/partials/tools_section.html', _tools_context(extraction))


# ---------------------------------------------------------------------------
# Extraction form — HTMX statistical methods
# ---------------------------------------------------------------------------

@login_required
@require_POST
def add_statistical_method(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)

    form = StatisticalMethodForm(request.POST)
    if form.is_valid():
        method = form.save(commit=False)
        method.extraction = extraction
        method.save()

    return render(request, 'contributor/partials/statistical_section.html',
                  _statistical_context(extraction))


@login_required
@require_POST
def delete_statistical_method(request, pk, method_id):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)

    method = get_object_or_404(StatisticalMethod, pk=method_id, extraction=extraction)
    method.delete()
    return render(request, 'contributor/partials/statistical_section.html',
                  _statistical_context(extraction))


# ---------------------------------------------------------------------------
# Extraction form — HTMX predictors
# ---------------------------------------------------------------------------

@login_required
@require_POST
def add_predictor(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)

    form = PredictorCovariateForm(request.POST)
    if form.is_valid():
        predictor = form.save(commit=False)
        predictor.extraction = extraction
        predictor.save()

    return render(request, 'contributor/partials/predictors_section.html',
                  _predictors_context(extraction))


@login_required
@require_POST
def delete_predictor(request, pk, predictor_id):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)

    predictor = get_object_or_404(PredictorCovariate, pk=predictor_id, extraction=extraction)
    predictor.delete()
    return render(request, 'contributor/partials/predictors_section.html',
                  _predictors_context(extraction))


# ---------------------------------------------------------------------------
# Extraction form — submit
# ---------------------------------------------------------------------------

@login_required
@require_POST
def submit_extraction_view(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return err

    from django.contrib import messages
    from core.services.extraction import submit_extraction
    try:
        submit_extraction(extraction=extraction, actor=request.user)
        messages.success(request, 'Extraction submitted for review.')
    except ValueError as e:
        messages.error(request, str(e))

    return redirect('contributor:dashboard')

@login_required
def run_llm_extraction_view(request, pk):
    publication = get_object_or_404(Publication, pk=pk)

    if not (request.user.is_staff or request.user.groups.filter(name='Editor').exists()):
        from django.contrib import messages
        messages.error(request, 'You do not have permission to run LLM extractions.')
        return redirect('contributor:publication_detail', pk=pk)

    if request.method == 'POST':
        from django.contrib import messages
        from core.services.llm_extraction import run_llm_extraction
        try:
            extraction = run_llm_extraction(publication)
            messages.success(
                request,
                f'LLM extraction complete. It has been added to the review queue.'
            )
        except Exception as e:
            messages.error(request, f'LLM extraction failed: {e}')

    return redirect('contributor:publication_detail', pk=pk)

# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------

@login_required
def review_queue(request):
    reviews = ExtractionReview.objects.filter(
        decision='pending',
    ).select_related('extraction__publication', 'submitted_by')

    return render(request, 'contributor/review_queue.html', {
        'reviews': reviews,
    })


@login_required
def review_detail(request, review_id):
    review = get_object_or_404(ExtractionReview, pk=review_id)
    extraction = review.extraction
    publication = extraction.publication

    if request.method == 'POST' and (request.user.is_staff or
            request.user.groups.filter(name='Reviewer').exists()):
        action = request.POST.get('action')
        notes = request.POST.get('reviewer_notes', '').strip()
        score = request.POST.get('quality_score', '').strip()
        quality_score = int(score) if score.isdigit() else None

        from django.contrib import messages
        try:
            if action == 'approve':
                approve_extraction(review=review, reviewer=request.user,
                                   notes=notes, quality_score=quality_score)
                messages.success(request, 'Extraction approved.')
                return redirect('contributor:review_queue')
            elif action == 'needs_revision':
                needs_revision(review=review, reviewer=request.user,
                               notes=notes, quality_score=quality_score)
                messages.warning(request, 'Extraction returned for revision.')
                return redirect('contributor:review_queue')
            elif action == 'reject':
                reject_extraction(review=review, reviewer=request.user,
                                  notes=notes, quality_score=quality_score)
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
    })


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------

@login_required
def request_deletion_view(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    if request.method == 'POST':
        from django.contrib import messages
        reason = request.POST.get('reason', '').strip()
        try:
            request_deletion(publication=publication, requested_by=request.user, reason=reason)
            messages.warning(request, 'Deletion request submitted. The paper is now locked.')
        except ValueError as e:
            messages.error(request, str(e))
    return redirect('contributor:publication_detail', pk=pk)


@login_required
def cancel_deletion_view(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    deletion_request = get_object_or_404(DeletionRequest, publication=publication,
                                          requested_by=request.user, status='pending')
    if request.method == 'POST':
        from django.contrib import messages
        try:
            cancel_deletion_request(deletion_request=deletion_request, cancelled_by=request.user)
            messages.success(request, 'Deletion request cancelled. The paper is now unlocked.')
        except ValueError as e:
            messages.error(request, str(e))
    return redirect('contributor:publication_detail', pk=pk)


@login_required
def deletion_queue(request):
    pending_requests = DeletionRequest.objects.filter(
        status='pending',
    ).select_related('publication', 'requested_by')
    return render(request, 'contributor/deletion_queue.html', {
        'pending_requests': pending_requests,
    })


@login_required
def resolve_deletion_view(request, deletion_request_id):
    deletion_request = get_object_or_404(DeletionRequest, pk=deletion_request_id)

    if not (request.user.is_staff or request.user.groups.filter(name='Editor').exists()):
        from django.contrib import messages
        messages.error(request, 'You do not have permission to resolve deletion requests.')
        return redirect('contributor:deletion_queue')

    if request.method == 'POST':
        from django.contrib import messages
        action = request.POST.get('action')
        note = request.POST.get('resolution_note', '').strip()
        try:
            resolve_deletion_request(deletion_request=deletion_request,
                                      resolved_by=request.user,
                                      approve=action == 'approve', note=note)
            if action == 'approve':
                messages.success(request, 'Publication marked as excluded.')
            else:
                messages.success(request, 'Deletion request rejected. Paper is unlocked.')
        except ValueError as e:
            messages.error(request, str(e))
    return redirect('contributor:deletion_queue')


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@login_required
def profile(request):
    return render(request, 'contributor/profile.html')


def logout_view(request):
    logout(request)
    return redirect('login')