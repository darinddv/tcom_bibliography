from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from core.models.deletion_request import DeletionRequest
from core.services.deletion import resolve_deletion_request
from contributor.decorators import editor_required


@editor_required
def deletion_queue(request):
    pending_requests = DeletionRequest.objects.filter(
        status='pending',
    ).select_related('publication', 'requested_by')

    return render(request, 'contributor/deletion_queue.html', {
        'pending_requests': pending_requests,
    })


@editor_required
def resolve_deletion_view(request, deletion_request_id):
    deletion_request = get_object_or_404(DeletionRequest, pk=deletion_request_id)

    if request.method == 'POST':
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
