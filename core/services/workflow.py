from django.contrib.auth.models import User
from django.utils import timezone
from core.models.workflow import WorkflowTransition, PublicationAssignment
from core.models.publications import Publication


# Valid transitions map -- from_state: [allowed to_states]
VALID_TRANSITIONS = {
    '':                 ['unassigned'],
    'unassigned':       ['assigned', 'pending_review', 'archived', 'flagged'],
    'assigned':         ['in_progress', 'unassigned', 'archived', 'flagged'],
    'in_progress':      ['pending_review', 'archived', 'flagged'],
    'pending_review':   ['approved', 'rejected', 'in_progress', 'flagged'],
    'rejected':         ['in_progress', 'pending_review', 'archived', 'flagged'],
    'approved':         ['pending_review', 'archived', 'flagged'],
    'archived':         ['unassigned', 'flagged'],
    'flagged':          ['unassigned', 'archived'],
}

def get_current_state(publication: Publication) -> str:
    """
    Returns the current workflow state of a publication.
    Derived from the most recent WorkflowTransition.
    Returns empty string if no transitions exist.
    """
    latest = (
        WorkflowTransition.objects
        .filter(publication=publication)
        .order_by('-timestamp')
        .first()
    )
    return latest.to_state if latest else ''


def transition(
    publication: Publication,
    to_state: str,
    actor: User = None,
    comment: str = '',
    is_system_action: bool = False,
) -> WorkflowTransition:
    """
    Transition a publication to a new workflow state.
    Raises ValueError if the transition is not permitted.
    Returns the new WorkflowTransition instance.
    """
    from_state = get_current_state(publication)

    allowed = VALID_TRANSITIONS.get(from_state, [])
    if to_state not in allowed:
        raise ValueError(
            f'Invalid transition: {from_state!r} -> {to_state!r}. '
            f'Allowed transitions from {from_state!r}: {allowed}'
        )

    return WorkflowTransition.objects.create(
        publication=publication,
        from_state=from_state,
        to_state=to_state,
        actor=actor,
        comment=comment,
        is_system_action=is_system_action,
    )