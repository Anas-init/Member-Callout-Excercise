from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Announcement, Local


class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["local_id"] = str(user.local_id)
        token["full_name"] = user.full_name
        return token


class LocalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Local
        fields = ["id", "name"]


class AnnouncementCreateSerializer(serializers.Serializer):
    idempotency_key = serializers.UUIDField()
    title = serializers.CharField(max_length=255, required=False)
    body = serializers.CharField(required=False)
    needs_ack = serializers.BooleanField(default=False)
    target_classification = serializers.CharField(
        max_length=100, required=False, allow_null=True
    )
    raw_text = serializers.CharField(required=False)

    def validate(self, attrs):
        has_raw = bool(attrs.get("raw_text"))
        has_manual = bool(attrs.get("title")) and bool(attrs.get("body"))
        if has_raw == has_manual:
            raise serializers.ValidationError(
                "Send either raw_text (drafts, not sent) or both title and body."
            )
        return attrs


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = [
            "id", "title", "body", "push_preview", "needs_ack",
            "target_classification", "status", "ai_draft", "approved_at",
            "sent_at", "created_at",
        ]
