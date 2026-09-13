from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .ai import generate_draft
from .mixins import LocalScopedMixin
from .models import Announcement, AnnouncementRecipient, Local
from .permissions import IsLeader, IsMember
from .serializers import (
    AnnouncementCreateSerializer,
    AnnouncementSerializer,
    LocalSerializer,
    LoginSerializer,
    MemberAnnouncementSerializer,
)
from .services import announcement_counts, fan_out


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer


class LocalListView(generics.ListAPIView):
    permission_classes = [IsLeader]
    serializer_class = LocalSerializer

    def get_queryset(self):
        return Local.objects.filter(id=self.request.user.local_id).order_by("name")


class AnnouncementListCreateView(LocalScopedMixin, generics.ListCreateAPIView):
    permission_classes = [IsLeader]
    queryset = Announcement.objects.order_by("-created_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AnnouncementCreateSerializer
        return AnnouncementSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        raw_text = data.get("raw_text")

        with transaction.atomic():
            announcement, created = Announcement.objects.get_or_create(
                idempotency_key=data["idempotency_key"],
                defaults={
                    "local": request.user.local,
                    "created_by": request.user,
                    "title": data.get("title", ""),
                    "body": data.get("body", ""),
                    "needs_ack": data["needs_ack"],
                    "target_classification": data.get("target_classification"),
                    "ai_draft": {"raw_text": raw_text} if raw_text else None,
                },
            )

            if not created:
                if (
                    announcement.local_id != request.user.local_id
                    or announcement.created_by_id != request.user.id
                ):
                    raise Http404
                return Response(AnnouncementSerializer(announcement).data)

            if not raw_text:
                fan_out(announcement)

        return Response(
            AnnouncementSerializer(announcement).data, status=status.HTTP_201_CREATED
        )


class AnnouncementDetailView(LocalScopedMixin, generics.RetrieveAPIView):
    permission_classes = [IsLeader]
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer

    def retrieve(self, request, *args, **kwargs):
        announcement = self.get_object()
        data = self.get_serializer(announcement).data
        data["counts"] = announcement_counts(announcement.id)
        return Response(data)


def member_recipient(request, recipient_id):
    return get_object_or_404(
        AnnouncementRecipient.objects.select_related("announcement"),
        id=recipient_id,
        member=request.user,
    )


class MemberInboxView(generics.ListAPIView):
    permission_classes = [IsMember]
    serializer_class = MemberAnnouncementSerializer

    def get_queryset(self):
        return (
            AnnouncementRecipient.objects.filter(member=self.request.user)
            .select_related("announcement")
            .order_by("-created_at")
        )


class MemberReadView(APIView):
    permission_classes = [IsMember]

    def post(self, request, recipient_id):
        recipient = member_recipient(request, recipient_id)
        AnnouncementRecipient.objects.filter(
            id=recipient_id, read_at__isnull=True
        ).update(read_at=timezone.now())
        recipient.refresh_from_db()
        return Response(MemberAnnouncementSerializer(recipient).data)


class MemberAcknowledgeView(APIView):
    permission_classes = [IsMember]

    def post(self, request, recipient_id):
        recipient = member_recipient(request, recipient_id)
        if not recipient.announcement.needs_ack:
            return Response(
                {"detail": "This announcement does not require acknowledgement."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        AnnouncementRecipient.objects.filter(
            id=recipient_id, acknowledged_at__isnull=True
        ).update(acknowledged_at=now)
        AnnouncementRecipient.objects.filter(
            id=recipient_id, read_at__isnull=True
        ).update(read_at=now)

        recipient.refresh_from_db()
        return Response(MemberAnnouncementSerializer(recipient).data)


def leader_announcement(request, pk):
    return get_object_or_404(Announcement, id=pk, local=request.user.local)


class AiDraftView(APIView):
    permission_classes = [IsLeader]

    def post(self, request, pk):
        announcement = leader_announcement(request, pk)
        if announcement.status != "draft":
            return Response(
                {"detail": "Only a draft can be redrafted."},
                status=status.HTTP_409_CONFLICT,
            )

        raw_text = request.data.get("raw_text") or (announcement.ai_draft or {}).get("raw_text")
        if not raw_text:
            return Response(
                {"detail": "No raw_text to draft from."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        announcement.ai_draft = {"raw_text": raw_text, **generate_draft(raw_text)}
        announcement.save(update_fields=["ai_draft"])
        return Response({"id": announcement.id, "approved": False, "ai_draft": announcement.ai_draft})


class AiDraftConfirmView(APIView):
    permission_classes = [IsLeader]

    def post(self, request, pk):
        announcement = leader_announcement(request, pk)
        draft = announcement.ai_draft or {}
        if not draft.get("title"):
            return Response(
                {"detail": "There is no generated draft to approve."},
                status=status.HTTP_409_CONFLICT,
            )

        title = request.data.get("title") or draft["title"]
        body = request.data.get("body") or draft.get("body")
        push_preview = request.data.get("push_preview") or draft.get("push_preview") or ""
        if not body:
            return Response(
                {"detail": "An approved announcement needs a body."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            approved = Announcement.objects.filter(id=pk, status="draft").update(
                title=title,
                body=body,
                push_preview=push_preview[: settings.PUSH_PREVIEW_MAX_CHARS],
                approved_at=timezone.now(),
                approved_by=request.user,
            )
            if not approved:
                return Response(
                    {"detail": "This announcement has already been approved."},
                    status=status.HTTP_409_CONFLICT,
                )
            announcement.refresh_from_db()
            fan_out(announcement)

        return Response(AnnouncementSerializer(announcement).data)
