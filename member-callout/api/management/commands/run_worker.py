import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from api.models import Announcement, AnnouncementRecipient, PushLog


class Command(BaseCommand):
    help = "Deliver pending announcement recipients."

    def add_arguments(self, parser):
        parser.add_argument("--drain", action="store_true")

    def handle(self, *args, **options):
        while True:
            delivered = self.deliver_batch()
            if delivered:
                self.stdout.write(f"delivered {delivered}")
                continue
            if options["drain"]:
                return
            time.sleep(settings.WORKER_POLL_SECONDS)

    @transaction.atomic
    def deliver_batch(self):
        rows = list(
            AnnouncementRecipient.objects.filter(delivery_status="pending")
            .select_for_update(skip_locked=True)
            .order_by("created_at")[: settings.WORKER_BATCH_SIZE]
        )
        if not rows:
            return 0

        announcement_ids = {row.announcement_id for row in rows}
        announcements = Announcement.objects.in_bulk(announcement_ids)

        Announcement.objects.filter(id__in=announcement_ids, status="queued").update(
            status="sending"
        )

        PushLog.objects.bulk_create(
            [
                PushLog(
                    recipient_id=row.id,
                    payload={
                        "title": announcements[row.announcement_id].title,
                        "body": announcements[row.announcement_id].push_preview
                        or announcements[row.announcement_id].body,
                    },
                )
                for row in rows
            ],
            ignore_conflicts=True,
        )

        AnnouncementRecipient.objects.filter(id__in=[row.id for row in rows]).update(
            delivery_status="delivered", delivered_at=timezone.now()
        )

        for announcement_id in announcement_ids:
            still_pending = AnnouncementRecipient.objects.filter(
                announcement_id=announcement_id, delivery_status="pending"
            ).exists()
            if not still_pending:
                Announcement.objects.filter(id=announcement_id).update(status="sent")

        return len(rows)
