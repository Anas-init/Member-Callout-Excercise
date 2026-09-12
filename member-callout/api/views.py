from django.db import transaction
from django.http import Http404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .mixins import LocalScopedMixin
from .models import Announcement, Local
from .permissions import IsLeader
from .serializers import (
    AnnouncementCreateSerializer,
    AnnouncementSerializer,
    LocalSerializer,
    LoginSerializer,
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
