from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("locals/", views.LocalListView.as_view(), name="locals"),
    path("announcements/", views.AnnouncementListCreateView.as_view(), name="announcements"),
    path("announcements/<uuid:pk>/", views.AnnouncementDetailView.as_view(), name="announcement-detail"),
    path("announcements/<uuid:pk>/ai-draft/", views.AiDraftView.as_view(), name="ai-draft"),
    path("announcements/<uuid:pk>/ai-draft/confirm/", views.AiDraftConfirmView.as_view(), name="ai-draft-confirm"),
    path("members/announcements/", views.MemberInboxView.as_view(), name="member-inbox"),
    path("members/announcements/<uuid:recipient_id>/read/", views.MemberReadView.as_view(), name="member-read"),
    path("members/announcements/<uuid:recipient_id>/acknowledge/", views.MemberAcknowledgeView.as_view(), name="member-acknowledge"),
]
