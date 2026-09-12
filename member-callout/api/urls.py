from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("locals/", views.LocalListView.as_view(), name="locals"),
    path("announcements/", views.AnnouncementListCreateView.as_view(), name="announcements"),
    path("announcements/<uuid:pk>/", views.AnnouncementDetailView.as_view(), name="announcement-detail"),
]
