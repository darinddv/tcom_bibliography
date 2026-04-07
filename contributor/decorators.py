from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def contributor_required(view_func):
    """Requires Contributor, Reviewer, Editor, or staff access."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not (request.user.is_staff or
                request.user.groups.filter(
                    name__in=['Contributor', 'Reviewer', 'Editor']
                ).exists()):
            messages.error(request, 'Contributor access required.')
            return redirect('contributor:bibliography')
        return view_func(request, *args, **kwargs)
    return wrapper


def reviewer_required(view_func):
    """Requires Reviewer, Editor, or staff access."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not (request.user.is_staff or
                request.user.groups.filter(
                    name__in=['Reviewer', 'Editor']
                ).exists()):
            messages.error(request, 'Reviewer access required.')
            return redirect('contributor:bibliography')
        return view_func(request, *args, **kwargs)
    return wrapper


def editor_required(view_func):
    """Requires Editor or staff access."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not (request.user.is_staff or
                request.user.groups.filter(name='Editor').exists()):
            messages.error(request, 'Editor access required.')
            return redirect('contributor:bibliography')
        return view_func(request, *args, **kwargs)
    return wrapper
