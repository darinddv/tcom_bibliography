from django.contrib.auth.models import User
from django.utils import timezone
from core.models.deletion_request import DeletionRequest
from core.models.publications import Publication


def request_deletion(
    publication: Publication,
    requested_by: User,
    reason: str,
) -> DeletionRequest:
    """
    Submit a deletion request for a publication.
    Only allowed if no pending request already exists.
    """
    if not reason.strip():
        raise ValueError('A reason is required when requesting deletion.')

    if publication.is_locked():
        raise ValueError('This publication already has a pending deletion request.')

    return DeletionRequest.objects.create(
        publication=publication,
        requested_by=requested_by,
        reason=reason,
    )


def cancel_deletion_request(
    deletion_request: DeletionRequest,
    cancelled_by: User,
) -> DeletionRequest:
    """
    Cancel a pending deletion request.
    Only the original requester can cancel.
    """
    if deletion_request.status != 'pending':
        raise ValueError('Only pending deletion requests can be cancelled.')

    if deletion_request.requested_by != cancelled_by:
        raise ValueError('Only the original requester can cancel this request.')

    deletion_request.status = 'cancelled'
    deletion_request.resolved_by = cancelled_by
    deletion_request.resolved_at = timezone.now()
    deletion_request.save()

    return deletion_request


def resolve_deletion_request(
    deletion_request: DeletionRequest,
    resolved_by: User,
    approve: bool,
    note: str = '',
) -> DeletionRequest:
    """
    Approve or reject a deletion request. Editor/admin only.
    Approval soft-deletes the publication.
    """
    if deletion_request.status != 'pending':
        raise ValueError('Only pending deletion requests can be resolved.')

    deletion_request.status = 'approved' if approve else 'rejected'
    deletion_request.resolved_by = resolved_by
    deletion_request.resolved_at = timezone.now()
    deletion_request.resolution_note = note
    deletion_request.save()

    if approve:
        pub = deletion_request.publication
        pub.inclusion_status = 'excluded'
        pub.exclusion_reason = f'Deleted via deletion request: {deletion_request.reason[:200]}'
        pub.save()

    return deletion_request