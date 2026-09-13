from rest_framework.permissions import BasePermission


class IsLeader(BasePermission):
    def has_permission(self, request, view):
        return request.user is not None and request.user.role == "leader"


class IsMember(BasePermission):
    def has_permission(self, request, view):
        return request.user is not None and request.user.role == "member"
