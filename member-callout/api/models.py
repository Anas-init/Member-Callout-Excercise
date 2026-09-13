import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

# not using auto increment in id field b/c we need some idempotency in our work flow

class Local(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False) 
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(self, email, password, local, full_name="", **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        user = self.model(
            email=self.normalize_email(email),
            local=local,
            full_name=full_name,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, local, full_name="", **extra_fields):
        extra_fields.setdefault("role", "leader")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, local, full_name, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [("leader", "Leader"), ("member", "Member")]
    STATUS_CHOICES = [("active", "Active"), ("retired", "Retired"), ("suspended", "Suspended")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    local = models.ForeignKey(Local, on_delete=models.PROTECT, related_name="users")
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    classification = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "local"]

    @property
    def is_active(self):
        return self.status == "active"

    def __str__(self):
        return self.full_name


class Announcement(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("queued", "Queued"),
        ("sending", "Sending"),
        ("sent", "Sent"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    idempotency_key = models.UUIDField(unique=True)
    local = models.ForeignKey(Local, on_delete=models.PROTECT, related_name="announcements")
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_announcements")
    title = models.CharField(max_length=255)
    body = models.TextField()
    push_preview = models.CharField(max_length=255, null=True, blank=True)
    needs_ack = models.BooleanField(default=False)
    target_classification = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    ai_draft = models.JSONField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True,
        related_name="approved_announcements",
    )

    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~(
                    models.Q(ai_draft__isnull=False)
                    & models.Q(approved_at__isnull=True)
                    & models.Q(sent_at__isnull=False)
                ),
                name="ai_draft_requires_approval_before_send",
            ),
        ]

    def __str__(self):
        return self.title


class AnnouncementRecipient(models.Model):
    DELIVERY_CHOICES = [("pending", "Pending"), ("delivered", "Delivered"), ("failed", "Failed")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name="recipients")
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_announcements")
    delivery_status = models.CharField(max_length=10, choices=DELIVERY_CHOICES, default="pending")
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("announcement", "member")]
        indexes = [
            models.Index(
                fields=["created_at"],
                condition=models.Q(delivery_status="pending"),
                name="recipient_pending_idx",
            ),
        ]

    def __str__(self):
        return f"{self.member} <- {self.announcement}"


class PushLog(models.Model):


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.OneToOneField(
        AnnouncementRecipient, on_delete=models.CASCADE, related_name="push_log"
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField()

    def __str__(self):
        return f"push -> {self.recipient_id}"
