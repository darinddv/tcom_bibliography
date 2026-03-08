from django.contrib.auth.models import User
from django.utils import timezone
from core.models.extraction import ExtractionRecord
from core.models.extraction_review import ExtractionReview
from core.models.workflow import PublicationAssignment
from core.services.workflow import transition, get_current_state
from core.services.assignment import complete_assignment


def submit_extraction(extraction: ExtractionRecord, actor: User) -> ExtractionReview:
    """
    Submit an extraction for review.
    Allowed from any status -- contributors can resubmit approved or rejected
    extractions if they spot errors. Each submission creates a new review record.
    """
    # Mark as submitted
    extraction.status = 'submitted'
    extraction.save()

    # Close the contributor's active assignment if one exists
    complete_assignment(
        publication=extraction.publication,
        actor=actor,
    )

    # Always create a fresh review record -- don't reuse old ones
    # Each submission cycle gets its own review
    review = ExtractionReview.objects.create(
        extraction=extraction,
        submitted_by=actor,
    )

    # Transition workflow to pending_review from any active state
    current_state = get_current_state(extraction.publication)
    if current_state in ('assigned', 'in_progress', 'approved', 'rejected'):
        transition(
            publication=extraction.publication,
            to_state='pending_review',
            actor=actor,
            comment=f'Extraction submitted by {actor.username}.',
        )

    return review


def reopen_assignment(extraction: ExtractionRecord) -> None:
    """
    Reopen the assignment for the contributor who submitted this extraction.
    Called when a review comes back as needs_revision or rejected.
    Creates a new active assignment if one doesn't already exist.
    """
    # Find the contributor from the most recent review
    review = extraction.reviews.order_by('-submitted_at').first()
    if not review:
        return
    contributor = review.submitted_by

    # Reopen assignment only if no active assignment exists for this contributor
    existing = PublicationAssignment.objects.filter(
        publication=extraction.publication,
        assigned_to=contributor,
        completed_at=None,
    ).exists()

    if not existing:
        PublicationAssignment.objects.create(
            publication=extraction.publication,
            assigned_to=contributor,
            assigned_by=contributor,
        )


def approve_extraction(
    review: ExtractionReview,
    reviewer: User,
    notes: str = '',
    quality_score: int = None,
) -> ExtractionReview:
    """
    Approve an extraction review.
    Transitions the publication to approved if no other pending reviews exist.
    """
    review.decision = 'approved'
    review.reviewer = reviewer
    review.reviewed_at = timezone.now()
    review.reviewer_notes = notes
    review.quality_score = quality_score
    review.save()

    review.extraction.status = 'approved'
    review.extraction.save()

    # Reopen assignment so contributor can still edit if needed
    reopen_assignment(review.extraction)

    # Only transition publication to approved if no other pending reviews remain
    pending_others = ExtractionReview.objects.filter(
        extraction__publication=review.extraction.publication,
        decision='pending',
    ).exclude(pk=review.pk).exists()

    if not pending_others:
        transition(
            publication=review.extraction.publication,
            to_state='approved',
            actor=reviewer,
            comment=f'Extraction approved by {reviewer.username}.',
        )

    return review


def needs_revision(
    review: ExtractionReview,
    reviewer: User,
    notes: str,
    quality_score: int = None,
) -> ExtractionReview:
    """
    Return an extraction for revision.
    Requires notes explaining what needs improvement.
    Reopens the contributor's assignment and transitions back to in_progress.
    """
    if not notes:
        raise ValueError('Reviewer notes are required when requesting revision.')

    review.decision = 'needs_revision'
    review.reviewer = reviewer
    review.reviewed_at = timezone.now()
    review.reviewer_notes = notes
    review.quality_score = quality_score
    review.save()

    review.extraction.status = 'draft'
    review.extraction.save()

    reopen_assignment(review.extraction)

    transition(
        publication=review.extraction.publication,
        to_state='in_progress',
        actor=reviewer,
        comment=f'Needs revision: {notes[:100]}',
    )

    return review


def reject_extraction(
    review: ExtractionReview,
    reviewer: User,
    notes: str,
    quality_score: int = None,
) -> ExtractionReview:
    """
    Reject an extraction review.
    Requires notes explaining the rejection.
    Reopens the contributor's assignment so they can resubmit.
    """
    if not notes:
        raise ValueError('Reviewer notes are required when rejecting an extraction.')

    review.decision = 'rejected'
    review.reviewer = reviewer
    review.reviewed_at = timezone.now()
    review.reviewer_notes = notes
    review.quality_score = quality_score
    review.save()

    review.extraction.status = 'draft'
    review.extraction.save()

    reopen_assignment(review.extraction)

    transition(
        publication=review.extraction.publication,
        to_state='rejected',
        actor=reviewer,
        comment=f'Extraction rejected by {reviewer.username}: {notes[:100]}',
    )

    return review