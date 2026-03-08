from django.contrib.auth.models import User
from django.utils import timezone
from core.models.workflow import PublicationAssignment
from core.models.publications import Publication
from core.services.workflow import transition, get_current_state


def assign_publication(
    publication: Publication,
    assigned_to: User,
    assigned_by: User,
) -> PublicationAssignment:
    """
    Assign a publication to a contributor.
    Multiple contributors can be assigned to the same publication simultaneously.
    Only transitions workflow state if the paper is currently unassigned.
    """
    # Prevent duplicate active assignments for the same person on the same paper
    existing = PublicationAssignment.objects.filter(
        publication=publication,
        assigned_to=assigned_to,
        completed_at=None,
    ).first()
    if existing:
        return existing

    assignment = PublicationAssignment.objects.create(
        publication=publication,
        assigned_to=assigned_to,
        assigned_by=assigned_by,
    )

    # Only transition if currently unassigned
    current_state = get_current_state(publication)
    if current_state == 'unassigned':
        transition(
            publication=publication,
            to_state='assigned',
            actor=assigned_by,
            comment=f'Assigned to {assigned_to.username}.',
        )

    return assignment


def self_assign(publication: Publication, user: User) -> PublicationAssignment:
    """
    Convenience wrapper for a contributor claiming a paper themselves.
    """
    return assign_publication(
        publication=publication,
        assigned_to=user,
        assigned_by=user,
    )


def complete_assignment(publication: Publication, actor: User) -> None:
    """
    Mark the actor's active assignment as complete.
    Does not affect workflow state -- that is driven by ExtractionRecord submission.
    """
    PublicationAssignment.objects.filter(
        publication=publication,
        assigned_to=actor,
        completed_at=None,
    ).update(completed_at=timezone.now())