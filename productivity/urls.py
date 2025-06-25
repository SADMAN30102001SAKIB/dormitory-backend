from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DomainViewSet, TrackedTimeViewSet, LiveUsersView

router = DefaultRouter()
router.register(r"domains", DomainViewSet, basename="domain")
router.register(r"tracked-times", TrackedTimeViewSet, basename="trackedtime")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "live-users/",
        LiveUsersView.as_view(),
        name="live-users",
    ),
]
