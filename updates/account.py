from django.contrib.auth import logout, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.contrib import messages

from core.models.workflow import PublicationAssignment
from core.models.extraction import ExtractionRecord
from contributor.decorators import contributor_required


@contributor_required
def work(request):
    """My Work — assigned papers queue for contributors."""
    assignments = PublicationAssignment.objects.filter(
        assigned_to=request.user,
        completed_at=None,
    ).select_related('publication')

    active_extractions = ExtractionRecord.objects.filter(
        reviewer=request.user,
        status__in=['draft', 'submitted'],
    ).select_related('publication')

    return render(request, 'contributor/work.html', {
        'assignments': assignments,
        'active_extractions': active_extractions,
    })


@login_required
def profile(request):
    return render(request, 'contributor/profile.html')


def register(request):
    if request.user.is_authenticated:
        return redirect('contributor:analytics')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, 'Welcome! Your account has been created.')
            return redirect('contributor:analytics')
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')
