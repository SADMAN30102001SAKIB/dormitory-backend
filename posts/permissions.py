from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAuthorOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Read-only methods are allowed for everyone
        if request.method in SAFE_METHODS:
            return True
        # Write permissions only for the author
        return obj.author == request.user
