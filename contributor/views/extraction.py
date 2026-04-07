from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages

from core.models.publications import Publication
from core.models.workflow import PublicationAssignment
from core.models.extraction import ExtractionRecord
from core.models.study_profile import StudyProfile
from core.models.study_demographics import StudyDemographics
from core.models.risk_of_bias import RiskOfBiasAssessment, RiskOfBiasDomain
from core.models.statistical_method import StatisticalMethod
from core.models.predictor import PredictorCovariate
from core.models.assessment import AssessmentToolUsage, OutcomeDomain
from core.services.workflow import transition, get_current_state
from contributor.forms import (
    StudyProfileForm, StudyDemographicsForm,
    RiskOfBiasForm, RiskOfBiasDomainForm,
    AssessmentToolUsageForm, OutcomeDomainForm,
    StatisticalMethodForm, PredictorCovariateForm,
)
from contributor.decorators import contributor_required


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_extraction_or_redirect(request, publication):
    extraction_id = request.POST.get('extraction_id') or request.GET.get('extraction_id')

    if extraction_id:
        extraction = get_object_or_404(
            ExtractionRecord,
            pk=extraction_id,
            publication=publication,
        )
        return extraction, None

    # Fallback: find the current user's human extraction
    extraction = ExtractionRecord.objects.filter(
        publication=publication,
        reviewer=request.user,
        reviewer_type='human',
    ).first()

    if extraction:
        return extraction, None

    return None, redirect('contributor:publication_detail', pk=publication.pk)


def _check_not_locked(publication, request):
    if publication.is_locked():
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
        'extraction_id': extraction.pk,
    }


def _statistical_context(extraction):
    return {
        'statistical_methods': StatisticalMethod.objects.filter(extraction=extraction),
        'statistical_form': StatisticalMethodForm(),
        'extraction': extraction,
        'publication': extraction.publication,
        'extraction_id': extraction.pk,
    }


def _predictors_context(extraction):
    return {
        'predictors': PredictorCovariate.objects.filter(extraction=extraction),
        'predictor_form': PredictorCovariateForm(),
        'extraction': extraction,
        'publication': extraction.publication,
        'extraction_id': extraction.pk,
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
        'extraction_id': extraction.pk,
    }


# ---------------------------------------------------------------------------
# Full page
# ---------------------------------------------------------------------------

@login_required
def extraction_form(request, pk, extraction_id=None):
    publication = get_object_or_404(Publication, pk=pk)

    lock_response = _check_not_locked(publication, request)
    if lock_response:
        return lock_response

    if extraction_id:
        # Edit a specific extraction (human or LLM) by ID
        extraction = get_object_or_404(
            ExtractionRecord,
            pk=extraction_id,
            publication=publication,
        )
    else:
        # Per-user flow: find the current user's extraction, or create one
        extraction = ExtractionRecord.objects.filter(
            publication=publication,
            reviewer=request.user,
            reviewer_type='human',
        ).first()

        if not extraction:
            has_assignment = PublicationAssignment.objects.filter(
                publication=publication,
                assigned_to=request.user,
            ).exists()
            if not has_assignment:
                messages.error(request, 'You are not assigned to this paper.')
                return redirect('contributor:publication_detail', pk=pk)

            extraction = ExtractionRecord.objects.create(
                publication=publication,
                reviewer=request.user,
                reviewer_type='human',
                status='draft',
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

    return render(request, 'contributor/extraction_form.html', {
        'publication': publication,
        'extraction': extraction,
        'latest_review': latest_review,
        'extraction_id': extraction.pk,
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
# Combined save — study profile + demographics + risk of bias header
# Used by both auto-save (HTMX change event) and Save Draft button
# ---------------------------------------------------------------------------

@login_required
@require_POST
def save_extraction(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)

    study_profile, _ = StudyProfile.objects.get_or_create(extraction=extraction)
    demographics, _ = StudyDemographics.objects.get_or_create(
        study_profile=study_profile
    )
    rob, _ = RiskOfBiasAssessment.objects.get_or_create(extraction=extraction)

    profile_form = StudyProfileForm(request.POST, instance=study_profile)
    demographics_form = StudyDemographicsForm(request.POST, instance=demographics)
    rob_form = RiskOfBiasForm(request.POST, instance=rob)

    if all([
        profile_form.is_valid(),
        demographics_form.is_valid(),
        rob_form.is_valid(),
    ]):
        profile_form.save()
        demographics_form.save()
        rob_form.save()
        return HttpResponse(status=204)

    return HttpResponse(status=422)


# ---------------------------------------------------------------------------
# HTMX RoB domain actions
# ---------------------------------------------------------------------------

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

    domain = get_object_or_404(
        RiskOfBiasDomain, pk=domain_id, assessment__extraction=extraction
    )
    domain.delete()
    return render(request, 'contributor/partials/rob_section.html', _rob_context(extraction))


# ---------------------------------------------------------------------------
# HTMX tool actions
# ---------------------------------------------------------------------------

@login_required
def tools_section(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)
    return render(
        request, 'contributor/partials/tools_section.html', _tools_context(extraction)
    )


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

    return render(
        request, 'contributor/partials/tools_section.html', _tools_context(extraction)
    )


@login_required
@require_POST
def delete_tool_usage(request, pk, tool_usage_id):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)

    tool_usage = get_object_or_404(
        AssessmentToolUsage, pk=tool_usage_id, extraction=extraction
    )
    tool_usage.delete()
    return render(
        request, 'contributor/partials/tools_section.html', _tools_context(extraction)
    )


@login_required
@require_POST
def add_outcome_domain(request, pk, tool_usage_id):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)

    tool_usage = get_object_or_404(
        AssessmentToolUsage, pk=tool_usage_id, extraction=extraction
    )
    form = OutcomeDomainForm(request.POST)
    if form.is_valid():
        outcome = form.save(commit=False)
        outcome.assessment_tool_usage = tool_usage
        outcome.save()

    return render(
        request, 'contributor/partials/tools_section.html', _tools_context(extraction)
    )


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
    return render(
        request, 'contributor/partials/tools_section.html', _tools_context(extraction)
    )


# ---------------------------------------------------------------------------
# HTMX statistical methods
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

    return render(
        request,
        'contributor/partials/statistical_section.html',
        _statistical_context(extraction),
    )


@login_required
@require_POST
def delete_statistical_method(request, pk, method_id):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)

    method = get_object_or_404(StatisticalMethod, pk=method_id, extraction=extraction)
    method.delete()
    return render(
        request,
        'contributor/partials/statistical_section.html',
        _statistical_context(extraction),
    )


# ---------------------------------------------------------------------------
# HTMX predictors
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

    return render(
        request,
        'contributor/partials/predictors_section.html',
        _predictors_context(extraction),
    )


@login_required
@require_POST
def delete_predictor(request, pk, predictor_id):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return HttpResponse(status=403)

    predictor = get_object_or_404(
        PredictorCovariate, pk=predictor_id, extraction=extraction
    )
    predictor.delete()
    return render(
        request,
        'contributor/partials/predictors_section.html',
        _predictors_context(extraction),
    )


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------

@login_required
@require_POST
def submit_extraction_view(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    extraction, err = _get_extraction_or_redirect(request, publication)
    if err:
        return err

    from core.services.extraction import submit_extraction
    try:
        submit_extraction(extraction=extraction, actor=request.user)
        messages.success(request, 'Extraction submitted for review.')
    except ValueError as e:
        messages.error(request, str(e))

    return redirect('contributor:work')