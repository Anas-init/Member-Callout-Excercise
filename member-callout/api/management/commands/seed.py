import uuid
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from api.models import Announcement, AnnouncementRecipient, Local, PushLog, User

NAMESPACE = uuid.UUID("6b6f3c1e-0000-4000-8000-000000000c0d")

PASSWORD = "callout1234"

CLASSIFICATIONS = [
    "Journeyman Wireman",
    "Apprentice 3rd Year",
    "Apprentice 1st Year",
    "Foreman",
]

FIRST_NAMES = """
Ray Marcus Alicia Tomasz Deon Rosa Hector Sheila Dwayne Priya
Curtis Jolene Andre Mei Frank Rashida Gustavo Bridget Owen Tanya
Leon Consuelo Dermot Aisha Vince Marguerite Kwame Lorna Emmett Yuki
Stanley Fatima Roland Nadia Clyde Imani Bruno Shauna Terrence Delia
Wesley Anika Gerald Paloma Duncan Renata Amos Kiera Malik Josefina
""".split()

LAST_NAMES = """
Calderon Novak Whitfield Okonkwo Barrera Lindgren Mabasa Delgado Pham Rourke
Castellanos Abernathy Oyelaran Stefanik Quintero Brandt Achebe Villalobos Kaur Mancini
Fitzgerald Moreau Ibarra Sandoval Kowalczyk Traore Hollis Berkowitz Nakamura Espinoza
Underwood Bissonnette Adeyemi Strand Lucero Petrosyan Kirkland Salazar Amundsen Charbonneau
Riddick Vasquez Mbeki Halloran Tsosie Ferreira Blackwood Anand Cormier Escalante
""".split()

LOCALS = [
    {"slug": "local27", "name": "Local 27", "leader": "Denise Okafor", "members": 2000},
    {"slug": "local9", "name": "Local 9", "leader": "Walter Brennan", "members": 200},
]


def stable_id(*parts):
    return uuid.uuid5(NAMESPACE, ":".join(parts))


def member_name(i):
    return f"{FIRST_NAMES[i % len(FIRST_NAMES)]} {LAST_NAMES[(i // len(FIRST_NAMES)) % len(LAST_NAMES)]}"


def email_for(full_name, slug):
    first, last = full_name.lower().split()
    return f"{first}.{last}@{slug}.crewlink.test"


class Command(BaseCommand):
    help = "Populate the database with two locals, their members, and one sent announcement."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            PushLog.objects.all().delete()
            AnnouncementRecipient.objects.all().delete()
            Announcement.objects.all().delete()
            User.objects.all().delete()
            Local.objects.all().delete()

        password = make_password(PASSWORD)

        for spec in LOCALS:
            slug, name = spec["slug"], spec["name"]

            local, _ = Local.objects.update_or_create(
                id=stable_id("local", slug), defaults={"name": name}
            )

            User.objects.update_or_create(
                id=stable_id("leader", slug),
                defaults={
                    "local": local,
                    "full_name": spec["leader"],
                    "email": email_for(spec["leader"], slug),
                    "role": "leader",
                    "password": password,
                },
            )

            User.objects.bulk_create(
                [
                    User(
                        id=stable_id("member", slug, str(i)),
                        local=local,
                        full_name=member_name(i),
                        email=email_for(member_name(i), slug),
                        role="member",
                        classification=CLASSIFICATIONS[i % len(CLASSIFICATIONS)],
                        status="retired" if i and i % 50 == 0 else "active",
                        password=password,
                    )
                    for i in range(spec["members"])
                ],
                ignore_conflicts=True,
                batch_size=500,
            )

            self.stdout.write(f"{name} ({local.id}): {spec['members']} members")
            self.stdout.write(f"  leader: {email_for(spec['leader'], slug)}")
            self.stdout.write(f"  member: {email_for(member_name(0), slug)}")

        self.stdout.write(self.seed_announcement())
        self.stdout.write(f"password for every account: {PASSWORD}")

    def seed_announcement(self):
        sent_at = timezone.now() - timedelta(days=2)

        announcement, _ = Announcement.objects.update_or_create(
            id=stable_id("announcement", "local27"),
            defaults={
                "idempotency_key": stable_id("idempotency", "local27"),
                "local": Local.objects.get(id=stable_id("local", "local27")),
                "created_by": User.objects.get(id=stable_id("leader", "local27")),
                "title": "Emergency meeting Thursday 6pm",
                "body": "The contractor is pulling crews off the westside job. "
                        "Everyone needs to be at the hall Thursday at 6pm.",
                "push_preview": "Emergency meeting Thurs 6pm at the hall re: westside job.",
                "needs_ack": True,
                "status": "sent",
                "sent_at": sent_at,
            },
        )

        members = list(
            User.objects.filter(
                local=announcement.local, role="member", status="active"
            ).values_list("id", flat=True)
        )

        AnnouncementRecipient.objects.bulk_create(
            [
                AnnouncementRecipient(
                    id=stable_id("recipient", str(announcement.id), str(member_id)),
                    announcement=announcement,
                    member_id=member_id,
                    delivery_status="delivered",
                    delivered_at=sent_at,
                    read_at=sent_at + timedelta(minutes=20) if i % 100 < 60 else None,
                    acknowledged_at=sent_at + timedelta(minutes=25) if i % 100 < 35 else None,
                )
                for i, member_id in enumerate(members)
            ],
            ignore_conflicts=True,
            batch_size=500,
        )

        return f"announcement {announcement.id}: {len(members)} recipients"
