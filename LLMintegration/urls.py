from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ConversationViewSet, semantic_search_view

router = DefaultRouter(
    trailing_slash=False
)  # automatically generate URL patterns for the viewset
router.register(
    "conversations", ConversationViewSet, basename="conversation"
)  # r'conversations' is the The URL prefix under which all the generated routes for the viewset live. basename='conversation' is used to name the URL patterns for reverse lookups.

urlpatterns = [
    path("", include(router.urls)),
    path("semantic-search/", semantic_search_view, name="semantic-search"),
]
