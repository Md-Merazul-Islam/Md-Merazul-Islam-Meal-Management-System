from celery import shared_task
from django.utils import timezone
from .models import CommitmentForSixMonths

@shared_task
def reset_expired_commitments():
    today = timezone.now().date()
    expired_commitments = CommitmentForSixMonths.objects.filter(
        commitment_status=True,
        commitment_end_date__lt=today
    )
    count = expired_commitments.count()

    for commitment in expired_commitments:
        commitment.reset_commitment()

    return f'Reset {count} expired commitments.'
