from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone

from .models import AnnouncementRecipient, User


def fan_out(announcement):
    members = User.objects.filter(
        local=announcement.local, role="member", status="active"
    )
    if announcement.target_classification:
        members = members.filter(classification=announcement.target_classification)

    AnnouncementRecipient.objects.bulk_create(
        [
            AnnouncementRecipient(announcement=announcement, member_id=member_id)
            for member_id in members.values_list("id", flat=True)
        ],
        ignore_conflicts=True,
        batch_size=1000,
    )

    announcement.status = "queued"
    announcement.sent_at = timezone.now()
    announcement.save(update_fields=["status", "sent_at"])


def announcement_counts(announcement_id):
    def compute():
        return AnnouncementRecipient.objects.filter(
            announcement_id=announcement_id
        ).aggregate(
            total=Count("id"),
            sent=Count("id", filter=Q(delivery_status="delivered")),
            read=Count("id", filter=Q(read_at__isnull=False)),
            acknowledged=Count("id", filter=Q(acknowledged_at__isnull=False)),
        )

    return cache.get_or_set(
        f"counts:{announcement_id}", compute, settings.COUNTS_CACHE_SECONDS
    )
